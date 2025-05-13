from django.shortcuts import render
from database.models import Properties
from .filters import PropertiesFilter

def property_list(request):
    f = PropertiesFilter(request.GET, queryset=Properties.objects.all())
    return render(request, 'property_list.html', {'filter': f})