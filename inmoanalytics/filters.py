import django_filters
import django.db.models as models
from django import forms
from database.models import Properties, PropertyFeatures

FLOOR_LEVEL_CHOICES = [
    ('', 'Cualquiera'),
    ('bajo', 'Planta baja'),
    ('sotano', 'Sótano'),
    ('semi-sotano', 'Semi-sótano'),
    ('entresuelo', 'Entresuelo'),
    ('entreplanta', 'Entreplanta'),
    ('1+', '1º o más'),
    ('3+', '3º o más'),
    ('5+', '5º o más'),
    ('7+', '7º o más'),
    ('10+', '10º o más'),
    ('15+', '15º o más'),
]

CONSTRUCTION_YEAR_CHOICES = [
    ('', 'Cualquiera'),
    ('2020-2024', '2020-2024'),
    ('2015-2020', '2015-2020'),
    ('2005-2015', '2005-2015'),
    ('1995-2005', '1995-2005'),
    ('1975-1995', '1975-1995'),
    ('1955-1975', '1955-1975'),
    ('1925-1955', '1925-1955'),
    ('<1925', 'Antes de 1925'),
    ('>2024', 'Después de 2024'),
]

energy_ratings = ['A', 'B', 'C', 'D', 'E', 'F', 'G']

def get_energy_choices():
    return [('', 'Cualquiera')] + [
        (rating, f"{rating} o mejor") for rating in reversed(energy_ratings)
    ]


def filter_boolean_as_true(queryset, name, value):
    if value:
        return queryset.filter(**{name: True})
    return queryset


