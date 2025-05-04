import re
import time
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from custom_types import Property, PropertyFeatures


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

def get_property_data(resp_casa_content: bytes, property_basic_data: Property):
    """
       Procesa el contenido HTML de un anuncio inmobiliario para extraer datos estructurados.
       Si algún dato no está disponible, se asignan valores por defecto.
       """

    # Analizar el HTML con BeautifulSoup
    soup = BeautifulSoup(resp_casa_content, "html.parser")
    property_features = PropertyFeatures()
    property_features.property = property_basic_data
    property_basic_data_updated = property_basic_data

    try:
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
            property_basic_data_updated.municipality = municipality if not municipality.endswith("apital") else municipality.split()[0]
            if municipality == location:
                property_basic_data_updated.neighborhood = None
            else:
                property_basic_data_updated.neighborhood = location[0].upper() + location[1:] if location else None
            property_basic_data_updated.street = street[0].upper() + street[1:] if street else None

        basic_features = soup.find("ul", class_="re-DetailHeader-features") or []
        for feature in basic_features:
            feature_text = feature.text.strip().lower()
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

        for feature in specific_features:
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
                    energy_label = soup.find('span', {'data-testid': 'shared-feature-energy-label'})
                    property_features.energy_calification = energy_label.text.strip()
                else:
                    property_features.energy_calification = value[0].upper()
            elif label == "orientación":
                property_features.orientation = value.capitalize()
            elif label == "parking":
                if value == "privado":
                    property_features.garage = True
                else:
                    pass  # Incluir comunitario, por ahora 2 que si incluye, otro no claro y otro opcional
            elif label == "calefacción":
                property_features.heating = True
            else:
                if label == 'planta':
                    if property_features.floor_level == "NS/NC":
                        pass
                else:
                    pass
        #
        #
        # # Extraer la sección principal de los datos
        # main_data = soup.find("section", class_="detail-info")
        # if not main_data:
        #     raise ValueError("No se encontró la sección principal de datos.")
        #
        # # Extraer ubicación
        # location_element = main_data.find("span", class_="main-info__title-minor")
        # if location_element:
        #     location = location_element.text.split(",")[-1].replace(",", "").strip()
        #     if location == "Madrid":
        #         location = location_element.text.split(",")[0].replace(",", "").strip()
        # else:
        #     location = "NS/NC"
        #
        # if location != property_basic_data.municipality:
        #     print("DIFERENCIA DE LOCALIZACION")
        #
        # # Extraer precio # TODO: revisar ownership status y underfloor heating
        # # price_element = main_data.find("strong", class_="price")
        # # price = int(price_element.text.split()[0].replace(".", "")) if price_element else 0
        #
        # # Extraer calificación energética (si está disponible)
        # energy_element = soup.find('span', text=re.compile(r'\d+ kWh/m² año'))
        # if energy_element:
        #     energy_class = energy_element.get('class')[0]
        #     property_features.energy_calification = energy_class.split("-")[-1].upper().strip()
        # # TODO: ¿crear checksum con la descripción?
        # property_description = main_data.find("div", class_="comment")
        # if property_description:
        #     if "suelo radiante" in property_description.text.lower():
        #         property_features.underfloor_heating = True
        #
        # # Extraer detalles adicionales
        # detalles_datos_elements = main_data.find_all("div", class_="details-property")
        # if detalles_datos_elements:
        #     detalles_datos = detalles_datos_elements[-1]
        #     for fila_datos in detalles_datos.find_all("li"):
        #         fila_text_str = fila_datos.text.lower()
        #
        #         # Superficie en m²
        #         if " m²" in fila_text_str and "parcela" not in fila_text_str:
        #             property_features.area = int(fila_text_str.replace('.', '').split()[0])
        #             continue
        #
        #         # Número de habitaciones
        #         if "habitaciones" in fila_text_str or "habitación" in fila_text_str:
        #             property_features.rooms = int(fila_text_str.split()[0]) if fila_text_str.split()[0] != 'sin' else 0
        #             continue
        #
        #         # Número de baños
        #         if "baño" in fila_text_str:
        #             baths_str = fila_text_str.split()[0]
        #             property_features.baths = int(baths_str) if baths_str != 'sin' else 0
        #             continue
        #
        #         # Terraza
        #         if "terraza" in fila_text_str:
        #             property_features.terrace = True
        #             continue
        #
        #         # Garaje
        #         if "garaje" in fila_text_str:
        #             #  TODO: plaza comunitaria o 2 plazas # caso 'plaza de garaje por 55.000 € adicionales'
        #             property_features.garage = True
        #             continue
        #
        #         # Trastero
        #         if "trastero" in fila_text_str:
        #             property_features.storage_room = True
        #             continue
        #
        #         # Orientación
        #         if "orientación" in fila_text_str:
        #             orientation_parts = fila_text_str.split()
        #             orientation_list = orientation_parts[1:] if len(orientation_parts) > 1 else ["NS/NC"]
        #             property_features.orientation = "".join([x.capitalize() for x in orientation_list]).replace(",",
        #                                                                                                         "/").strip()
        #             continue
        #
        #         # Año de construcción o estado (obra nueva)
        #         if "construido en" in fila_text_str:
        #             property_features.construction_year = fila_text_str.split()[2].strip()
        #             continue
        #         elif "obra nueva" in fila_text_str:
        #             # TODO: controlar datos de obra nueva
        #             property_features.construction_year = 'Obra nueva'
        #             continue
        #
        #         # Calefacción
        #         if "calefacción" in fila_text_str:
        #             property_features.heating = True
        #             continue
        #
        #         # Piscina
        #         if "piscina" in fila_text_str:
        #             property_features.pool = True
        #             continue
        #
        #         # TODO: parsear datos
        #         if "jardin" in fila_text_str or "jardín" in fila_text_str:
        #             property_features.garden = True
        #             continue
        #
        #         if "aire acondicionado" in fila_text_str:
        #             property_features.air_conditioning = True
        #             if "sin" in fila_text_str:
        #                 print("que")
        #             continue
        #
        #         if "armarios empotrados" in fila_text_str:
        #             property_features.fitted_wardrobes = True
        #             if "sin" in fila_text_str:
        #                 print("que")
        #             continue
        #
        #         if "balcón" in fila_text_str or "balcon" in fila_text_str:
        #             if fila_text_str == "balcón":
        #                 property_features.balcony = True
        #             else:
        #                 print('que')
        #             continue
        #
        #         if "planta" in fila_text_str or "bajo" in fila_text_str:
        #             if fila_text_str.startswith("planta"):
        #                 property_features.floor_level = fila_text_str.split()[1][0].strip()
        #             elif 'bajo' in fila_text_str:
        #                 property_features.floor_level = "Bajo"
        #             else:
        #                 print("que")  # TODO: Verificar que es un numero de plantas porque no es un piso
        #             continue
        #
        #         if "ascensor" in fila_text_str:
        #             if fila_text_str.startswith("con"):
        #                 property_features.elevator = True
        #             elif fila_text_str.startswith("sin"):
        #                 property_features.elevator = False
        #             else:
        #                 print('que')
        #             continue
        #
        #         if "suelo radiante" in fila_text_str or 'suelo' in fila_text_str:
        #             print('underfloor_heating')
        #             continue
        #
        #         print(f"Ningun valor a procesar -> {fila_text_str}")

        return property_basic_data_updated, property_features

    except Exception as exc:
        # TODO: guardar traza de error y error en tabla BD?
        print("Algún dato es incorrecto. EXCEPCION -> . {}\n{}".format(exc, soup.text))
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

