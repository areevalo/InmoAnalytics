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

# Definir la URL de búsqueda en Fotocasa
base_url = "https://www.fotocasa.es/es/"

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
req_headers = {
    "User-Agent": USER_AGENT,
    "Host": "www.fotocasa.es"
}

class FotocasaScraper(BaseScraper):
    def __init__(self):
        super().__init__(base_url)
        self.req_headers = req_headers
        self.proxies = {
            'http': 'http://102.38.7.110:1972',
            'https': 'http://102.38.7.110:1972'
        }
        self.proxies = {}

    def scrape(self):
        self.logger.info("Empezando scraping en Fotocasa...")
        session = requests.Session()
        # ok, session, resp_init_html_content = self.open_browser_with_session(url="https://www.idealista.com/venta-viviendas/madrid-provincia/")
        # TODO: poner la URL por pantalla
        req_init_url = input("Introduzca la URL de la búsqueda de Fotocasa que quiere procesar:")
        if req_init_url == "":
            req_init_url = "https://www.fotocasa.es/es/comprar/viviendas/madrid-provincia/todas-las-zonas/l?sortType=publicationDate"

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
        for page in range(1, 100):
            page_scraped_properties = []
            if resp_next_page_content:
                html_content = resp_next_page_content
            properties_parsed = parse_helpers.get_properties(html_content, base_url)

            for ix, property_parsed in enumerate(properties_parsed):
                time.sleep(3 + 2 * random.random())
                self.logger.info("Obteniendo datos de la vivienda {} de la página {}...".format(ix + 1, page))

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
                    ok, session, resp_property_content = self.open_browser_with_session(s, cookies, property_parsed.url)
                    # return False

                # TODO: pasar a parse_helpers
                propery_data_parsed = parse_helpers.get_property_data(resp_property_content, property_parsed)
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
            # Listado con total de propiedades scrapeadas
            scraped_properties.extend(page_scraped_properties)

            if "Siguiente" in str(html_content):
                num_init_page = None
                # TODO: REVISAR QUE VALOR COOKIE O HEADER O ALMACENAMIENTO LOCAL CAMBIA EN EL CAMBIO DE PAGINA / revisar por qué la segunda página nunca me pide captcha
                time.sleep(3 + 5 * random.random())
                if not resp_next_page_content:
                    num_init_page = input("¿Desea seguir el flujo normal de descarga? En caso contrario introduzca el "
                                          "número de página desde el que desea scrapear")
                next_page_url = parse_helpers.get_next_page_path(html_content, num_init_page)
                req_next_page_url = urljoin(self.base_url, next_page_url)
                resp_next_page = session.get(
                    url=req_next_page_url,
                    headers=self.req_headers
                )
                resp_next_page_content = resp_next_page.content
                ok = self.basic_validate_request(resp_next_page)
                if not ok or ix % 49 == 0:
                    # Abrir navegador Playwirght en caso de error al pasar a siguiente página o cada 50 páginas
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
        writer = pandas.ExcelWriter('idealista_viviendas.xlsx', engine='xlsxwriter')
        df.to_excel(writer, index=False)
        writer._save()