class PropertiesFilter(django_filters.FilterSet):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filters['municipality'].field.empty_label = None
        self.filters['min_rooms'].field.empty_label = None
        self.filters['min_baths'].field.empty_label = None
        self.filters['construction_type'].field.empty_label = None
        self.filters['type_of_home'].field.empty_label = None
        self.filters['ownership_status'].field.empty_label = None
        self.filters['min_energy_calification'].field.empty_label = None
        self.filters['orientation'].field.empty_label = None
        self.filters['floor_level'].field.empty_label = None
        self.filters['construction_year'].field.empty_label = None
        for name, field in self.form.fields.items():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs['class'] = 'form-select'

    def filter_construction_year_range(queryset, name, value):
        if not value:
            return queryset
        if value.startswith('<'):
            return queryset.filter(
                propertyfeatures__construction_year__lt='1925'
            )
        elif value.startswith('>'):
            return queryset.filter(
                propertyfeatures__construction_year__gt='2024'
            )
        elif '-' in value:
            start, end = value.split('-')
            # Incluye tanto los años exactos (como enteros) como los strings en el rango
            return queryset.filter(
                (
                        models.Q(propertyfeatures__construction_year__gte=start) &
                        models.Q(propertyfeatures__construction_year__lte=end)
                ) |
                models.Q(propertyfeatures__construction_year__in=[str(y) for y in range(int(start), int(end) + 1)])
            )
        return queryset


    def filter_floor_level(queryset, name, value):
        if value == 'bajo':
            return queryset.filter(propertyfeatures__floor_level__iexact='Bajo')
        elif value == 'sotano':
            return queryset.filter(propertyfeatures__floor_level__iexact='Sótano')
        elif value == 'semi-sotano':
            return queryset.filter(propertyfeatures__floor_level__iexact='Semi-sótano')
        elif value == 'entresuelo':
            return queryset.filter(propertyfeatures__floor_level__iexact='Entresuelo')
        elif value == 'entreplanta':
            return queryset.filter(propertyfeatures__floor_level__iexact='Entreplanta')
        elif value == '15+':
            return queryset.filter(propertyfeatures__floor_level__iexact='>15')
        elif value and value.endswith('+'):
            num = int(value[:-1])
            # Filtra los valores numéricos mayores o iguales a num
            return queryset.filter(
                propertyfeatures__floor_level__in=[str(i) for i in range(num, 16)]
            )
        return queryset

    price_min = django_filters.NumberFilter(field_name="price", lookup_expr='gte', label='Precio mínimo')
    price_max = django_filters.NumberFilter(field_name="price", lookup_expr='lte', label='Precio máximo')
    municipality = django_filters.ChoiceFilter(
        field_name='municipality',
        label='Municipio',
        choices=lambda: [('', 'Cualquiera')] + [(m, m) for m in Properties.objects.order_by('municipality').values_list('municipality', flat=True).distinct() if m]
    )


    min_rooms = django_filters.ChoiceFilter(
        label='Habitaciones',
        choices=[('', 'Cualquiera')] + [(str(i), f'{i}+') for i in range(1, 5)],
        method='filter_min_rooms',
        widget=forms.Select(attrs={'id': 'min_rooms', 'class': 'form-select'})
    )
    min_baths = django_filters.ChoiceFilter(
        label='Baños',
        choices=[('', 'Cualquiera')] + [(str(i), f'{i}+') for i in range(1, 4)],
        method='filter_min_baths',
        widget=forms.Select(attrs={'id': 'min_baths', 'class': 'form-select'})
    )
    min_area = django_filters.NumberFilter(
        field_name="propertyfeatures__area",
        lookup_expr='gte',
        label='Superficie mínima (m²)',
        widget=forms.NumberInput(attrs={
            'id': 'min_area',
            'class': 'form-control',
            'placeholder': 'Mínimo',
            'min': 0
        })
    )
    ownership_status = django_filters.ChoiceFilter(
        field_name='propertyfeatures__ownership_status',
        label='Estado de propiedad',
        choices=lambda: [('', 'Cualquiera')] + [
            (s, s) for s in PropertyFeatures.objects.order_by('ownership_status')
            .values_list('ownership_status', flat=True).distinct() if s
        ]
    )

    floor_level = django_filters.ChoiceFilter(
        label='Planta',
        choices=FLOOR_LEVEL_CHOICES,
        method=filter_floor_level,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    min_energy_calification = django_filters.ChoiceFilter(
        label='Calificación energética',
        choices=get_energy_choices,
        method='filter_min_energy_calification'
    )

    orientation = django_filters.ChoiceFilter(
        field_name='propertyfeatures__orientation',
        label='Orientación',
        choices=lambda: [('', 'Cualquiera')] + [
            (o, o) for o in PropertyFeatures.objects.order_by('orientation')
            .values_list('orientation', flat=True).distinct() if o
        ]
    )

    construction_year = django_filters.ChoiceFilter(
        label='Año construcción',
        choices=CONSTRUCTION_YEAR_CHOICES,
        method=filter_construction_year_range,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    neighborhood = django_filters.CharFilter(
        field_name='neighborhood',
        label='Barrio',
        lookup_expr='icontains'
    )

    # Boolean filters (extras checklist)
    elevator = django_filters.BooleanFilter(
        field_name="propertyfeatures__elevator",
        label='Ascensor',
        method=filter_boolean_as_true,
        widget=forms.CheckboxInput()
    )
    garage = django_filters.BooleanFilter(
        field_name="propertyfeatures__garage",
        label='Garaje',
        method=filter_boolean_as_true,
        widget=forms.CheckboxInput()
    )
    fitted_wardrobes = django_filters.BooleanFilter(
        field_name="propertyfeatures__fitted_wardrobes",
        label='Armarios empotrados',
        method=filter_boolean_as_true,
        widget=forms.CheckboxInput()
    )
    storage_room = django_filters.BooleanFilter(
        field_name="propertyfeatures__storage_room",
        label='Trastero',
        method=filter_boolean_as_true,
        widget=forms.CheckboxInput()
    )
    air_conditioning = django_filters.BooleanFilter(
        field_name="propertyfeatures__air_conditioning",
        label='Aire acondicionado',
        method=filter_boolean_as_true,
        widget=forms.CheckboxInput()
    )
    heating = django_filters.BooleanFilter(
        field_name="propertyfeatures__heating",
        label='Calefacción',
        method=filter_boolean_as_true,
        widget=forms.CheckboxInput()
    )
    underfloor_heating = django_filters.BooleanFilter(
        field_name="propertyfeatures__underfloor_heating",
        label='Suelo radiante',
        method=filter_boolean_as_true,
        widget=forms.CheckboxInput()
    )
    pool = django_filters.BooleanFilter(
        field_name="propertyfeatures__pool",
        label='Piscina',
        method=filter_boolean_as_true,
        widget=forms.CheckboxInput()
    )
    terrace = django_filters.BooleanFilter(
        field_name="propertyfeatures__terrace",
        label='Terraza',
        method=filter_boolean_as_true,
        widget=forms.CheckboxInput()
    )
    balcony = django_filters.BooleanFilter(
        field_name="propertyfeatures__balcony",
        label='Balcón',
        method=filter_boolean_as_true,
        widget=forms.CheckboxInput()
    )
    garden = django_filters.BooleanFilter(
        field_name="propertyfeatures__garden",
        label='Jardín',
        method=filter_boolean_as_true,
        widget=forms.CheckboxInput()
    )

    type_of_home = django_filters.ChoiceFilter(
        field_name='propertyfeatures__type_of_home',
        label='Tipo de vivienda',
        choices=lambda: [('', 'Cualquiera')] + [
            (t, t) for t in
            PropertyFeatures.objects.order_by('type_of_home').values_list('type_of_home', flat=True).distinct() if t
        ]
    )
    construction_type = django_filters.ChoiceFilter(
        label='Tipo de construcción',
        method='filter_construction_type',
        choices=[('', 'Cualquiera'), ('obra_nueva', 'Obra nueva'), ('segunda_mano', 'Segunda mano')]
    )


    class Meta:
        model = Properties
        fields = [
            'price_min', 'price_max', 'municipality', 'neighborhood',
            'min_rooms', 'min_baths',
            'min_area', 'terrace', 'pool', 'balcony',
            'garden', 'heating', 'air_conditioning',
            'type_of_home', 'construction_type',
            'elevator', 'garage', 'pool', 'ownership_status', 'floor_level',
            'orientation', 'construction_year', 'min_energy_calification'
        ]

    def filter_min_rooms(self, queryset, name, value):
        if value:
            return queryset.filter(propertyfeatures__rooms__gte=int(value))
        return queryset

    def filter_min_baths(self, queryset, name, value):
        if value:
            return queryset.filter(propertyfeatures__baths__gte=int(value))
        return queryset

    def filter_construction_type(self, queryset, name, value):
        if value == 'obra_nueva':
            return queryset.filter(propertyfeatures__construction_year='Obra nueva')
        else:
            return queryset.exclude(propertyfeatures__construction_year='Segunda mano')

    def filter_min_energy_calification(self, queryset, name, value):
        if value:
            idx = energy_ratings.index(value)
            allowed = energy_ratings[:idx+1]
            return queryset.filter(
                propertyfeatures__energy_calification__in=allowed
            )
        # Si no hay valor, incluye también los NULL
        return queryset.filter(propertyfeatures__energy_calification__isnull=True) | queryset

