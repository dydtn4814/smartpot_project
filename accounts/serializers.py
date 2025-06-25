from rest_framework import serializers
from .models import SensorData, SoilMoistureThreshold, HumidityThreshold, auto_function_date

class SensorDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = SensorData
        fields = ['temperature', 'humidity', 'soil_moisture', 'timestamp']
        
        
class SoilMoistureThresholdSerializer(serializers.ModelSerializer):
    class Meta:
        model = SoilMoistureThreshold
        fields = ['value','updated_at']
        
        
class HumidityThresholdSerializer(serializers.ModelSerializer):
    class Meta:
        model = HumidityThreshold
        fields = ['value','updated_at']
 

class auto_function_dateSerializer(serializers.ModelSerializer):
    class Meta:
        model = auto_function_date
        fields = ['pump_function_at','humidifier_function_at']        
        