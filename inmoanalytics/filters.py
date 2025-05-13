import django_filters
from database.models import Properties

class PropertiesFilter(django_filters.FilterSet):
    price_min = django_filters.NumberFilter(field_name="price", lookup_expr='gte', label='Precio mínimo')
    price_max = django_filters.NumberFilter(field_name="price", lookup_expr='lte', label='Precio máximo')
    municipality = django_filters.CharFilter(lookup_expr='icontains', label='Municipio')
    neighborhood = django_filters.CharFilter(lookup_expr='icontains', label='Barrio')

    class Meta:
        model = Properties
        fields = ['price_min', 'price_max', 'municipality', 'neighborhood']