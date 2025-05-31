from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.safestring import mark_safe
from database.models import Properties
from .filters import PropertiesFilter

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
    f = PropertiesFilter(request.GET, queryset=Properties.objects.filter(active=1).order_by('-id'))
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
            prop.construction_year = features.construction_year
            prop.type_of_home = features.type_of_home
            prop.ownership_status = features.ownership_status
            prop.is_new_home = "Obra nueva" if features.construction_year == "Obra nueva" else "Segunda mano"
            prop.floor = features.floor_level
            prop.elevator = "Sí" if features.elevator else "No"
            prop.garage = "Sí" if features.garage else "No"
        else:
            prop.baths = prop.rooms = prop.area = prop.floor = prop.elevator = prop.garage = None
            prop.type_of_home = prop.ownership_status = prop.construction_year = None

        properties.append(prop)
    return render(request, 'property_list.html', {
        'filter': f,
        'properties': properties,
        'page_obj': page_obj,
    })