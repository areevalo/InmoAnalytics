import datetime
import time
import random
from urllib.parse import urljoin

import pandas
import requests

from custom_types import PropertyFeatures
from database.db_funcs import add_to_batch
from . import parse_helpers
from scrapers.base_scraper import BaseScraper, extract_cookies_from_session

# Definir la URL de búsqueda en Idealista
base_url = "https://www.idealista.com"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"

req_headers = {
    "User-Agent": USER_AGENT,
    "Host": "www.idealista.com",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3"
}

req_headers_2 = {
    "Host": "www.idealista.com",
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Connection": "keep-alive",
    "Referer": "https://www.idealista.com/venta-viviendas/madrid-provincia/",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Priority": "u=0, i"
}


class IdealistaScraper(BaseScraper):
    DEFAULT_SEARCH_URL = "https://www.idealista.com/venta-viviendas/madrid-provincia/con-sin-inquilinos/?ordenado-por=fecha-publicacion-desc"

    def __init__(self):
        super().__init__(base_url)
        self.req_headers = req_headers
        self.proxies = {
            'http': 'http://102.38.7.110:1972',
            'https': 'http://102.38.7.110:1972'
        }
        self.proxies = {}

    def scrape(self):
        self.logger.info("Empezando scraping en Idealista...")
        try:
            session = requests.Session()
            # ok, session, resp_init_html_content = self.open_browser_with_session(url="https://www.idealista.com/venta-viviendas/madrid-provincia/")
            # TODO: poner la URL por pantalla
            # req_init_url = input("Introduzca la URL de la búsqueda de idealista que quiere procesar:")
            # if req_init_url == "":
            #     req_init_url = "https://www.idealista.com/venta-viviendas/madrid-provincia/con-sin-inquilinos/?ordenado-por=fecha-publicacion-desc"

            req_init_url = self.DEFAULT_SEARCH_URL
            self.logger.info("Proceso iniciado a {}".format(datetime.datetime.now()))
            # Hacer la solicitud HTTP y obtener el HTML inicial
            resp_init = session.get(
                url=req_init_url,
                headers=self.req_headers,
                proxies=self.proxies
            )
            html_content = resp_init.content
            if not resp_init.status_code == 200:
                cookies = extract_cookies_from_session(session)
                ok, session, html_content = self.open_browser_with_session(cookies=cookies, url=req_init_url)
            resp_next_page_content = None

            scraped_properties = []  # type: List[PropertyFeatures]
            num_next_page = None
            for num_page in range(1, 200):
                num_page = num_next_page if num_next_page else num_page
                page_scraped_properties = []
                if resp_next_page_content:
                    html_content = resp_next_page_content
                properties_parsed = parse_helpers.get_properties(html_content, base_url)
                if properties_parsed:
                    properties_parsed = self.normalize_data(properties_parsed)

                for ix, property_parsed in enumerate(properties_parsed):
                    time.sleep(3 + 2 * random.random())
                    self.logger.info("Obteniendo datos de la vivienda {} de la página {}...".format(ix + 1, num_page))

                    # Hacer una solicitud HTTP por cada una de las propiedades a procesar
                    resp_property = session.get(
                        url=property_parsed.url,
                        headers=self.req_headers,
                        proxies=self.proxies
                    )
                    resp_property_content = resp_property.content
                    ok = self.basic_validate_request(resp_property)
                    if not ok:
                        # TODO: verificar funcionamiento del reintento
                        self.logger.error(f"Error en la petición de la vivienda #{ix}. Reintentando con Playwright...")
                        cookies = extract_cookies_from_session(session)
                        ok, session, resp_property_content = self.open_browser_with_session(session, cookies, property_parsed.url)
                        # return False

                    property_data_parsed = parse_helpers.get_property_data(resp_property_content, self.logger)
                    if not property_data_parsed:
                        self.logger.error(f"No se han podido obtener los datos de la propiedad #{ix + 1}. "
                                          f"Omitiendo y pasando a siguiente propiedad...")
                        continue
                    # TODO: pasar a parse_helpers
                    property_data_to_generate_checksum = {
                        "neighborhood": property_parsed.neighborhood,
                        "municipality": property_parsed.municipality,
                        "floor_level": property_data_parsed.floor_level,
                        "rooms": property_data_parsed.rooms,
                        "baths": property_data_parsed.baths,
                        "area": property_data_parsed.area,
                    }

                    checksum = self.generate_property_checksum(property_data_to_generate_checksum)
                    property_parsed.checksum = checksum
                    property_data_parsed.property = property_parsed
                    page_scraped_properties.append(property_data_parsed)
                # end for properties_parsed
                add_to_batch(page_scraped_properties, self.logger)
                # Listado con total de propiedades scrapeadas
                scraped_properties.extend(page_scraped_properties)

                if "Siguiente" in str(html_content):
                    num_next_page = None
                    time.sleep(3 + 5 * random.random())
                    # if not resp_next_page_content:
                    #     num_next_page = input("¿Desea seguir el flujo normal de descarga? En caso contrario introduzca el "
                    #                           "número de página desde el que desea scrapear")
                    next_page_url = parse_helpers.get_next_page_path(html_content, num_next_page, self.logger)
                    req_next_page_url = urljoin(self.base_url, next_page_url)
                    resp_next_page = session.get(
                        url=req_next_page_url,
                        headers=self.req_headers
                    )
                    num_next_page = num_page + 1 if not num_next_page else int(num_next_page)

                    resp_next_page_content = resp_next_page.content
                    ok = self.basic_validate_request(resp_next_page)
                    if not ok or num_next_page % 50 == 0:
                        # Abrir navegador Playwright en caso de error al pasar a siguiente página o cada 50 páginas
                        self.logger.error(f"Error en la petición de la página #{num_next_page}. Reintentando con Playwright...")
                        # cookies = extract_cookies_from_session(session)
                        ok, session, resp_next_page_content = self.open_browser_with_session(url=req_next_page_url, mandatory_pause=300)
                    self.logger.info("Procesando la página {} ({})...".format(num_next_page, req_next_page_url))
                    continue
                else:
                    self.logger.info("No hay más páginas para procesar")
                    break

            self.logger.info("Proceso finalizado a {}".format(datetime.datetime.now()))

        except Exception as e:
            self.logger.error(f"Error en el proceso de scraping: {e}")