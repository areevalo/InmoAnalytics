import json
import re
import time
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from custom_types import Property, PropertyFeatures
from utils.scraper_logger import ScraperLogger

orientation_key_map = {
    0: "NS/NC",
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
    0: "NS/NC",
    1: "Sótano",
    2: "Subsótano",
    3: "Bajos",
    4: "Entresuelo",
    5: "Principal",
    6: "1ª Planta",
    7: "2ª Planta",
    8: "3ª Planta",
    9: "4ª Planta",
    10: "5ª Planta",
    11: "6ª Planta",
    12: "7ª Planta",
    13: "8ª Planta",
    14: "9ª Planta",
    15: "10ª Planta",
    16: "11ª Planta",
    17: "12ª Planta",
    18: "13ª Planta",
    19: "14ª Planta",
    20: "15ª Planta",
    21: "10ª o más",
    "N": "Superior a Planta 15",
    31: "Otros"
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

        property_data = Property(
            url=urljoin(base_url, url_path),
            price=int(price.replace('.', '').rstrip("€")) if price != 'A consultar' else None,
            municipality=municipality,
            neighborhood="",
            street="",
            origin="Fotocasa",
            checksum=""
        )

        properties.append(property_data)

    return properties

def get_property_data(resp_casa_content: bytes, property_basic_data: Property, logger: ScraperLogger):
    """
       Procesa el contenido HTML de un anuncio inmobiliario para extraer datos estructurados.
       Si algún dato no está disponible, se asignan valores por defecto.
       """
    def get_floor_number(features_list):
        for f in features_list:
            if f.get("label") == "floor":
                floor_value = f.get("value")
                return floor_value.split()[0][:-1] if floor_value else None
        return None # 1 que es un bajo, un 1º, otro un 4, y otro un 5, 4 una casa (normal)

    def get_type_of_home(title: str):
        # Buscar el texto antes de "en venta"
        match = re.search(r'^(.*?) en venta', title)
        if match:
            return match.group(1).strip()
        return None

    def get_orientation(orientation_key_num: int):
        return orientation_key_map.get(orientation_key_num, "NS/NC")

    def get_floor(floor_key_num):
        return floor_key_map.get(floor_key_num, "NS/NC")

    # Analizar el HTML con BeautifulSoup
    soup = BeautifulSoup(resp_casa_content, "html.parser")
    property_features = PropertyFeatures() # "suelos de calefacción radiante" "suelo radiante" "suelo radiante y refrigerante" "suelos radiantes" "refrigeración por hilo radiante"
    property_features.property = property_basic_data
    property_basic_data_updated = property_basic_data

    try:
        script_tag = soup.find("script", id="sui-scripts")
        match = re.search(r'window\.__INITIAL_PROPS__\s*=\s*JSON\.parse\("(.+?)"\)', script_tag.string,
                          re.DOTALL) if script_tag and script_tag.string else None
        if match:
            json_escaped = match.group(1)
            # Decodificar el JSON escapado
            json_string = json_escaped.replace('\\"', '"').replace('\\"', '"')  # Reemplazar las comillas escapadas
            property_data = json.loads(json_string)  # Convertir a un diccionario de Python
            logger.info(f"JSON con datos encontrado en el HTML. Procesando datos de la propiedad...")
            # Extraer los datos de interés
            # TODO: comparar JSON de obra nueva de segunda mano y procesar en métodos diferentes
            property_details = property_data['realEstateAdDetailEntityV2']
            property_old_details = property_data.get('realEstate')
            if not property_old_details:
                # TODO: método de obtención de datos de obra nueva
                return property_basic_data_updated, property_features
            # Obtención de datos básicos de localización para actualizar property_basic_data
            location_data = property_details['address']
            municipality = location_data.get('locality').strip()
            if municipality.endswith("apital"):
                property_basic_data_updated.municipality = municipality.split()[0]  # Madrid
            elif municipality.endswith("(Madrid)"):
                property_basic_data_updated.municipality = municipality.replace("(Madrid)", "")
            else:
                property_basic_data_updated.municipality = municipality
            property_basic_data_updated.neighborhood = location_data.get('neighborhood','')
            property_basic_data_updated.street = property_old_details.get('location', '')
            # ['street']['name'] + ', ' + property_data['realEstateAdDetailEntityV2']['address']['street']['number']
            # Obtención de características de la propiedad
            features_data = property_details['features']
            property_features.area = features_data.get('surface')
            property_features.rooms = features_data.get('rooms')
            property_features.baths = features_data.get('bathrooms')
            floor_key_num = features_data.get('floor')
            property_features.floor_level = get_floor(floor_key_num)
            property_features.construction_year = features_data.get('antiquity')
            orientation_key_num = features_data.get('orientation')
            property_features.orientation = get_orientation(orientation_key_num)
            property_title = property_data.get('propertyTitle', '').strip()
            property_features.type_of_home = get_type_of_home(property_title)
            # floor_level = get_floor_number(property_old_details.get("featuresList", []))
            # property_features.floor_level = floor_level
            property_features.energy_calification = property_details['energyCertificate'].get('energyEfficiencyRatingType', '').strip()
            description = property_details.get('description')
            if description and "suelo radiante" in description.lower():
                property_features.underfloor_heating = True
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
                elif "garaje" in feature_text:
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
                    pass # feature_text not in ("pista de tenis", "gimnasio", "zona infantil", "no amueblado", "zona comunitaria", "lavadero", "sistema video vigilancia cctv 24h", "alarma", "internet", "servicio portería", "nevera", "lavadora", "horno", "suite - con baño", "cocina equipada", "puerta blindada", "electrodomésticos", "parquet", "cocina office", "gres cerámica", "estado", "amueblado", "emisiones", "agua caliente", "habitaciones:", "baños:", "superficie:", "patio")

        else:
            logger.warning("No se encontró el JSON en el HTML. Continuando con la obtención de datos de forma manual..")
            # TODO: evitar procesar  nuda propiedad, subastas, oportunidad de inversión por alquiler u okupado
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
                elif label == "planta" and property_features.floor_level == "NS/NC":
                    if "bajo" in value:
                        property_features.floor_level = "Bajo"
                    elif "sótano" in value:
                        property_features.floor_level = "Sótano"
                    else:
                        property_features.floor_level = value.split()[0][:-1]
                else:
                    if label == 'planta':
                        if property_features.floor_level == "NS/NC":
                            pass
                    else:
                        pass

        return property_basic_data_updated, property_features

    except Exception as exc:
        # TODO: guardar traza de error y error en tabla BD?
        logger.error("Algún dato es incorrecto. EXCEPCION -> . {}\n{}".format(exc, soup.text))
        if "Please enable JS and disable any ad blocker" in soup.text:
            time.sleep(500)
        return property_basic_data_updated, property_features

def get_next_page_path(resp_property_content: bytes, num_init_page: int, logger=None):
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
        print("No se ha podido obtener la siguiente página a procesar -> {}".format(exc))
        return None

    return next_page_url

