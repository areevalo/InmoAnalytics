import re

from bs4 import BeautifulSoup


def obtener_casas(resp_casas_content: bytes):
    # Analizar el HTML con BeautifulSoup
    soup = BeautifulSoup(resp_casas_content, "html.parser")

    # Extraer los datos de cada anuncio
    data = []

    for listing in soup.find_all("article", class_="item"):
        title = listing.find("a", class_="item-link").text.strip()
        description = listing.find("div", class_="item-description").text.strip()
        price = listing.find("span", class_="item-price").text.strip()
        url = listing.find("a", class_="item-link").get('href')
        data.append({"Título": title, "Descripción": description, "Precio": price, "Url": url})

    return data

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