# Hacer la solicitud HTTP y obtener el HTML
resp_init = s.get(
    url=url,
    headers=req_headers
)
req_headers_cookies = req_headers
req_headers_cookies['Origin'] = "https://www.fotocasa.es"
req_headers_cookies['Referer'] = "https://www.fotocasa.es/"
resp_cookies = s.options(
    url="https://api.privacy-center.org/v1/events",
    headers=req_headers
)
busqueda_fotocasa_url = "https://www.fotocasa.es/es/comprar/viviendas/madrid-provincia/todas-las-zonas/ascensor/l?conservationStatusIds=3%3B8%3B1%3B2&maxPrice=275000&minBathrooms=2&minRooms=3&propertySubtypeIds=1%3B2%3B6%3B7%3B8%3B54%3B3%3B9%3B5&searchArea=jnjm9q--iBmzlBr0V03sKr0V03sKr0V_tzEr0Vrw0Er0Vzm6pConViz2sKr0Vuqy4Br0V03sKs8yD03sKs8yDrw0Er0Vrw0Er0V9hlBr0V9hlBr0VmzlBtjiG9hlBqkqxCk-zEzw1Cq5kBr0Vq5kBr0Vk-zEr0Vq5kBr0Vk-zEntyDxqlBr0Vq5kBntyDxqlBr0Vq5kBonVk-zEr0Vq5kBr0VntyDr0VxqlBr0Vq5kBr0VhzpOr0VntyD6q2Cq5kBr0VxqlB0nuiMq5kB6uoxDq5kBr0VxqlBtjiGq5kBonVq5kB-u2rFxqlBi8gGq5kB1p3Kq5kB4kijC9hlBonV9hlBr0VmzlBr0V9hlBr0Vrw0Ezw1C9hlBr0Vl_xDmzlB6q2C9hlBr0V9hlBonVmzlBr0Vs8yDonVrw0Er0V_tzE6q2Crw0El_xDrw0Er0Vrw0Es8yDrw0E50oOmzlBs8yD03sKs8yD9hlBzu5Is8yDrw0Es8yDrw0El_xDrw0Ei_6Is8yDhpuSu8yDyk5c56zD08wna5tV9hlBjvxDmzlB5tV9hlB5tV9hlBqtyD9hlB5tVotyDmzlB4gV9hlBzvrO5tV9hlB4gV9hlB5tVrw0E5tV9hlBxj1Crw0EotyD5tVrw0E4gV9hlB5tVrw0E5tV9hlB4gVrw0E5tVotyD9hlB5tVmzlBz2nOmzlB5tV9hlBjvxDmzlB5tV9hlB5tVotyDrw0E4gV9hlBzrzD_tzE291Crw0EjvxDmzlBotyD9hlBzrzD9hlB5tV9hlBqtyD9hlBotyDrw0E5tVotyDrw0EjvxDrw0E5tV9hlBzrzD9hlBizpO_tzE5tV03sK5tV03sKzrzD9hlB924Iu00hHonVmzlBr0V9hlBr0V9hlBzw1CmzlB6q2C9hlBr0V9hlBi8gGmzlBi8gG9hlB1p3Ks8yD9hlB1p3KmzlB1p3K9hlBq5v2Eq5kBr0VxqlBr0Vq5kBr0Vq5kBzw1Cq5kBr0Vk-zEonVq5kBr0VxqlBr0Vmw1mJonVk-zEr0Vq5kBhzpOq5kBr0Vq5kBr0VxqlBy2nOxqlBy2nOxqlBhom5Bq5kByrzDonVq5kBr0Vq5kBr0VxqlBonVq5kB6q2Cq5kBzw1Ck-zEi8gGq5kBi8gGxqlBi8gGq5kBonVq5kB6q2CxqlBzw1Cq5kBzw1Cq5kBzw1CxqlB6q2C79rKonVi2s4Br0Vi2s4Br0V79rKonVk-zEr0Vq5kBivxDk-zE6q2Cq5kBzw1CxqlBonVq5kBr0Vk-zEr0Vq5kBonVq5kBr0VxqlBonVq5kBr0V79rKzw1Cq5kBr0VxqlBmk4wC03sKr0VmzlBonV_tzEzw1Crw0Es8yDmzlBonV03sKr0V9hlBr0V03sKonV03sKs8yD7k8hHm-3I08wna56zD9hlBl_xD03sKr0V03sKu8yD_tzE56zD9hlBl_xDmzlBxu5Irw0Es8yDrw0EqxqO_tzEu8yD_tzE56zD9hlBl_xD9hlB56zD9hlBl_xDrw0Es8yD03sKqxqOrw0El_xDhpuS56zDhpuSogkjBrw0El_xD03sKi_6I9hlB3zyXmzlBm-3Irw0Ei_6Il_xD9hlBi_6IonV9hlBqxqO9hlB56zDonV9hlBr0Vrw0EonVs8yDonV9hlBi8gGu8yDr0V9hlBy20Q9hlBs2_1Bq5kBr0Vq5kBzw1CxqlBjh0Kq5kBq11Kq5kBr0VptyD70-Fq5kBi8gG2mtSonVtrvSr0Vq5kBivxD79rKonVk-zEr0Vq5kBonVxqlBr0V58yEonVk-zEonVk-zEy2nOtrvSr0V39upBivxDs-0sOhgxD58yE5tVk-zE4gVq5kB5tVxqlB4gV58yExj1CxqlB4gVq5kB5tVk-zEwp0C58yE5tVxqlB4gV58yE5tVxqlB4gV58yE5tVk-zE4gV79rK4gVq5kB5tVtrvS4gV2mtS5tV79rK4gVq5kBt8yD79rKhgxD39upB5tVwv6c4gVq8tvWonVt5mrE4gVk-zE4gVwv6c5tVi2s4B4gV39upBk_xDxp7vWr0Vq5kBonVq5kBzw1ChzpOzw1ChzpOzw1CivxDq5kBzw1CxqlBzw1Cq5kB70-Fq5kBonVxqlBq11KivxDs2_1Bq5kB6-9X9hlBzw1C9hlB56zDw20C9hlBr0Vl_xDonV56zD9hlBonVs8yDonVmzlBonVivtgEr0V9hlBonVl_xDh5rH9hlBr0V70oOzw1Cl_xDr0V9hlBw20CmzlB70-Fs8yDzx7X79rKntyDxqlBonV79rKivxDk-zEy2nOxqlBivxDk-zEr0V0ys7Pt8yDynx-Mn-3I153c4gVk-zEk_xDk-zE4gVhgxDxqlBk_xDq5kB4gV79rKxj1CxqlBhgxD4gVk-zExj1Cq5kBph-Fq5kBt9_pFxqlBxj1Cq5kBph-FhgxD5tVxqlBph-Fq5kB4gVq5kBxj1CxqlBxj1Cq5kB4gVq5kB5tVxqlB4gVq5kB4gVq5kB5tVm_xD5tV58yE4gVxqlB4gVq5kB5tVk-zE4gVq5kB5tVq5kB4gVxqlBt4mO4gVxqlB5tV58yE4gVxqlBxj1C58yE4gVq5kB5tVk-zE4gVhgxDxqlB5tVq5kB4gVq5kB5tVxqlBhgxD5tVq5kB4gVm_xD5tVhgxDq5kB5tVxqlBxj1Cq5kB4gVq5kB5tVv4mO5tVk-zE4gVq5kB60oO5tVq5kBhgxDk-zE5tVq5kBm_xDq5kB4gVq5kBt8yDq5kBhgxDxqlB5tVq5kBhgxDk-zE5tV79rK4gVk-zE5tVq5kBhgxDxqlBk_xDk-zEhgxD2mtS5tVxqlBhgxD79rK5tVi2s4Br0VptyDr0VivxDi8gGivxDqjrHr0VivxDr0VivxDzw1C824Izw1CntyDonVxqlBr0VivxDzw1Cq5kBivxDzw1CxqlBr0Vq5kBonVntyDxqlBonVy2nOonVhzpOr0VivxDonVxqlBr0VivxDr0Vq5kBonVhzpOonVq5kBr0Vk-zEonV79rKonVntyD79rKonVk-zEr0Vk-zEonV58yEonVxqlBntyDq5kBonVk-zEr0VrpijIk_xDxqlB4gVq5kB5tVq5kB4gVxqlB4gVq5kB5tVq5kBxj1CxqlBph-Fq5kBr_t3G9hlBm70KizpO-m-X9hlBw4ugGhgxD5tVq5kBph-FxqlBxj1Cq5kBxj1Cq5kB5tVxqlBxj1Cq5kB4gVq5kB5tVxqlBxj1C58yE4gVxqlBxj1Cq5kBxj1Ck-zEn31Qq5kB_1zQ9hlBxj1CmzlBuogG9hlBm70K9hlB5tVmzlB4gV9hlB5tV9hlBxj1CmzlBotyDrw0E4gV9hlB5tV9hlB4gVrw0E5tV9hlB4gVmzlBxj1C_tzE5tVmzlB5tV03sK4gV9hlB5tV03sK4gVrw0E5tVotyD4gV9hlB5tVmzlB4gV9hlB5tVizpO5tV9hlBph-F9hlBvv2KmzlBxj1C9hlBuogGjvxDuogGmzlBuogG9hlBm3s2EhgxD5tVxqlB5tV58yExj1Ck-zE5tVk-zE4gVq5kB5tV79rK5tVq5kB4gVxqlB5tV58yE5tVk-zExj1Ck-zE5tVq5kB4gVq5kB5tVt8yDq5kB4gVq5kB5tVxqlB5tVq5kB4gVk-zEvv2Kq5kBs1hYk-zE5tVq5kB5tVk-zE4gV58yE5tVxqlB5tV58yE4gVxqlB5tVq5kB5tVk-zE5tVq5kB4gVq5kB5tVq5kB5tVk-zE4gVq5kBvv2K_tzE5tVzrzD_tzE4gVoxwpB5tVv67c5tVhpuS5tV03sK4gVrw0E5tV03sK5tV03sK5tV03sK4gV8sr9Czw1C_tzEr0Vrw0Er0Vzm6pC5tV9hlB5tV9hlB5tVmzlB4gV_tzE5tVmzlB291C9hlB4gV9hlB5tVmzlB291C_tzE114gBq5kBvv2Kq5kB5tVxqlBxj1Cq5kB3vhGq5kBxj1CxqlB5tVq5kBqx7gBq5kBz8n2B03sK5tV9hlB4gVrw0E5tV9hlB5tV9hlB291Crw0E5tV9hlBxj1C03sK5tV03sK5tV03sK5tVhpuS5tVmzlB4gV03sK5tV03sK5tV_tzE291Crw0E5tV9hlB4gVmzlB5tV9hlB5tV9hlB5tVrw0E5tVrw0E5tV9hlB5tVrw0E4gV03sK5tV_tzEzrzD9hlB5tV03sK5tVrw0E5tV_tzE5tVrw0E4gV9hlBzrzD9hlBotyDmzlBotyD9hlB5tVzrzD9hlBzvrO9hlB4gV9hlB5tVmzlBotyD9hlB5tVmzlBotyD5tV9hlB5tVmzlB5tV_tzE5tVqtyD5tV9hlB5tV9hlB291CmzlBgzpOmzlB291C9hlBqxlgB5tV9hlBzrzD5tV_tzE5tVmzlBotyD5tV9hlBotyD5tVrw0E5tVotyDmzlB5tV_tzE5tVoxwpB4gVrw0E5tVrw0E"
resp_busqueda_fotocasa = s.get(
    url=busqueda_fotocasa_url,
    headers=req_headers
)

html_content = resp_busqueda_fotocasa.content



# for

# Analizar el HTML con BeautifulSoup
soup = BeautifulSoup(html_content, "html.parser")

# Extraer los datos de cada anuncio
data = []
for listing in soup.find_all("div", class_="re-CardPackPadding"):
    title = listing.find("h3", class_="re-CardPackTitle").text.strip()
    description = listing.find("p", class_="re-CardPackDescription").text.strip()
    price = listing.find("span", class_="re-CardPackPrice").text.strip()
    location = listing.find("p", class_="re-CardPackLocation").text.strip()
    data.append({"Título": title, "Descripción": description, "Precio": price, "Ubicación": location})

# Crear el DataFrame de Pandas y exportarlo a un archivo Excel
df = pandas.DataFrame(data)
df.to_excel("fotocasa_listings.xlsx", index=False)