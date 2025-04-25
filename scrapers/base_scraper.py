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


class BaseScraper:
    def __init__(self, base_url):
        self.base_url = base_url
        self.logger = ScraperLogger(self.__class__.__name__).logger

    def generate_property_checksum(self, property_data):
        """
        Genera un checksum único basado en los datos relevantes de una propiedad.

        :returns: checksum generado usando SHA-256.
        """
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
        if 200 <= resp.status_code < 300:
            if "Please enable JS and disable any ad blocker" not in resp.text:
                return True
        return False

    def open_browser_with_session(self, session: Session = None, cookies: list = None, url = None):
        captcha_timeout = 600 * 1000 # 10 minutos
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

                self.logger.info("Página cargada. Buscando CAPTCHA...")
                time.sleep(2)

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
                    previous_height = page.evaluate('document.body.scrollHeight')
                    # Hacer scroll gradual en incrementos de 300px
                    for scroll_pos in range(0, previous_height, 300):
                        page.evaluate(f'window.scrollTo(0, {scroll_pos})')
                        time.sleep(0.25 + 0.5 * random())  # Pequeña pausa entre scrolls
                    # Scroll final al fondo
                    page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                    time.sleep(2)  # Esperar a que se cargue el nuevo contenido
                    new_height = page.evaluate('document.body.scrollHeight')
                    return new_height != previous_height

                if page.url.startswith('https://www.fotocasa.es'):
                    # Hacer scroll hasta que no haya más contenido nuevo
                    has_more_content = True
                    while has_more_content:
                        try:
                            has_more_content = scroll_and_wait()
                            # Verificar si hay placeholder de carga
                            placeholders = page.query_selector_all('.sui-PerfDynamicRendering-placeholder')
                            if not placeholders:
                                break
                        except Exception as e:
                            self.logger.warning(f"Error durante el scroll: {str(e)}")
                            break

                    # Esperar a que desaparezcan todos los placeholders (propiedades generadas dinámicamente)
                    page.wait_for_selector('.sui-PerfDynamicRendering-placeholder', state='detached', timeout=10000)

                time.sleep(10)

                self.logger.info("Obteniendo contenido final de la página y cookies...")
                response_html = page.content()
                cookies_dict = context.cookies()
                for key in ['didomi_token', '__rtbh.lid', '__rtbh.uid', 'euconsent-v2']:
                    value = page.evaluate(f"window.localStorage.getItem('{key}')")
                    if value:
                        cookie_dict = {
                            "name": key,
                            "value": value,
                            "domain": '.idealista.com' if not key.startswith('__') else 'www.idealista.com',
                            "path": '/',
                            "httpOnly": False,
                        }
                        cookies_dict.append(cookie_dict)

                browser.close()
            jar = requests.cookies.RequestsCookieJar()
            for cookie in cookies_dict:
                jar.set(
                    name=cookie['name'],
                    value=cookie['value'],
                    domain=cookie['domain'],
                    path=cookie.get('path', '/'),
                    secure=cookie.get('secure', False)
                )
            session.cookies = jar
        except Exception as exc:
             self.logger.error(f"Couldn't open browser/handle session. HANDLED EXCEPTION -> {exc}")
             # Intenta cerrar el navegador si aún existe en caso de excepción general
             try:
                 if 'browser' in locals() and browser.is_connected():
                     browser.close()
             except Exception:
                 pass
             return False, session, ''
        return True, session, response_html

    def fetch_html(self, url):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return BeautifulSoup(response.text, 'html.parser')
        except requests.exceptions.RequestException as e:
            print(f"Error fetching URL {url}: {e}")
            return None

    def normalize_price(self, price_str):
        # Convierte el precio a un número eliminando símbolos y espacios
        return int(price_str.replace('€', '').replace(',', '').strip())

    def insert_into_database(self, data, table_name, db_connection):
        # Inserta datos normalizados en la base de datos
        cursor = db_connection.cursor()
        placeholders = ', '.join(['%s'] * len(data))
        query = f"INSERT INTO {table_name} VALUES ({placeholders})"
        cursor.execute(query, tuple(data.values()))
        db_connection.commit()

    def normalize_data(self, data):
        # TODO: Implementar lógica común para normalizar datos (ejemplo: convertir precios a números)
        pass