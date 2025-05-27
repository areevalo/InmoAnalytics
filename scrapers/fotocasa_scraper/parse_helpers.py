import json
import re
import time
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from custom_types import Property, PropertyFeatures
from scrapers.constants import UNDERFLOOR_HEATING_KEYWORDS, OCCUPIED_PROPERTY_KEYWORDS, \
    BARE_OWNERSHIP_PROPERTY_KEYWORDS, RENTED_PROPERTY_KEYWORDS, AUCTION_PROPERTY_KEYWORDS
from utils.scraper_logger import ScraperLogger

orientation_key_map = {
    0: None,
    1: "Norte",
    2: "Noroeste",
    3: "Noreste",
    4: "Sur",
    5: "Sureste",
    6: "Suroeste",
    7: "Este",
    8: "Oeste"
}

floor_key_map = {
    0: None,
    1: "Sótano",
    2: "Subsótano",
    3: "Bajo",
    4: "Entresuelo",
    5: "Principal",
    6: "1",
    7: "2",
    8: "3",
    9: "4",
    10: "5",
    11: "6",
    12: "7",
    13: "8",
    14: "9",
    15: "10",
    16: "11",
    17: "12",
    18: "13",
    19: "14",
    20: "15",
    21: ">15", # "10ª o más"
    "N": ">15",
    31: ">15" # "Otros"
}


current_year = time.localtime().tm_year

antiquity_key_map = {
    1: f">{current_year - 1}",  # "Menos de 1 año"
    2: f"{current_year - 5}-{current_year - 1}",  # "1 a 5 años"
    3: f"{current_year - 10}-{current_year - 5}",  # "5 a 10 años"
    4: f"{current_year - 20}-{current_year - 10}",  # "10 a 20 años"
    5: f"{current_year - 30}-{current_year - 20}",  # "20 a 30 años"
    6: f"{current_year - 50}-{current_year - 30}",  # "30 a 50 años"
    7: f"{current_year - 70}-{current_year - 50}",  # "50 a 70 años"
    8: f"{current_year - 100}-{current_year - 70}",  # "70 a 100 años"
    9: f"<{current_year - 100}"  # "+ 100 años"
}


def get_properties(html_content: bytes, base_url: str):
    # Analizar el HTML con BeautifulSoup
    soup = BeautifulSoup(html_content, "html.parser")

    # Extraer los datos de cada anuncio
    properties = []
    for listing in soup.find_all("article", class_=["re-CardPackPremium", "re-CardPackMinimal"]):
        title = listing.find("span", class_="re-CardTitle").text.strip()
        description = listing.find("p", class_="re-CardDescription").text.strip()
        price = listing.find("span", class_="re-CardPrice").text.strip()
        # location = listing.find("p", class_="re-CardPackLocation").text.strip()
        url_path = listing.find("a", class_=["re-CardPackPremium-carousel", "re-CardPackMinimal-slider"]).get('href')
        # street_start_position = title.find(' en ')
        # if street_start_position > -1:
        #     # Ajustar para empezar después de 'en'
        #     street_start_position += len(' en ')
        #
        #     # Buscar todas las comas en el título
        #     commas = [pos for pos, char in enumerate(title) if char == ',']
        #
        #     # Inicializar campos
        #     street = None
        #     neighborhood = None
        #     municipality = None
        #
        #     if commas:
        #         # La última coma indica el barrio
        #         neighborhood = title[commas[-1] + 1:].strip()
        #
        #         # Si hay más de una coma, analizar el contenido entre las comas
        #         if len(commas) > 1:
        #             street = title[street_start_position:commas[-1]].strip()
        #         else:
        #             # Si solo hay una coma, asumir que todo después de 'en' hasta la coma es la calle
        #             street = title[street_start_position:commas[0]].strip()
        #     else:
        #         # Si no hay comas, asumir que todo después de 'en' es la calle
        #         street = title[street_start_position:].strip()
        #
        #     # Capitalizar los resultados para consistencia
        #     street = street[0].upper() + street[1:] if street else None
        #     neighborhood = neighborhood[0].upper() + neighborhood[1:] if neighborhood else None
        municipality = "Madrid"  # Asumir municipio por defecto si no está presente

        property_basic_data = Property(
            url=urljoin(base_url, url_path),
            price=int(price.replace('.', '').rstrip("€")) if price != 'A consultar' else None,
            municipality=municipality,
            neighborhood="",
            street="",
            origin="Fotocasa",
            checksum=""
        )

        properties.append(property_basic_data)

    return properties

