from django.core.paginator import Paginator
from django.shortcuts import render
from database.models import Properties
from .filters import PropertiesFilter
from .utils import parse_year_range

def property_list(request):
    f = PropertiesFilter(request.GET, queryset=Properties.objects.all())
    properties_qs = f.qs
    paginator = Paginator(properties_qs, 100)  # 20 propiedades por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    properties = []
    for prop in page_obj:
        features = prop.propertyfeatures_set.first()
        if features:
            prop.rooms = features.rooms
            prop.baths = features.baths
            prop.area = f"{features.area} m²" if features.area else None
            # min_year, max_year = parse_year_range(getattr(features, 'construction_year', None))
            # prop.construction_year_min = min_year
            # prop.construction_year_max = max_year
        else:
            prop.baths = prop.rooms = prop.area = None
            # prop.construction_year_min = prop.construction_year_max = None

        properties.append(prop)
    return render(request, 'property_list.html', {
        'filter': f,
        'properties': properties,
        'page_obj': page_obj
    })