import re
import time
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from custom_types import PropertyFeatures, Property
from scrapers.constants import UNDERFLOOR_HEATING_KEYWORDS, OCCUPIED_PROPERTY_KEYWORDS, \
    BARE_OWNERSHIP_PROPERTY_KEYWORDS, RENTED_PROPERTY_KEYWORDS, AUCTION_PROPERTY_KEYWORDS, STREET_KEYWORDS
from utils.scraper_logger import ScraperLogger

FLOOR_LEVEL_KEYWORDS = [
    "planta", "entreplanta", "bajo", "sótano", "principal"
]

def get_location_from_title(title: str):
    municipality = neighborhood = street = None
    street_start_position = title.find(' en ')

    if street_start_position > -1:
        street_start_position += len(' en ')
        after_en = title[street_start_position:].strip()
        parts = [p.strip() for p in after_en.split(',')]

        if len(parts) == 1:
            municipality = parts[0]
        elif len(parts) == 2:
            if any(keyword in parts[0].lower() for keyword in STREET_KEYWORDS):
                street = parts[0]
            else:
                neighborhood = parts[0]
            municipality = parts[1]
        else:
            if parts[-2].isdigit() or 's/n' in parts[-2].lower():
                # El penúltimo es número o s/n, así que lo anterior es la calle
                street = ', '.join(parts[:-1])
                neighborhood = None
                municipality = parts[-1]
            else:
                street = ', '.join(parts[:-2])
                neighborhood = parts[-2]
                municipality = parts[-1]

        # Capitalizar resultados
        street = street[0].upper() + street[1:] if street else None
        neighborhood = neighborhood[0].upper() + neighborhood[1:] if neighborhood else None
        municipality = municipality[0].upper() + municipality[1:] if municipality else None

        return municipality, neighborhood, street


def get_properties(resp_casas_content: bytes, base_url: str):
    # Analizar el HTML con BeautifulSoup
    soup = BeautifulSoup(resp_casas_content, "html.parser")

    # Extraer los datos de cada anuncio
    properties = []  # type: List[Property]

    for listing in soup.find_all("article", class_="item"):
        title = listing.find("a", class_="item-link").text.strip()
        description = listing.find("div", class_="item-description").text.strip()
        price = listing.find("span", class_="item-price").text.strip()
        url_path = listing.find("a", class_="item-link").get('href')
        municipality, neighborhood, street = get_location_from_title(title)

        property_basic_data = Property(
            url=urljoin(base_url, url_path),
            price=int(price.replace('.', '').rstrip("€")),
            municipality=municipality,
            neighborhood=neighborhood,
            street=street,
            origin="Idealista",
            checksum=""
        )

        properties.append(property_basic_data)

    # end for listings

    return properties


