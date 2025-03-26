import datetime
import time
import random

import pandas as pd
import requests

import parse_helpers

# Definir la URL de búsqueda en Fotocasa
base_url = "https://www.idealista.com"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0"
s = requests.Session()
req_headers = {
    "User-Agent": USER_AGENT,
    "Host": "www.idealista.com",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/png,image/svg+xml,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3",
    "Connection": "keep-alive",
    "Priority": "u=0, i",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "TE": "trailers",
    "Upgrade-Insecure-Requests": "1"
}
# TODO: poner la URL por pantalla
busqueda_idealista_url = input("Introduzca la URL de la búsqueda de idealista que quiere procesar:\n")
if busqueda_idealista_url == "":
    busqueda_idealista_url = "https://www.idealista.com/areas/venta-viviendas/con-precio-hasta_260000,metros-cuadrados-mas-de_60,de-tres-dormitorios,de-cuatro-cinco-habitaciones-o-mas,dos-banos,tres-banos-o-mas,ascensor,obra-nueva,buen-estado/?shape=%28%28oe_uFvymWo%60Aq%7CH%7BvEawMykH%60iGu_T%7Ci%40yfAu_NryJsjDkxHwiVksKucA%3F%7BzVpvPw_C%7B%7CE%7Dyh%40npFmkHbnLzkm%40vnCscA%7C%60KmnXl%7BKvfFivM%7Ekb%40%7EfJpcLdaSapJjf%40jyNesHxwQmqFngJmcE%60iGhf%40%7EhRc%7CCpnB%29%29"

print("Proceso iniciado a {}".format(datetime.datetime.now()))
# Hacer la solicitud HTTP y obtener el HTML
resp_busqueda_idealista = s.get(
    url=busqueda_idealista_url,
    headers=req_headers
)
html_content = resp_busqueda_idealista.content
resp_next_page = None
datos_casas_parsed = []

for page in range (1,100):
    if resp_next_page:
        html_content = resp_next_page.content
    casas_parsed = parse_helpers.obtener_casas(html_content)

    for ix, casa_parsed in enumerate(casas_parsed):
        casa_url = base_url + casa_parsed['Url']
        time.sleep(random.randint(2, 5))
        resp_casa = s.get(
            url=casa_url,
            headers=req_headers
        )
        print("Obteniendo datos de la vivienda {} de la página {}...".format(ix + 1, page))

        casa_data_parsed = parse_helpers.obtener_datos_casa(resp_casa.content, casa_url)
        datos_casas_parsed.append(casa_data_parsed)

    if "Siguiente" in str(html_content):
        time.sleep(random.randint(2, 5))
        next_page_url = parse_helpers.obtener_siguiente_pag(html_content)
        resp_next_page = s.get(
            url = base_url + next_page_url,
            headers= req_headers
        )
        print("Pasando a la página {}...".format(page + 1))
        continue
    else:
        print("No hay más páginas para procesar")
        break

print("Proceso finalizado a {}".format(datetime.datetime.now()))

# Crear el DataFrame de Pandas y exportarlo a un archivo Excel
print("Creando Excel con los datos de viviendas procesadas")
# Convertir los diccionarios en filas de datos
data = [list(d.values()) for d in datos_casas_parsed]

# Crear un DataFrame a partir de las filas de datos
df = pd.DataFrame(data, columns=list(datos_casas_parsed[0].keys()))

# Escribir el DataFrame en un archivo Excel
writer = pd.ExcelWriter('idealista_viviendas_pinto2.xlsx', engine='xlsxwriter')
df.to_excel(writer, index=False)
writer._save()