def get_type_of_home(property_data: dict, is_new_home: bool):
    title_key = "seoTitle" if is_new_home else "propertyTitle"
    title = property_data.get(title_key, '').strip()
    # Buscar el texto antes de "en venta"
    match = re.search(r'^(.*?) en venta', title)
    if match:
        property_type = match.group(1).strip()
        if property_type.lower() == "casa adosada":
            return "Chalet adosado"
        else:
            return property_type
    return None

def get_orientation(orientation_key_num: int):
    return orientation_key_map.get(orientation_key_num)

def get_floor(floor_key_num):
    return floor_key_map.get(floor_key_num)

def get_antiquity(antiquity_key_num):
    return antiquity_key_map.get(int(antiquity_key_num))

def get_street(location_data: dict):
    street_data = location_data.get('street')
    street_name = street_data.get('name')
    if street_name and street_name[-1].isupper():
        prepositions = ["de", "del", "la", "el", "los", "las", "y", "en", "a", "por", "con", "sin", "o", "u", "al"]
        street_name_words = street_name.lower().split()
        street_name = " ".join(
            [w if i in [0,1] and w in prepositions else (w.capitalize() if w not in prepositions else w)
             for i, w in enumerate(street_name_words)]
        )
    street_number = street_data.get('number')
    if street_number:
        return street_name.strip() + ', ' + str(street_number)
    return street_name.strip() if street_name and not "n/a" in street_name.lower() else None


