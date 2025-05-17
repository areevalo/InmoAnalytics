import django_filters
from database.models import Properties, PropertyFeatures


class PropertiesFilter(django_filters.FilterSet):
        price_min = django_filters.NumberFilter(field_name="price", lookup_expr='gte', label='Precio mínimo')
        price_max = django_filters.NumberFilter(field_name="price", lookup_expr='lte', label='Precio máximo')
        municipality = django_filters.ChoiceFilter(
            field_name='municipality',
            label='Municipio',
            choices=lambda: [(m, m) for m in Properties.objects.order_by('municipality').values_list('municipality', flat=True).distinct() if m]
        )
        neighborhood = django_filters.CharFilter(lookup_expr='icontains', label='Barrio')
        # min_year = django_filters.NumberFilter(field_name="propertyfeatures__construction_year", lookup_expr='gte', label='Año construcción desde')
        # max_year = django_filters.NumberFilter(field_name="propertyfeatures__construction_year", lookup_expr='lte', label='Año construcción hasta')

        min_rooms = django_filters.NumberFilter(field_name="propertyfeatures__rooms", lookup_expr='gte', label='Habitaciones mínimas')
        min_bathrooms = django_filters.NumberFilter(field_name="propertyfeatures__baths", lookup_expr='gte', label='Baños mínimos')
        min_area = django_filters.NumberFilter(field_name="propertyfeatures__area", lookup_expr='gte', label='Superficie mínima (m²)')
        max_area = django_filters.NumberFilter(field_name="propertyfeatures__area", lookup_expr='lte', label='Superficie máxima (m²)')

        terrace = django_filters.BooleanFilter(field_name="propertyfeatures__terrace", label='Terraza')
        pool = django_filters.BooleanFilter(field_name="propertyfeatures__pool", label='Piscina')
        balcony = django_filters.BooleanFilter(field_name="propertyfeatures__balcony", label='Balcón')
        garden = django_filters.BooleanFilter(field_name="propertyfeatures__garden", label='Jardín')
        heating = django_filters.BooleanFilter(field_name="propertyfeatures__heating", label='Calefacción')
        air_conditioning = django_filters.BooleanFilter(field_name="propertyfeatures__air_conditioning", label='Aire acondicionado')

        type_of_home = django_filters.ChoiceFilter(
            field_name='propertyfeatures__type_of_home',
            label='Tipo de vivienda',
            choices=lambda: [
                (t, t) for t in
                PropertyFeatures.objects.order_by('type_of_home').values_list('type_of_home', flat=True).distinct() if t
            ]
        )
        construction_type = django_filters.ChoiceFilter(
            label='Tipo de construcción',
            method='filter_construction_type',
            choices=[('obra_nueva', 'Obra nueva'), ('segunda_mano', 'Segunda mano')]
        )

        def filter_construction_type(self, queryset, name, value):
            if value == 'obra_nueva':
                return queryset.filter(propertyfeatures__construction_year='Obra nueva')
            else:
                return queryset.exclude(propertyfeatures__construction_year='Segunda mano')


        class Meta:
            model = Properties
            fields = [
                'price_min', 'price_max', 'municipality', 'neighborhood',
                # 'min_year', 'max_year',
                'min_rooms', 'min_bathrooms',
                'min_area', 'max_area', 'terrace', 'pool', 'balcony',
                'garden', 'heating', 'air_conditioning',
                'type_of_home', 'construction_type'
                # , 'property_status'
            ]