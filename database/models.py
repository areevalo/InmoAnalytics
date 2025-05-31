from django.db import models


class Properties(models.Model):
    """Representa una propiedad inmobiliaria y su información básica.

    Almacena detalles como la URL del anuncio, precio, ubicación y metadatos
    para el seguimiento y la gestión de la propiedad"""
    id = models.BigAutoField(primary_key=True)
    url = models.TextField()
    price = models.IntegerField()
    municipality = models.CharField(max_length=50)
    neighborhood = models.CharField(max_length=50, blank=True, null=True)
    street = models.CharField(max_length=255, blank=True, null=True)
    origin = models.CharField(max_length=50)
    checksum = models.CharField(unique=True, max_length=255, blank=True, null=True)
    active = models.BooleanField(default=True)
    create_time_stamp = models.DateTimeField(auto_now_add=True)
    update_time_stamp = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False  # Indica que la tabla es gestionada externamente (en este caso phpMyAdmin del hosting)
        db_table = 'properties'
        app_label = 'database'


class PropertyFeatures(models.Model):
    """Almacena características detalladas de una propiedad específica.

    Incluye información sobre número de habitaciones, baños, área,
    entre otros atributos"""

    id = models.BigAutoField(primary_key=True)
    # Relación con Properties. Especifica que se elimine en cascada junto con la propiedad
    property = models.ForeignKey(Properties, on_delete=models.CASCADE)
    rooms = models.IntegerField()
    baths = models.IntegerField()
    area = models.IntegerField()
    type_of_home = models.CharField(max_length=50)
    pool = models.BooleanField(blank=True, null=True)
    garage = models.BooleanField(blank=True, null=True)
    energy_calification = models.CharField(max_length=50, blank=True, null=True)
    garden = models.BooleanField(blank=True, null=True)
    fitted_wardrobes = models.BooleanField(blank=True, null=True)
    air_conditioning = models.BooleanField(blank=True, null=True)
    underfloor_heating = models.BooleanField(blank=True, null=True)
    heating = models.BooleanField(blank=True, null=True)
    terrace = models.BooleanField(blank=True, null=True)
    storage_room = models.BooleanField(blank=True, null=True)
    ownership_status = models.CharField(max_length=50, blank=True, null=True)
    balcony = models.BooleanField(blank=True, null=True)
    floor_level = models.CharField(max_length=50, blank=True, null=True)
    elevator = models.BooleanField(blank=True, null=True)
    orientation = models.CharField(max_length=50, blank=True, null=True)
    construction_year = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'property_features'
        app_label = 'database'