def get_property_data(resp_casa_content: bytes, logger: ScraperLogger):
    """Procesa el contenido HTML de un anuncio inmobiliario para extraer datos estructurados.
    Si algún dato no está disponible, se asignan valores por defecto"""

    # Analizar el HTML con BeautifulSoup
    soup = BeautifulSoup(resp_casa_content, "html.parser")
    property_features = PropertyFeatures()

    try:
        price = soup.find("span", class_="price-container").text.strip()
        # Valores por defecto para una posible comparación de precios
        property_features.property = Property(
            url=soup.find("link", rel="canonical").get('href'),
            price=int(price.replace('.', '').rstrip("€")),
            municipality=None,
            neighborhood=None,
            street=None,
            origin="Idealista",
            checksum=""
        )
        # Extraer del título el tipo de vivienda
        title = soup.find("span", class_="main-info__title-main")
        home_type = title.text.split(' en ')[0].strip()
        property_features.type_of_home = home_type if home_type != "Casa o chalet independiente" else "Casa o chalet"
        # Extraer la sección principal de los datos
        main_data = soup.find("section", class_="detail-info")
        if not main_data:
            raise ValueError("No se encontró la sección principal de datos.")

        # Extraer calificación energética (si está disponible)
        energy_element = soup.find('span', text=re.compile(r'\d+ kWh/m² año'))
        if energy_element:
            energy_class = energy_element.get('class')[0]
            property_features.energy_calification = energy_class.split("-")[-1].upper().strip()
        property_description = main_data.find("div", class_="comment")
        if property_description:
            if any(keyword in property_description.text.lower() for keyword in UNDERFLOOR_HEATING_KEYWORDS):
                property_features.underfloor_heating = True
                # Análisis de estado de la propiedad
            if any(keyword in property_description.text.lower() for keyword in OCCUPIED_PROPERTY_KEYWORDS):
                property_features.ownership_status = "Ocupada ilegalmente"
            if any(keyword in property_description.text.lower() for keyword in BARE_OWNERSHIP_PROPERTY_KEYWORDS):
                property_features.ownership_status = "Nuda propiedad"
            if any(keyword in property_description.text.lower() for keyword in RENTED_PROPERTY_KEYWORDS):
                property_features.ownership_status = "Alquilada"
            if any(keyword in property_description.text.lower() for keyword in AUCTION_PROPERTY_KEYWORDS):
                property_features.ownership_status = "Subastada"

        # Extraer detalles adicionales
        detalles_datos_elements = main_data.find_all("div", class_="details-property")
        if detalles_datos_elements:
            detalles_datos = detalles_datos_elements[-1]
            for fila_datos in detalles_datos.find_all("li"):
                fila_text_str = fila_datos.text.lower()

                # Superficie en m²
                if " m²" in fila_text_str and "parcela" not in fila_text_str:
                    property_features.area = int(fila_text_str.replace('.', '').split()[0])
                    continue

                # Número de habitaciones
                if "habitaciones" in fila_text_str or "habitación" in fila_text_str:
                    property_features.rooms = int(fila_text_str.split()[0]) if fila_text_str.split()[0] != 'sin' else 0
                    continue

                # Número de baños
                if "baño" in fila_text_str:
                    baths_str = fila_text_str.split()[0]
                    property_features.baths = int(baths_str) if baths_str != 'sin' else 0
                    continue

                if "terraza" in fila_text_str:
                    property_features.terrace = True
                    continue

                if "garaje" in fila_text_str and not fila_text_str.endswith("adicionales"):
                    property_features.garage = True
                    continue
                else:
                    pass

                if "trastero" in fila_text_str and not fila_text_str.endswith("adicionales"):
                    property_features.storage_room = True
                    continue
                else:
                    pass

                if "orientación" in fila_text_str:
                    orientation_parts = fila_text_str.split()
                    orientation_list = orientation_parts[1:] if len(orientation_parts) > 1 else []
                    if orientation_list:
                        property_features.orientation = ("".join([x.capitalize() for x in orientation_list]).
                                                         replace(",", "/").strip())
                    continue

                # Año de construcción o estado (obra nueva)
                if "construido en" in fila_text_str:
                    property_features.construction_year = fila_text_str.split()[2].strip()
                    continue
                elif "obra nueva" in fila_text_str:
                    property_features.construction_year = 'Obra nueva'
                    continue

                if "calefacción" in fila_text_str:
                    property_features.heating = True
                    continue

                if "piscina" in fila_text_str:
                    property_features.pool = True
                    continue

                if "jardin" in fila_text_str or "jardín" in fila_text_str:
                    property_features.garden = True
                    continue

                if "aire acondicionado" in fila_text_str:
                    property_features.air_conditioning = True
                    continue

                if "armarios empotrados" in fila_text_str:
                    property_features.fitted_wardrobes = True
                    continue

                if "balcón" in fila_text_str or "balcon" in fila_text_str:
                    if fila_text_str == "balcón":
                        property_features.balcony = True
                    continue

                if any(keyword in fila_text_str.lower() for keyword in FLOOR_LEVEL_KEYWORDS):
                    if fila_text_str.startswith("planta"):
                        floor_level = fila_text_str.split()[1].replace('º', '').replace('ª', '')
                    elif "bajo" in fila_text_str:
                        floor_level = "Bajo"
                    elif " planta" not in fila_text_str:
                        floor_level = fila_text_str.split()[0].capitalize()
                    else:
                        # Número de plantas de casas o chalets
                        continue
                    # Normalizado con Fotocasa
                    floor_level = "Entresuelo" if floor_level == "Entreplanta" else floor_level

                    property_features.floor_level = floor_level if floor_level != "-" else 1
                    continue

                if "ascensor" in fila_text_str:
                    if fila_text_str.startswith("con"):
                        property_features.elevator = True
                    elif fila_text_str.startswith("sin"):
                        property_features.elevator = False
                    continue

        return property_features

    except Exception as exc:
        logger.error("Algún dato es incorrecto. EXCEPCION -> . {}\n{}".format(exc, soup.text))
        if "Please enable JS and disable any ad blocker" in soup.text:
            time.sleep(120)
        return None


def get_next_page_path(resp_property_content: bytes, num_init_page: int, logger=None):
    # Analizar el HTML con BeautifulSoup
    soup = BeautifulSoup(resp_property_content, "html.parser")
    try:
        pagination_element = soup.find("div", class_="pagination")
        next_page_button = pagination_element.find("a", class_="icon-arrow-right-after")
        next_page_url = next_page_button.get('href')
        if num_init_page:
            next_page_url = re.sub(r'pagina-\d+', f'pagina-{num_init_page}', next_page_url)
            logger.info(f"Se ha modicado la página a procesar a la número {num_init_page}")
    except Exception as exc:
        logger.error("No se ha podido obtener la siguiente página a procesar -> {}".format(exc))
        return None

    return next_page_url
