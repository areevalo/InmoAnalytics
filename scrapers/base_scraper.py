import hashlib

import json
import time

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

        Args:
            property_data (dict): Diccionario con los datos clave de la propiedad.

        Returns:
            str: Checksum generado usando SHA-256.
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

    def open_browser_with_session(self, session: Session = None, cookies: dict = None, url = None):
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
                page.goto(self.base_url) if not url else page.goto(url)  # Cambia por la URL del sitio donde ocurre el CAPTCHA

                time.sleep(10)
                # TODO: pausar de otra manera que no sea con punto de interrupción (solo cuando pida captcha)
                # Pausar para resolver el CAPTCHA manualmente
                time.sleep(0.1)
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
            self.logger.error(f"Couldn't open headless browser. HANDLED EXCEPTION -> {exc}")
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
        # Implementa lógica común para normalizar datos (ejemplo: convertir precios a números)
        pass
