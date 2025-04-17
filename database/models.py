from django.db import models


class Properties(models.Model):
    id = models.BigAutoField(primary_key=True)
    url = models.TextField()
    price = models.IntegerField()
    municipality = models.CharField(max_length=50)
    neighborhood = models.CharField(max_length=50, blank=True, null=True)
    street = models.CharField(max_length=255, blank=True, null=True)
    origin = models.CharField(max_length=50)
    checksum = models.CharField(unique=True, max_length=255, blank=True, null=True)
    create_time_stamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'properties'
        app_label = 'database'


class PropertyFeatures(models.Model):
    id = models.BigAutoField(primary_key=True)
    property = models.ForeignKey(Properties, on_delete=models.CASCADE)  # Relación con Properties
    rooms = models.IntegerField()
    baths = models.IntegerField()
    area = models.IntegerField()
    type_of_home = models.CharField(max_length=50)
    pool = models.IntegerField(blank=True, null=True)
    garage = models.IntegerField(blank=True, null=True)
    energy_calification = models.CharField(max_length=50, blank=True, null=True)
    garden = models.IntegerField(blank=True, null=True)
    fitted_wardrobes = models.IntegerField(blank=True, null=True)
    air_conditioning = models.IntegerField(blank=True, null=True)
    underfloor_heating = models.IntegerField(blank=True, null=True)
    heating = models.IntegerField(blank=True, null=True)
    terrace = models.IntegerField(blank=True, null=True)
    storage_room = models.IntegerField(blank=True, null=True)
    ownership_status = models.CharField(max_length=50, blank=True, null=True)
    balcony = models.IntegerField(blank=True, null=True)
    floor_level = models.CharField(max_length=50, blank=True, null=True)
    elevator = models.IntegerField(blank=True, null=True)
    orientation = models.CharField(max_length=50, blank=True, null=True)
    construction_year = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'property_features'
        app_label = 'database'
