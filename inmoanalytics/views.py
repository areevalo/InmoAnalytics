from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render
from database.models import Properties
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

def property_list(request):
    f = PropertiesFilter(request.GET, queryset=Properties.objects.all().order_by('-id'))
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
        prop.price = f"{prop.price:,.0f} €".replace(",", ".") if prop.price else None
        features = prop.propertyfeatures_set.first()
        if features:
            prop.rooms = features.rooms
            prop.baths = features.baths
            prop.area = f"{features.area} m²" if features.area else None
            # min_year, max_year = parse_year_range(getattr(features, 'construction_year', None))
            # prop.construction_year_min = min_year
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