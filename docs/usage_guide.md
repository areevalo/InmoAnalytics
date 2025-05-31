# Guía de Uso del Proyecto InmoAnalytics

Este documento proporciona instrucciones sobre cómo ejecutar y utilizar las diferentes partes del proyecto InmoAnalytics.

## 1. Entorno de Desarrollo

Asegúrate de tener Python y Django instalados en tu sistema, así como las dependencias del proyecto listadas en `requirements.txt`. Se recomienda utilizar un entorno virtual.
```bash
# Creación y activación de entorno virtual
python -m venv venv
# En Windows
venv\Scripts\activate
# En macOS/Linux
source venv/bin/activate
# Instalar dependencias
pip install -r requirements.txt
```

## 2. Inicialización del Servidor Web (Aplicación Django)

Para interactuar con la interfaz web de InmoAnalytics, donde podrás visualizar, filtrar y exportar propiedades, necesitas iniciar el servidor de desarrollo de Django.

Desde la raíz del proyecto, ejecuta:
```bash 
python manage.py runserver
```
Una vez iniciado, podrás acceder a la aplicación abriendo tu navegador web y dirigiéndote a la dirección que se muestra en la consola (generalmente `http://127.0.0.1:8000/`).

La interfaz web te permitirá:
- Ver un listado paginado de propiedades.
- Aplicar filtros por ubicación (municipio, barrio), precio, número de habitaciones, baños, superficie, tipo de vivienda, y características adicionales (ascensor, garaje, piscina, etc.).
- Exportar los resultados filtrados a un archivo Excel.

## 3. Ejecución de los Scripts de Scraping

Para poblar la base de datos con información de propiedades, debes ejecutar los scripts de scraping. Estos scripts se encargarán de recolectar datos de los portales Idealista y Fotocasa de forma concurrente.

Desde la raíz del proyecto, ejecuta:
```bash 
python main_launcher.py
```
Este comando iniciará el `MainLauncher`, que a su vez ejecutará los scrapers configurados. El progreso y posibles errores se registrarán mediante el `ScraperLogger`. Es importante tener en cuenta que este proceso puede tardar dependiendo de la cantidad de datos a extraer y las limitaciones de los portales.

## 4. Proceso de Verificación de Propiedades

El proyecto incluye un comando de gestión de Django para realizar tareas de mantenimiento sobre los datos de las propiedades, como por ejemplo, revisar si una propiedad ha sido dada de baja o si sus características han cambiado en el portal original.

Para ejecutar este proceso, utiliza el siguiente comando de Django:
```bash 
python manage.py property_verification
```
Este comando buscará y ejecutará la lógica definida en `management/commands/property_verification.py`.

## Flujo de Trabajo General

1.  **Configura el entorno** e instala las dependencias.
2.  **Ejecuta los scrapers** (`python main_launcher.py`) para recopilar datos. Este paso puede requerir ejecuciones periódicas para mantener la base de datos actualizada.
3.  **Inicia el servidor web** (`python manage.py runserver`) para acceder a la aplicación.
4.  **Utiliza la interfaz web** para buscar, filtrar y analizar las propiedades.
5.  **Exporta los datos** a Excel si es necesario.
6.  Opcionalmente, **ejecuta el proceso de verificación** (`python manage.py property_verification`) para el mantenimiento de los datos.

Este flujo te permitirá utilizar todas las funcionalidades clave de InmoAnalytics, desde la recolección de datos hasta su análisis y exportación.