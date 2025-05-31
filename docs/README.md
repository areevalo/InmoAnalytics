## TFG: InmoAnalytics

### Descripción general
Este proyecto consiste en una aplicación web robusta diseñada para centralizar y analizar información inmobiliaria. Los datos se obtienen mediante técnicas de scraping concurrente desde importantes portales inmobiliarios como Fotocasa e Idealista. El sistema está estructurado como una aplicación Django que gestiona la recolección de datos, su almacenamiento en una base de datos y su presentación a través de una interfaz web interactiva. El objetivo principal es ofrecer al usuario una herramienta eficaz para la búsqueda, filtrado avanzado y análisis de propiedades en la Comunidad de Madrid, permitiendo además la exportación de los resultados a formato Excel.

### Organización del código
El proyecto se estructura en varios módulos principales:
- **Scrapers (`scrapers/`):** Contiene la lógica para la extracción de datos de los portales (ej. `IdealistaScraper`, `FotocasaScraper`), incluyendo un `BaseScraper` con funcionalidades comunes y helpers para el parseo de la información (`parse_helpers.py`). Se utiliza un `MainLauncher` para ejecutar los scrapers de forma concurrente.
- **Aplicación Django (`inmoanalytics/`, `database/`, `exports/`):**
    - `inmoanalytics/`: Configuración principal del proyecto Django, vistas (`views.py`), filtros (`filters.py`) y URLs (`urls.py`).
    - `database/`: Define los modelos de la base de datos (`models.py` para `Properties` y `PropertyFeatures`) y funciones de utilidad para interactuar con la base de datos (`db_funcs.py`).
    - `exports/`: Módulo para la funcionalidad de exportación de datos, como `excel_exporter.py`.
- **Gestión y Comandos (`management/commands/`):** Incluye comandos personalizados de Django, como `property_verification.py` para tareas de mantenimiento o verificación de datos.
- **Archivos estáticos y plantillas (`static/`, `templates/`):** Contienen los archivos CSS (`styles.css`), JavaScript (`property_list.js`) y las plantillas HTML (`property_list.html`) para la interfaz de usuario.
- **Utilidades (`utils.py`):** Funciones auxiliares generales utilizadas en el proyecto.

**Convenciones:**
- **Código fuente**: Desarrollado en inglés, adhiriéndose a estándares y convenciones internacionales de programación.
- **Comentarios en el código**: Redactados en español, con el fin de facilitar la comprensión detallada por parte del tribunal evaluador.
- **Documentación del proyecto**: Elaborada en español, explicando exhaustivamente el propósito, la arquitectura y el funcionamiento general del sistema.

### Tecnologías y herramientas utilizadas
- **Python**: Lenguaje principal para el desarrollo del backend, los scripts de scraping (utilizando concurrencia para eficiencia) y toda la lógica de la aplicación.
- **Django**: Framework de desarrollo web de alto nivel para Python, empleado para:
    - Construir la aplicación siguiendo el patrón Modelo-Vista-Plantilla (MVT).
    - Gestionar la lógica de negocio y las interacciones con la base de datos mediante su ORM.
    - Definir modelos de datos (`Properties`, `PropertyFeatures`).
    - Implementar un sistema de filtros avanzado (`django-filter`).
    - Gestionar las URLs y servir las vistas y plantillas.
- **HTML, CSS, JavaScript**: Para la construcción de la interfaz de usuario.
    - **Bootstrap**: Framework CSS para el diseño de una interfaz web responsiva, sencilla y funcional.
    - **JavaScript (cliente)**: Para la interactividad de la página, como la actualización dinámica de los barrios según el municipio seleccionado (usando AJAX), la validación de filtros antes de la exportación y la gestión de la interfaz de usuario.
- **Pandas**: Utilizada para la manipulación de datos y la generación de archivos Excel en la funcionalidad de exportación.
- **Base de Datos Relacional**: Aunque no se especifica el motor (ej. SQLite, PostgreSQL), Django ORM se encarga de la interacción para persistir y consultar los datos de las propiedades.
- **Git**: Para el control de versiones del proyecto.

### Funcionalidades clave
- **Scraping de Múltiples Fuentes**: Extracción automática y concurrente de datos de propiedades desde Idealista y Fotocasa.
- **Almacenamiento Centralizado**: Persistencia de la información recopilada en una base de datos estructurada.
- **Interfaz Web Interactiva**:
    - Visualización de propiedades con paginación.
    - Sistema de filtrado avanzado por múltiples criterios (ubicación, precio, tamaño, habitaciones, baños, tipo de vivienda, características adicionales como piscina, garaje, etc.).
    - Actualización dinámica de opciones de filtro (ej. barrios dependientes del municipio).
- **Exportación de Datos**: Posibilidad de exportar los listados de propiedades filtradas a un archivo Excel (`.xlsx`).
- **Logging**: Implementación de un sistema de logging (`ScraperLogger`) para el seguimiento y depuración de los procesos de scraping.
- **Gestión de Datos**: Comandos para la posible verificación y mantenimiento de la integridad de los datos de las propiedades.