from rest_framework import serializers
from .models import SensorData, SoilMoistureThreshold, HumidityThreshold

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