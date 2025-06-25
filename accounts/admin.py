from django.contrib import admin
from .models import SensorData, SoilMoistureThreshold, HumidityThreshold, auto_function_date

@admin.register(SensorData)
class SensorDataAdmin(admin.ModelAdmin):
    list_display = ('temperature','humidity','soil_moisture','timestamp')


@admin.register(SoilMoistureThreshold)
class SoilMoistureThresholdAdmin(admin.ModelAdmin):
    list_display = ('value', 'updated_at')
        
@admin.register(HumidityThreshold)
class HumidityThresholdAdmin(admin.ModelAdmin):
    list_display = ('value', 'updated_at')
    
@admin.register(auto_function_date)
class auto_function_dateAdmin(admin.ModelAdmin):
    list_display = ('pump_function_at','humidifier_function_at')