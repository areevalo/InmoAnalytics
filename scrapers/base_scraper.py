import hashlib
import time
from random import random

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from requests import Response, Session
from utils.scraper_logger import ScraperLogger


def extract_cookies_from_session(session):
    return [
        {
            "name": cookie.name,
            "value": cookie.value,
            "domain": cookie.domain or '.idealista.com',
            "path": cookie.path,
            "secure": cookie.secure,
            "httpOnly": getattr(cookie, "rest", {}).get("HttpOnly", False),
        }
        for cookie in session.cookies
    ]


def click_accept_cookies(page, logger: ScraperLogger):
    try:
        # Esperar a que el botón de aceptar cookies esté visible
        page.locator('button:has-text("Aceptar")').wait_for(state='visible', timeout=10000)
        # Hacer clic en el botón de aceptar cookies
        page.locator('button:has-text("Aceptar")').click()
        time.sleep(2)
        return True
    except Exception as e:
        logger.error(f"Error al hacer clic en el botón de aceptar cookies: {e}")
        return False


class BaseScraper:
    def __init__(self, base_url):
        self.base_url = base_url
        self.logger = ScraperLogger(self.__class__.__name__).logger

    def generate_property_checksum(self, property_data):
        """Genera un checksum único basado en los datos relevantes de una propiedad"""
        # Concatena los valores relevantes en una cadena
        property_data_to_hash = ''.join(str(value) for value in property_data.values())

        # Genera el hash usando SHA-256
        checksum = hashlib.sha256(property_data_to_hash.encode('utf-8')).hexdigest()

        return checksum

    def basic_req_headers_updated(self, headers_to_update: dict):
        req_headers_updated = self.req_headers
        req_headers_updated.update(headers_to_update)
        return req_headers_updated

    def basic_validate_request(self, resp: Response):
        ERROR_MARKERS = ["Please enable JS and disable any ad blocker", "You've disabled JavaScript in your web browser"]
        if 200 <= resp.status_code < 300:
            if not any(marker in resp.text for marker in ERROR_MARKERS):
                return True
        return False

    def open_browser_with_session(self, session: Session = None, cookies: list = None, url = None, mandatory_pause: int = None):
        captcha_timeout = 600 * 3000 # 10 minutos
        if not session:
            session = requests.Session()
        try:
            with sync_playwright() as p:
                browser = p.firefox.launch(headless=False)  # Abre el navegador en modo no headless
                context = browser.new_context(
                    user_agent=self.req_headers['User-Agent'],
                    viewport={'width': 1366, 'height': 768},
                    locale='es-ES'
                )

                context.add_init_script("""
                            Object.defineProperty(navigator, 'webdriver', {
                                get: () => undefined
                            });
                        """)

                # Cargar las cookies guardadas
                try:
                    if cookies:
                        context.add_cookies(cookies)
                except FileNotFoundError:
                    self.logger.error("No se pudieron guardar las cookies.")
                    return False, session, ''

                # Abrir una nueva página con las cookies cargadas
                page = context.new_page()
                target_url = url if url else self.base_url
                page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
                if "El acceso se ha bloqueado" in page.content():
                    self.logger.error("Se ha bloqueado el acceso a la página por detección de bot")
                    return False, session, ''
                self.logger.info("Página cargada. Buscando CAPTCHA...")
                time.sleep(1)

                captcha_locator = page.locator(
                    'iframe[title*="captcha"], iframe[src*="captcha"], '
                    '[id*="captcha-container"], [class*="captcha"], '
                    '#turnstile-widget, :text("Verifica que eres humano"), '
                    ':text("Please verify you are human")'
                    'captcha-delivery'
                )

                try:
                    captcha_locator.first.wait_for(state='visible', timeout=5000)
                    is_captcha_visible = True
                    self.logger.warning("Captcha detectado. Pendiente de resolución por el usuario..")
                except Exception:
                    is_captcha_visible = False
                    self.logger.info("No se detectó CAPTCHA visible inicialmente.")
                if mandatory_pause:
                    self.logger.info(f"Pausando el script por {mandatory_pause} segundos "
                                     f"para interactuar con la web y evitar bloqueo...")
                    time.sleep(mandatory_pause)
                if is_captcha_visible:
                    self.logger.warning("---------------------------------------------------------")
                    self.logger.warning(f"POR FAVOR, RESUELVE EL CAPTCHA EN LA VENTANA DEL NAVEGADOR PLAYWRIGHT.")
                    self.logger.warning("---------------------------------------------------------")
                    try:
                        self.logger.info("Esperando a que el CAPTCHA se resuelva...")
                        captcha_locator.first.wait_for(state='hidden', timeout=captcha_timeout)
                        self.logger.info("El elemento CAPTCHA ha sido resuelto. Continuando con el scraping...")
                        time.sleep(2)

                    except TimeoutError:
                        self.logger.error("TIMEOUT: El CAPTCHA no se resolvió en el tiempo esperado.")
                        return False, session, ''
                    except Exception as wait_exc:
                         self.logger.error(f"Error inesperado esperando desaparición del CAPTCHA: {wait_exc}")
                         return False, session, ''

                # Función para hacer scroll y esperar nuevo contenido
                def scroll_and_wait():
                    self.logger.info("Haciendo scroll para cargar todo el contenido dinámico...")
                    previous_height = page.evaluate('document.body.scrollHeight')
                    # Hacer scroll gradual en incrementos de 300px
                    for scroll_pos in range(0, previous_height, 300):
                        page.evaluate(f'window.scrollTo(0, {scroll_pos})')
                        time.sleep(0.5 + 0.5 * random())  # Pequeña pausa entre scrolls
                    # Scroll final al fondo
                    page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                    time.sleep(2)  # Esperar a que se cargue el nuevo contenido
                    new_height = page.evaluate('document.body.scrollHeight')
                    return new_height != previous_height

                if page.url.startswith('https://www.fotocasa.es'):
                    if page.url == self.DEFAULT_SEARCH_URL:
                        cookies_validated = False
                        cookies_max_retries = 5
                        n_retry = 0
                        while cookies_validated == False and n_retry < cookies_max_retries:
                            n_retry += 1
                            cookies_validated = click_accept_cookies(page, self.logger)
                    # Hacer scroll hasta que no haya más contenido nuevo
                    has_more_content = True
                    while has_more_content:
                        try:
                            time.sleep(2)
                            has_more_content = scroll_and_wait()
                            # Verificar si hay placeholder de carga
                            placeholders = page.query_selector_all('.sui-PerfDynamicRendering-placeholder')
                            if not placeholders:
                                break
                        except Exception as e:
                            self.logger.warning(f"Error durante el scroll: {str(e)}")
                            break

                time.sleep(10)

                self.logger.info("Obteniendo contenido final de la página y cookies...")
                response_html = self.get_page_content(page)
                cookies_dict = context.cookies()

                browser.close()

            s = requests.Session()
            for cookie in cookies_dict:
                if cookie['name'] == '':
                    continue
                s.cookies.set(
                    cookie['name'],
                    cookie['value'],
                    domain=cookie['domain'],
                    path=cookie.get('path', '/'),
                    expires=cookie.get('expires', None),
                    secure=cookie.get('secure', False),
                    rest={'HttpOnly': cookie.get('HttpOnly', False)}
                    # sameSite=cookie.get('sameSite', None)
                )
        except Exception as exc:
             self.logger.error(f"Couldn't open browser/handle session. HANDLED EXCEPTION -> {exc}")
             # Intenta cerrar el navegador si aún existe en caso de excepción general
             try:
                 if 'browser' in locals() and browser.is_connected():
                     browser.close()
             except Exception:
                 pass
             return False, s, ''
        return True, s, response_html

    def get_page_content(self, page, max_attempts=10, delay=3):
        for attempt in range(max_attempts):
            try:
                # Intentar obtener el contenido
                content = page.content()
                self.logger.info(f"Contenido obtenido exitosamente en el intento #{attempt + 1}.")
                return content
            except Exception as e:
                # Registrar el intento fallido y esperar antes de reintentar
                self.logger.warning(f"Intento #{attempt + 1} de obtener el contenido del navegador fallido: {e}")
                time.sleep(delay)
        self.logger.error(f"Se alcanzó el número máximo de intentos ({max_attempts}) "
                          "para obtener el contenido del navegador")
        return None

    def normalize_price(self, price_str):
        # Convierte el precio a un número eliminando símbolos y espacios
        return int(price_str.replace('€', '').replace(',', '').strip())

    def normalize_data(self, data_parsed):
        unique_property = False
        if not isinstance(data_parsed, list):
            properties_parsed = [data_parsed]
            unique_property = True
        else:
            properties_parsed = data_parsed
        for property_parsed in properties_parsed:
            if property_parsed.municipality == "San Agustin de Guadalix":
                property_parsed.municipality = "San Agustín del Guadalix"
            elif property_parsed.municipality.endswith("apital"):
                property_parsed.municipality = property_parsed.municipality.split()[0]  # Madrid
            elif property_parsed.municipality.endswith("(Madrid)"):
                property_parsed.municipality = property_parsed.municipality.replace("(Madrid)", "")

            if property_parsed.neighborhood:
                if " - " in property_parsed.neighborhood:
                    # Si hay un guón con espacios, eliminar los espacios
                    property_parsed.neighborhood = property_parsed.neighborhood.replace(" - ", "-").strip()

        if unique_property:
            return properties_parsed[0]

        return properties_parsed