def get_property_data(resp_casa_content: bytes, property_basic_data: Property, logger: ScraperLogger):
    """
       Procesa el contenido HTML de un anuncio inmobiliario para extraer datos estructurados.
       Si algún dato no está disponible, se asignan valores por defecto.
       """
    # Analizar el HTML con BeautifulSoup
    soup = BeautifulSoup(resp_casa_content, "html.parser")
    property_features = PropertyFeatures()
    property_basic_data_updated = property_basic_data
    # TODO: evitar procesar  nuda propiedad, subastas, oportunidad de inversión por alquiler u okupado
    try:

        script_tag = soup.find("script", id="sui-scripts")
        match = re.search(r'window\.__INITIAL_PROPS__\s*=\s*JSON\.parse\("(.+?)"\)', script_tag.string,
                          re.DOTALL) if script_tag and script_tag.string else None
        if match:
            json_escaped = match.group(1)
            # Decodificar el JSON escapado
            json_string = json_escaped.replace('\\"', '"').replace('\\"', '"')  # Reemplazar las comillas escapadas
            property_data = json.loads(json_string)  # Convertir a un diccionario de Python
            # logger.info(f"JSON con datos encontrado en el HTML. Procesando datos de la propiedad...")
            # Extraer los datos de interés
            property_details = property_data['realEstateAdDetailEntityV2']
            property_old_details = property_data.get('realEstate')
            is_new_home = True if not property_old_details else False

            # Obtención de datos básicos de localización para actualizar property_basic_data
            location_data = property_details['address']
            municipality = location_data.get('locality')
            property_basic_data_updated.municipality = municipality.strip() if municipality else None

            if property_basic_data_updated.municipality == "El Boalo - Cerceda – Mataelpino":
                property_basic_data_updated.municipality = location_data.get('municipality')
            else:
               property_basic_data_updated.neighborhood = location_data.get('neighborhood') or location_data.get('municipality')
            property_basic_data_updated.street = get_street(location_data)  # property_features.street = property_old_details.get('location', '').strip()
            # Obtención de características de la propiedad
            features_data = property_details['features']
            property_features.area = features_data.get('surface')
            property_features.rooms = features_data.get('rooms')
            property_features.baths = features_data.get('bathrooms')
            floor_key_num = features_data.get('floor')
            property_features.floor_level = get_floor(floor_key_num)
            antiquity_key_num = features_data.get('antiquity')
            property_features.construction_year = get_antiquity(antiquity_key_num) if antiquity_key_num else None
            orientation_key_num = features_data.get('orientation')
            property_features.orientation = get_orientation(orientation_key_num)
            type_of_home = get_type_of_home(property_data, is_new_home)
            if not type_of_home:
                logger.error(f"No se ha podido obtener el tipo de vivienda de la propiedad {property_basic_data.url}. ")
                return None, None
            property_features.type_of_home = type_of_home
            energy_calification = property_details['energyCertificate'].get('energyEfficiencyRatingType', '').strip()
            property_features.energy_calification = energy_calification if energy_calification else None
            property_description = property_details.get('description')
            if property_description:
                if any(keyword in property_description.lower() for keyword in UNDERFLOOR_HEATING_KEYWORDS):
                    property_features.underfloor_heating = True
                # Análisis de estado de la propiedad
                if any(keyword in property_description.lower() for keyword in OCCUPIED_PROPERTY_KEYWORDS):
                    property_features.ownership_status = "Ocupada ilegalmente"
                if any(keyword in property_description.lower() for keyword in BARE_OWNERSHIP_PROPERTY_KEYWORDS):
                    property_features.ownership_status = "Nuda propiedad"
                if any(keyword in property_description.lower() for keyword in RENTED_PROPERTY_KEYWORDS):
                    property_features.ownership_status = "Alquilada"
                if any(keyword in property_description.lower() for keyword in AUCTION_PROPERTY_KEYWORDS):
                    property_features.ownership_status = "Subastada"
            for feature in property_details.get('extraFeatures', []):
                feature_text = feature.lower().strip()
                if feature_text == "ascensor":
                    property_features.elevator = True
                elif feature_text == "aire acondicionado":
                    property_features.air_conditioning = True
                elif feature_text == "armarios":
                    property_features.fitted_wardrobes = True
                elif feature_text == "terraza":
                    property_features.terrace = True
                elif "garaje" in feature_text or "parking" in feature_text:
                    property_features.garage = True
                elif "piscina" in feature_text:
                    property_features.pool = True
                elif "jardín" in feature_text:
                    property_features.garden = True
                elif feature_text == "calefacción" and not property_features.heating:
                    property_features.heating = True
                elif feature_text == "trastero":
                    property_features.storage_room = True
                elif feature_text == "balcón":
                    property_features.balcony = True
                else:
                    # logger.info(f"No se ha procesado la característica {feature_text} de la propiedad {property_basic_data.url}")
                    pass
        else:
            # TODO: quitar si no es necesario
            logger.warning("No se encontró el JSON en el HTML. Continuando con la obtención de datos de forma manual..")
            # Extraer del título el tipo de vivienda
            title = soup.find("h1", class_="re-DetailHeader-propertyTitle").text.strip()
            street_start_position = title.rfind(' en ')
            if street_start_position > -1:
                # Ajustar para empezar después de 'en'
                street_start_position += len(' en ')

                # Buscar todas las comas en el título
                commas = [pos for pos, char in enumerate(title) if char == ',']

                # Inicializar campos
                street = None
                location = None

                if commas:
                    # Si hay más de una coma, analizar el contenido entre las comas
                    if len(commas) > 1:
                        possible_number = title[commas[0] + 1:commas[1]].strip()
                        # Verificar si el texto entre la primera y segunda coma es un número o un 's/n'
                        if possible_number.isdigit() or 's/n' in possible_number:
                            # Incluir el número en la calle
                            street = title[street_start_position:commas[1]].strip()
                            location = title[commas[1] + 1:].strip()
                        else:
                            # Si no es un número, asignar como barrio/municipio
                            street = title[street_start_position:commas[0]].strip()
                            location = title[commas[0] + 1:commas[-1]].strip()
                    else:
                        # Si solo hay una coma, asumir que todo después de 'en' hasta la coma es la calle
                        # TODO: meter "calle"
                        street = title[street_start_position:commas[0]].strip()
                        location = title[commas[0] + 1:].strip()
                else:
                    # Si no hay comas, asumir que todo después de 'en' es el barrio/municipio
                    location = title[street_start_position:].strip()

                # Capitalizar los resultados para consistencia
                municipality = soup.find("p", class_="re-DetailHeader-municipalityTitle").text.strip()
                if municipality.endswith("apital"):
                    property_basic_data_updated.municipality = municipality.split()[0]  # Madrid
                elif municipality.endswith("(Madrid)"):
                    property_basic_data_updated.municipality = municipality.replace("(Madrid)", "").strip()
                if municipality == location:
                    property_basic_data_updated.neighborhood = None
                else:
                    property_basic_data_updated.neighborhood = location[0].upper() + location[1:] if location else None
                property_basic_data_updated.street = street[0].upper() + street[1:] if street else None

            basic_features = soup.find("ul", class_="re-DetailHeader-features") or []
            for basic_feature in basic_features:
                feature_text = basic_feature.text.strip().lower()
                if "m²" in feature_text:
                    if "parcela" in feature_text or "terreno" in feature_text:
                        # Si la propiedad es una parcela, no asignar el área
                        pass
                    property_features.area = int(feature_text.split()[0])
                elif "hab" in feature_text:
                    property_features.rooms = int(feature_text.split()[0]) if feature_text.split()[0] != 'sin' else 0
                elif "baño" in feature_text:
                    baths_str = feature_text.split()[0]
                    property_features.baths = int(baths_str) if baths_str != 'sin' else 0
                elif any(word in feature_text for word in ("planta", "bajo", "sótano")):
                    if "planta" in feature_text:
                        property_features.floor_level = feature_text.split()[0][:-1]
                    elif "bajo" in feature_text:
                        property_features.floor_level = "Bajo"
                    elif "sótano" in feature_text:
                        property_features.floor_level = "Sótano"  # comparar con Idealista ya que es un valor para checksum
                    else:
                        print("que")
                else:
                    pass
            if "obra-nueva" in property_basic_data_updated.url:
                property_features.construction_year = "Obra nueva"
                specific_features = soup.find_all("div", class_="re-SharedFeature-legend")
            else:
                specific_features = soup.find_all("div", class_="re-DetailFeaturesList-featureContent")

            for feature in specific_features:  # TODO: separar características de obra nueva y de segunda mano
                label = (feature.find("p", class_="re-DetailFeaturesList-featureLabel") or feature.find("span", class_="re-SharedFeature-legendTitle")).text.lower().strip()
                value = (feature.find("div", class_="re-DetailFeaturesList-featureValue") or feature.find("span", class_="re-SharedFeature-legendDescription")).text.lower().strip()
                if label == "superficie":
                    property_features.area = int(value.split()[0])
                elif label == "habitaciones":
                    property_features.rooms = int(value)
                elif label == "baños":
                    property_features.baths = int(value)
                elif label == "tipo de inmueble":
                    property_features.type_of_home = value.capitalize()
                elif "armario" in label:
                    if value == "sí":
                        property_features.fitted_wardrobes = True
                    else:
                        pass
                elif label == "ascensor":
                    if value == "sí":
                        property_features.elevator = True
                    else:
                        property_features.elevator = False
                elif label == "antigüedad":
                    current_year = time.localtime().tm_year
                    if value.startswith("+") or value.startswith("más"):
                        years_of_antiquity = value.split()[1]
                        property_features.construction_year = '<' + str(current_year - int(years_of_antiquity))
                    elif value.startswith("-") or value.startswith("menos"):
                        years_of_antiquity = value.split()[2]
                        property_features.construction_year = current_year - int(years_of_antiquity) # property_features.construction_year = '>' + str(current_year - int(years_of_antiquity))
                    else:
                        antiquity = value.split()
                        antiquity_num1 = antiquity[2]
                        antiquity_num2 = antiquity[0]
                        construction_year = str(current_year - int(antiquity_num1)) + "-" + str(current_year - int(antiquity_num2))
                        property_features.construction_year = construction_year
                elif "energía" in label:
                    if property_features.construction_year == "Obra nueva":
                        energy_label = soup.find('span', {'property_data-testid': 'shared-feature-energy-label'})
                        property_features.energy_calification = energy_label.text.strip()
                    else:
                        property_features.energy_calification = value[0].upper()
                elif label == "terraza":
                    if value == "sí":
                        property_features.terrace = True
                    else:
                        pass
                elif label == "jardín":
                    if value == "privado":
                        property_features.garden = True
                    else:
                        pass
                elif label == "trastero":
                    if value == "sí":
                        property_features.storage_room = True
                    else:
                        pass
                elif label == "aire acondicionado":
                    if value == "sí":
                        property_features.air_conditioning = True
                    else:
                        pass
                elif label == "piscina":
                    if value == "privada":
                        property_features.pool = True
                    else:
                        pass
                elif label == "orientación":
                    property_features.orientation = value.capitalize()
                elif label == "parking":
                    if value == "privado":
                        property_features.garage = True
                    else:
                        pass  # Incluir comunitario, por ahora 3 que si incluye, otro no claro y otro opcional
                elif label == "calefacción":
                    if value == "no":
                        pass
                    else:
                        property_features.heating = True
                elif label == "planta" and property_features.floor_level is None:
                    if "bajo" in value:
                        property_features.floor_level = "Bajo"
                    elif "sótano" in value:
                        property_features.floor_level = "Sótano"
                    else:
                        property_features.floor_level = value.split()[0][:-1]
                else:
                    if label == 'planta':
                        if property_features.floor_level is None:
                            pass
                    else:
                        pass

        return property_basic_data_updated, property_features

    except Exception as exc:
        # TODO: guardar traza de error y error en tabla BD?
        logger.error("Algún dato es incorrecto. EXCEPCION -> . {}\n{}".format(exc, soup.text))
        if "Please enable JS and disable any ad blocker" in soup.text:
            time.sleep(120)
        return property_basic_data_updated, property_features

def get_next_page_path(resp_property_content: bytes, num_init_page: int, current_page: int, logger=None):
    # Analizar el HTML con BeautifulSoup
    soup = BeautifulSoup(resp_property_content, "html.parser")
    try:
        pagination_element = soup.find('div', class_='re-Pagination')
        next_page_button = pagination_element.find_all('a')[-1]
        next_page_url = next_page_button.get('href')
        if num_init_page:
            next_page_url = re.sub(r'/l/\d+', f'/l/{num_init_page}', next_page_url)
            logger.info(f"Se ha modicado la página a procesar a la número {num_init_page}")
    except Exception as exc:
        logger.error(f"No se ha podido obtener la siguiente página a procesar -> {exc}.\n"
                     f"Construyendo la URL de la siguiente página...")
        next_page_path_url = f"/es/comprar/viviendas/madrid-provincia/todas-las-zonas/l/{current_page + 1}?sortType=publicationDate"
        return next_page_path_url

    return next_page_url

