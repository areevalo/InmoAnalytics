import pandas as pd
from django.http import HttpResponse, HttpRequest

from database.models import Properties
from inmoanalytics.filters import PropertiesFilter


def export_properties_excel(request: HttpRequest) -> HttpResponse:
    """Exporta las propiedades filtradas a un archivo Excel"""
    f = PropertiesFilter(request.GET, queryset=Properties.objects.all())
    properties = f.qs.prefetch_related('propertyfeatures_set').all()

    # Define el orden y los nombres de las columnas: (campo en models, nombre en Excel)
    columns = [
        ('municipality', 'Municipio'),
        ('neighborhood', 'Barrio'),
        ('street', 'Calle'),
        ('price', 'Precio (€)'),
        ('rooms', 'Habitaciones'),
        ('baths', 'Baños'),
        ('area', 'Superficie (m²)'),
        ('type_of_home', 'Tipo de vivienda'),
        ('ownership_status', 'Estado de propiedad'),
        ('floor_level', 'Planta'),
        ('elevator', 'Ascensor'),
        ('garage', 'Garaje'),
        ('pool', 'Piscina'),
        ('terrace', 'Terraza'),
        ('balcony', 'Balcón'),
        ('garden', 'Jardín'),
        ('fitted_wardrobes', 'Armarios empotrados'),
        ('air_conditioning', 'Aire acondicionado'),
        ('heating', 'Calefacción'),
        ('underfloor_heating', 'Suelo radiante'),
        ('storage_room', 'Trastero'),
        ('orientation', 'Orientación'),
        ('energy_calification', 'Calificación energética'),
        ('construction_year', 'Año construcción'),
        ('url', 'URL'),
    ]
    # Campos que son booleanos y deben indicar¨se como "Sí"/"No" en el Excel
    boolean_fields = {
        'elevator', 'garage', 'pool', 'terrace', 'balcony', 'garden',
        'fitted_wardrobes', 'air_conditioning', 'heating', 'underfloor_heating', 'storage_room'
    }
    data = []
    for prop in properties:
        # Obtiene las características asociadas a cada propiedad
        features = prop.propertyfeatures_set.first()
        row = []
        for field, _ in columns:
            if hasattr(prop, field):
                value = getattr(prop, field)
            elif features and hasattr(features, field):
                value = getattr(features, field)
            else:
                value = "Sin datos"
            if value is None:
                value = "Sin datos"
            # Formatea los booleanos como "Sí"/"No"
            if field in boolean_fields and value != "Sin datos":
                value = "Sí" if value else "No"
            row.append(value)
        data.append(row)

    # Nombres para las columnas del Excel
    column_names = [col[1] for col in columns]
    df = pd.DataFrame(data, columns=column_names)
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=propiedades.xlsx'
    df.to_excel(response, index=False, engine='openpyxl')
    return response