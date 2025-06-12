from django.contrib import admin
from .models import SensorData, SoilMoistureThreshold

@admin.register(SensorData)
class SensorDataAdmin(admin.ModelAdmin):
    list_display = ('temperature','humidity','soil_moisture','timestamp')


@admin.register(SoilMoistureThreshold)
class SoilMoistureThresholdAdmin(admin.ModelAdmin):
    list_display = ('value', 'updated_at')
        
