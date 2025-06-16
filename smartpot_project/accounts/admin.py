from django.contrib import admin
from .models import SensorData, SoilMoistureThreshold, HumidityThreshold

@admin.register(SensorData)
class SensorDataAdmin(admin.ModelAdmin):
    list_display = ('temperature','humidity','soil_moisture','timestamp')


@admin.register(SoilMoistureThreshold)
class SoilMoistureThresholdAdmin(admin.ModelAdmin):
    list_display = ('value', 'updated_at')
        
@admin.register(HumidityThreshold)
class HumidityThresholdAdmin(admin.ModelAdmin):
    list_display = ('value', 'updated_at')
