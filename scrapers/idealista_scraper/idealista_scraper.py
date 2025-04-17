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

# Definir la URL de búsqueda en Fotocasa
base_url = "https://www.idealista.com"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
# USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:138.0) Gecko/20100101 Firefox/137.0"
s = requests.Session()
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
    def __init__(self):
        super().__init__(base_url)
        self.req_headers = req_headers
        self.proxy = {
            'server': 'https://83.218.186.22:5678'
        }

    def scrape(self):
        self.logger.info("Starting scraping for Idealista")
        # session = requests.session()
        ok, session, resp_init_html_content = self.open_browser_with_session(url="https://www.idealista.com/venta-viviendas/madrid-provincia/")
        # resp_init = s.get(
        #     url=self.base_url,
        #     headers=self.req_headers
        # )
        # if not resp_init.status_code == 200:
        #     cookies = extract_cookies_from_session(s)
        #     self.open_browser_with_session(cookies)
        # TODO: poner la URL por pantalla
        busqueda_idealista_url = input("Introduzca la URL de la búsqueda de idealista que quiere procesar:")
        if busqueda_idealista_url == "":
            busqueda_idealista_url = "https://www.idealista.com/venta-viviendas/madrid-provincia/con-sin-inquilinos/?ordenado-por=fecha-publicacion-desc"

        self.logger.info("Proceso iniciado a {}".format(datetime.datetime.now()))

        # Hacer la solicitud HTTP y obtener el HTML
        resp_busqueda_idealista = session.get(
            url=busqueda_idealista_url,
            headers=self.req_headers
            # proxies=self.proxy
        )
        html_content = resp_busqueda_idealista.content
        if not resp_busqueda_idealista.status_code == 200:
            cookies = extract_cookies_from_session(session)
            ok, session, html_content = self.open_browser_with_session(cookies=cookies, url=busqueda_idealista_url)
        resp_next_page_content = None
        scraped_properties = []  # type: List[PropertyFeatures]

        for page in range(1, 100):
            page_scraped_properties = []
            if resp_next_page_content:
                html_content = resp_next_page_content
            properties_parsed = parse_helpers.get_properties(html_content, base_url)

            for ix, property_parsed in enumerate(properties_parsed):
                time.sleep(3 + 2 * random.random())
                resp_casa = session.get(
                    url=property_parsed.url,
                    headers=self.req_headers,
                    # proxies=self.proxy
                )
                resp_casa_content = resp_casa.content
                ok = self.basic_validate_request(resp_casa)
                if not ok:
                    cookies = extract_cookies_from_session(session)
                    ok, session, resp_casa_content = self.open_browser_with_session(s, cookies, property_parsed.url)
                    self.logger.error(f"Error en la petición de la vivienda #{ix}. Abortando proceso...")
                    # return False
                self.logger.info("Obteniendo datos de la vivienda {} de la página {}...".format(ix + 1, page))

                # TODO: pasar a parse_helpers
                propery_data_parsed = parse_helpers.get_property_data(resp_casa_content, property_parsed)
                property_data_to_generate_checksum = {
                    "neighborhood": property_parsed.neighborhood,
                    "municipality": property_parsed.municipality,
                    "floor_level": propery_data_parsed.floor_level,
                    "rooms": propery_data_parsed.rooms,
                    "baths": propery_data_parsed.baths,
                    "area": propery_data_parsed.area,
                }

                checksum = self.generate_property_checksum(property_data_to_generate_checksum)
                property_parsed.checksum = checksum
                propery_data_parsed.property = property_parsed
                page_scraped_properties.append(propery_data_parsed)
            # end for properties_parsed
            add_to_batch(page_scraped_properties, self.logger)
            scraped_properties.extend(page_scraped_properties)

            if "Siguiente" in str(html_content):

                num_init_page = None
                # TODO: REVISAR QUE VALOR COOKIE O HEADER O ALMACENAMIENTO LOCAL CAMBIA EN EL CAMBIO DE PAGINA / revisar por qué la segunda página nunca me pide captcha
                time.sleep(3 + 5 * random.random())
                if not resp_next_page_content:
                    num_init_page = input("Desea seguir el flujo normal de descarga? En caso contrario introduzca el "
                                          "número de página desde el que desea scrapear")
                next_page_url = parse_helpers.obtener_siguiente_pag(html_content, num_init_page)
                req_next_page_url = urljoin(self.base_url, next_page_url)
                resp_next_page = s.get(
                    url=req_next_page_url,
                    headers=self.req_headers
                )
                resp_next_page_content = resp_next_page.content
                ok = self.basic_validate_request(resp_next_page)
                if not ok or ix % 50 == 0:
                    cookies = extract_cookies_from_session(session)
                    ok, session, resp_next_page_content = self.open_browser_with_session(s, cookies, req_next_page_url)
                self.logger.info("Pasando a la página {} ({})...".format(page + 1, req_next_page_url))
                continue
            else:
                self.logger.info("No hay más páginas para procesar")
                break

        self.logger.info("Proceso finalizado a {}".format(datetime.datetime.now()))

        # Crear el DataFrame de Pandas y exportarlo a un archivo Excel
        self.logger.info("Creando Excel con los datos de viviendas procesadas")
        # Convertir los diccionarios en filas de datos
        data = [list(p.values()) for p in scraped_properties]

        # Crear un DataFrame a partir de las filas de datos
        df = pandas.DataFrame(data, columns=list([0].keys()))

        # Escribir el DataFrame en un archivo Excel
        writer = pandas.ExcelWriter('idealista_viviendas_pinto2.xlsx', engine='xlsxwriter')
        df.to_excel(writer, index=False)
        writer._save()
