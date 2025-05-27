import pandas as pd

from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.utils.safestring import mark_safe
from database.models import Properties, PropertyFeatures
from .filters import PropertiesFilter
from .utils import parse_year_range

def get_neighborhoods(request):
    municipality = request.GET.get('municipality')
    neighborhoods = []
    if municipality:
        neighborhoods = list(
            Properties.objects.filter(municipality=municipality)
            .order_by('neighborhood')
            .values_list('neighborhood', flat=True)
            .distinct()
        )
    return JsonResponse({'neighborhoods': [n for n in neighborhoods if n]})

def export_properties_excel(request):
    f = PropertiesFilter(request.GET, queryset=Properties.objects.all())
    properties = f.qs.prefetch_related('propertyfeatures_set').all()

    # Define el orden y los nombres de las columnas: (campo, nombre en español)
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
    boolean_fields = {
        'elevator', 'garage', 'pool', 'terrace', 'balcony', 'garden',
        'fitted_wardrobes', 'air_conditioning', 'heating', 'underfloor_heating', 'storage_room'
    }
    data = []
    for prop in properties:
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
    df.to_excel(response, index=False)
    return response

def property_list(request):
    f = PropertiesFilter(request.GET, queryset=Properties.objects.filter(active=1).order_by('-id'))
    # boolean_fields = [
    #     ('air_conditioning', 'Aire acondicionado'),
    #     ('balcony', 'Balcón'),
    #     ('elevator', 'Ascensor'),
    #     ('fitted_wardrobes', 'Armarios empotrados'),
    #     ('garage', 'Garaje'),
    #     ('garden', 'Jardín'),
    #     ('heating', 'Calefacción'),
    #     ('pool', 'Piscina'),
    #     ('storage_room', 'Trastero'),
    #     ('terrace', 'Terraza'),
    #     ('underfloor_heating', 'Suelo radiante'),
    # ]
    # # Ordenar por etiqueta
    # boolean_fields_sorted = sorted(boolean_fields, key=lambda x: x[1])
    properties_qs = f.qs
    paginator = Paginator(properties_qs, 50)  # 20 propiedades por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    properties = []
    for prop in page_obj:
        prop.price = mark_safe(f"{prop.price:,.0f}&nbsp;€".replace(",", ".")) if prop.price else None
        features = prop.propertyfeatures_set.first()
        if features:
            prop.rooms = features.rooms
            prop.baths = features.baths
            prop.area = f"{features.area} m²" if features.area else None
            # min_year, max_year = parse_year_range(getattr(features, 'construction_year', None))
            prop.construction_year = features.construction_year
            # prop.construction_year_max = max_year
            prop.type_of_home = features.type_of_home
            prop.ownership_status = features.ownership_status
            prop.is_new_home = "Obra nueva" if features.construction_year == "Obra nueva" else "Segunda mano"
            prop.floor = features.floor_level
            prop.elevator = "Sí" if features.elevator else "No"
            prop.garage = "Sí" if features.garage else "No"
        else:
            prop.baths = prop.rooms = prop.area = prop.floor = prop.elevator = prop.garage = None
            prop.type_of_home = prop.ownership_status = prop.construction_year = None
            # prop.construction_year_min = prop.construction_year_max = None

        properties.append(prop)
    return render(request, 'property_list.html', {
        'filter': f,
        'properties': properties,
        'page_obj': page_obj,
        # 'boolean_fields_sorted': boolean_fields_sorted,
    })