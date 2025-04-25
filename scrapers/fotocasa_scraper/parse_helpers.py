import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from custom_types import Property


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
        street_start_position = title.find(' en ')
        # TODO: modificar y adaptar a Fotocasa
        if street_start_position > -1:
            # Ajustar para empezar después de 'en'
            street_start_position += len(' en ')

            # Buscar todas las comas en el título
            commas = [pos for pos, char in enumerate(title) if char == ',']

            # Inicializar campos
            street = None
            neighborhood = None
            municipality = None

            if commas:
                # La última coma indica el municipio
                municipality = title[commas[-1] + 1:].strip()

                # Si hay más de una coma, analizar el contenido entre las comas
                if len(commas) > 1:
                    possible_number = title[commas[0] + 1:commas[1]].strip()
                    # Verificar si el texto entre la primera y segunda coma es un número o un 's/n'
                    if possible_number.isdigit() or 's/n' in possible_number:
                        # Incluir el número en la calle
                        street = title[street_start_position:commas[1]].strip()
                        neighborhood = title[commas[1] + 1:commas[-1]].strip()
                    else:
                        # Si no es un número, asignar como barrio
                        street = title[street_start_position:commas[0]].strip()
                        neighborhood = title[commas[0] + 1:commas[-1]].strip()
                else:
                    # Si solo hay una coma, asumir que todo después de 'en' hasta la coma es el barrio
                    street = None
                    neighborhood = title[street_start_position:commas[0]].strip()
            else:
                # Si no hay comas, asumir que todo después de 'en' es el municipio
                municipality = title[street_start_position:].strip()

            # Capitalizar los resultados para consistencia
            street = street[0].upper() + street[1:] if street else None
            neighborhood = neighborhood[0].upper() + neighborhood[1:] if neighborhood else None
            municipality = municipality[0].upper() + municipality[1:] if municipality else None

        property_data = Property(
            url=urljoin(base_url, url_path),
            price=int(price.replace('.', '').rstrip("€")) if price != 'A consultar' else None,
            municipality=municipality,
            neighborhood=neighborhood,
            street=street,
            origin="Fotocasa",
            checksum=""
        )

        properties.append(property_data)

    return properties

def obtener_datos_casa(resp_casa_content: bytes, url: str):
    # Analizar el HTML con BeautifulSoup
    soup = BeautifulSoup(resp_casa_content, "html.parser")
    data = {}
    try:
        # TODO: evitar procesar  nuda propiedad, subastas, oportunidad de inversión por alquiler u okupado
        # Extraer los datos de cada anuncio
        main_data = soup.find("section", class_="detail-info")
        detalles_datos_elements = main_data.find_all("div", class_="details-property")
        if detalles_datos_elements:
            detalles_datos = detalles_datos_elements[-1]
        year = "NS/NC"
        t = "No"
        garage = "No"
        tr = "No"
        pool = "No"
        energy = "NS/NC"
        orientation = "NS/NC"
        c = "No"

        location_element = main_data.find("span", class_= "main-info__title-minor")
        location = location_element.text.split(",")[-1].replace(",", "").strip()
        if location == "Madrid":
            location = location_element.text.split(",")[0].replace(",", "").strip()
        price_element = main_data.find("strong", class_= "price")
        price = int(price_element.text.split()[0].replace(".",""))
        energy_element = soup.find('span', text=re.compile(r'\d+ kWh/m² año'))
        if energy_element:
            energy_class = energy_element.get('class')[0]
            energy = energy_class.split("-")[-1].upper()
        for fila_datos in detalles_datos.find_all("li"):
            fila_text = fila_datos.text
            if " m²" in fila_text:
                m2 = int(fila_text.split()[0])
                continue
            if "habitaciones" in fila_text or "habitación" in fila_text:
                rooms = int(fila_text.split()[0])
                continue
            if "baño" in fila_text:
                bathrooms = int(fila_text.split()[0])
                continue
            if "Terraza" in fila_text:
                t = "Sí"
                continue
            if "garaje" in fila_text:
                # TODO: plaza comunitaria o 2 plazas
                garage = "Privado"
                continue
            if "Trastero" in fila_text:
                tr = "Sí"
                continue
            if "Orientación" in fila_text:
                if "," not in fila_text:
                    orientation = fila_text.split()[1].capitalize()
                else:
                    orientation_list = fila_text.split()[-2:]
                    orientation = ''.join([x.capitalize() for x in orientation_list]).replace(",","/")
                continue
            if "Construido en" in fila_text:
                year = fila_text.split()[2]
                continue
            elif "nueva" in fila_text:
                year = "Obra nueva"
                # TODO: controlar datos de obra nueva
                continue
            if "Calefacción" in fila_text:
                c = "Sí"
                # TODO: controlar suelo radiante
                continue
            if "Piscina" in fila_text:
                pool = "Sí"
                continue


        data = {
            "Habitaciones": rooms,
            "Baños": bathrooms,
            "m2": m2,
            "Precio": price,
            "Ubicación": location,
            "Antigüedad": year,
            "Calefacción": c,
            "Terraza": t,
            "Garaje": garage,
            "Trastero": tr,
            "Piscina": pool,
            "Orientacion": orientation,
            "Cal. Energía": energy,
            "Url": url
        }
        return data
    except Exception as exc:
        print("Algún dato es incorrecto -> {}".format(soup.text))
        return data

def obtener_siguiente_pag(resp_busqueda_content: bytes):
    # Analizar el HTML con BeautifulSoup
    soup = BeautifulSoup(resp_busqueda_content, "html.parser")
    try:
        pagination_element = soup.find("div", class_="pagination")
        next_page_button = pagination_element.find("a", class_="icon-arrow-right-after")
        next_page_url = next_page_button.get('href')
    except Exception as exc:
        print("No se ha podido obtener la siguiente página a procesar -> {}".format(exc))
        return None

    return next_page_url

