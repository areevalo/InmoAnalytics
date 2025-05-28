import datetime
import time
import random
from encodings.punycode import selective_find
from urllib.parse import urljoin

import pandas
import requests
from bs4 import BeautifulSoup

from custom_types import PropertyFeatures
from database.db_funcs import add_to_batch
from . import parse_helpers
from scrapers.base_scraper import BaseScraper, extract_cookies_from_session


class FotocasaScraper(BaseScraper):
    BASE_URL = "https://www.fotocasa.es/es/"
    DEFAULT_SEARCH_URL = "https://www.fotocasa.es/es/comprar/viviendas/madrid-provincia/todas-las-zonas/l?sortType=publicationDate"
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"

    def __init__(self):
        super().__init__(self.BASE_URL)
        self.req_headers = {
            "User-Agent": self.USER_AGENT,
            "Host": "www.fotocasa.es"
        }
        self.proxies = {
            'http': 'http://102.38.7.110:1972',
            'https': 'http://102.38.7.110:1972'
        }
        self.proxies = {}

    def scrape(self):
        self.logger.info("Empezando scraping en Fotocasa...")
        try:
            # session = requests.Session()
            req_init_url = self.DEFAULT_SEARCH_URL
            ok, session, resp_init_html_content = self.open_browser_with_session(url=req_init_url)
            # TODO: poner la URL por pantalla
            # req_init_url = input("Introduzca la URL de la búsqueda de Fotocasa que quiere procesar:") or self.DEFAULT_SEARCH_URL

            self.logger.info("Proceso iniciado a {}".format(datetime.datetime.now()))
            # Hacer la solicitud HTTP y obtener el HTML inicial
            # resp_init = session.get(
            #     url=req_init_url,
            #     headers=self.req_headers,
            #     proxies=self.proxies
            # )
            html_content = resp_init_html_content
            # if not resp_init.status_code == 200:
            #     self.logger.error(f"Error en la petición inicial. Reintentando con Playwright...")
            #     cookies = extract_cookies_from_session(session)
            #     ok, session, html_content = self.open_browser_with_session(cookies=cookies, url=req_init_url)
            resp_next_page_content = None

            scraped_properties = []  # type: List[PropertyFeatures]
            for page in range(1, 100):
                page_scraped_properties = []
                if resp_next_page_content:
                    html_content = resp_next_page_content
                properties_parsed = parse_helpers.get_properties(html_content, self.BASE_URL)

                for ix, property_parsed in enumerate(properties_parsed):
                    if property_parsed.price is None:
                        self.logger.warning(f"No se ha podido obtener el precio de la propiedad #{ix + 1}. "
                                            f"Omitiendo y pasando a siguiente propiedad...")
                        continue
                    time.sleep(2 + 1 * random.random())
                    self.logger.info(f"Obteniendo datos de la vivienda {ix + 1} de la página {page}...")

                    # Hacer una solicitud HTTP por cada una de las propiedades a procesar
                    resp_property = session.get(
                        url=property_parsed.url,
                        headers=self.req_headers,
                        proxies=self.proxies
                    )
                    resp_property_content = resp_property.content
                    ok = self.basic_validate_request(resp_property)
                    if not ok:
                        self.logger.error(f"Error en la petición de la vivienda #{ix}. Reintentando con Playwright...")
                        cookies = extract_cookies_from_session(session)
                        ok, session, resp_property_content = self.open_browser_with_session(session, cookies, property_parsed.url)
                        # return False

                    property_parsed_updated, property_data_parsed = parse_helpers.get_property_data(
                        resp_property_content,
                        property_parsed,
                        self.logger
                    )
                    if not property_parsed_updated or not property_data_parsed:
                        self.logger.error(f"No se han podido obtener los datos de la propiedad #{ix + 1}. "
                                          f"Omitiendo y pasando a siguiente propiedad...")
                        continue
                    property_parsed_updated = self.normalize_data(property_parsed_updated)
                    # TODO: pasar a parse_helpers
                    property_data_to_generate_checksum = {
                        "neighborhood": property_parsed_updated.neighborhood,
                        "municipality": property_parsed_updated.municipality,
                        "floor_level": property_data_parsed.floor_level,
                        "rooms": property_data_parsed.rooms,
                        "baths": property_data_parsed.baths,
                        "area": property_data_parsed.area,
                    }
                    checksum = self.generate_property_checksum(property_data_to_generate_checksum)
                    property_parsed_updated.checksum = checksum
                    property_data_parsed.property = property_parsed_updated
                    page_scraped_properties.append(property_data_parsed)
                # end for properties_parsed
                add_to_batch(page_scraped_properties, self.logger)
                # Listado con total de propiedades scrapeadas
                scraped_properties.extend(page_scraped_properties)

                if "Siguiente" in str(html_content):
                    num_init_page = None
                    time.sleep(3 + 2 * random.random())

                    if not resp_next_page_content:
                        num_init_page = input("¿Desea seguir el flujo normal de descarga? En caso contrario introduzca el "
                                              "número de página desde el que desea scrapear")
                    next_page_path_url = parse_helpers.get_next_page_path(html_content, num_init_page, page, self.logger)
                    req_next_page_url = urljoin(self.base_url, next_page_path_url)
                    self.logger.info("Pasando a la página {} ({})...".format(page + 1, req_next_page_url))
                    cookies = extract_cookies_from_session(session)
                    ok, session, resp_next_page_content = self.open_browser_with_session(session, cookies,
                                                                                         req_next_page_url)
                    if not ok:
                        # Abrir navegador Playwright en caso de error al pasar a siguiente página
                        cookies = extract_cookies_from_session(session)
                        ok, session, resp_next_page_content = self.open_browser_with_session(session, cookies, req_next_page_url)

                    continue
                else:
                    self.logger.info("No hay más páginas para procesar")
                    break

            self.logger.info("Proceso finalizado a {}".format(datetime.datetime.now()))

        except Exception as e:
            # TODO: cuando se cierra el navegador, salta excepción en vez de reintentar
            self.logger.error("Error en el proceso de scraping: {}".format(e))