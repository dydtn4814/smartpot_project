from django.db import models

class SensorData(models.Model): # 센서 동향 모델
    timestamp = models.DateTimeField(auto_now_add=True)
    temperature = models.FloatField()
    humidity = models.FloatField()
    soil_moisture = models.FloatField()

    def __str__(self):
        return f"{self.timestamp} | Temp: {self.temperature}°C, Humi: {self.humidity}%, Soil: {self.soil_moisture}%"

class SoilMoistureThreshold(models.Model): # 자동급수 토양수분 기준 모델
    value = models.FloatField(help_text="기준 토양습도 (%)")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Threshold: {self.value}% (updated at {self.updated_at})"
    
class HumidityThreshold(models.Model): # 자동급수 토양수분 기준 모델
    value = models.FloatField(help_text="기준 습도 (%)")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Threshold: {self.value}% (updated at {self.updated_at})"
    
class auto_function_date(models.Model): # 자동실행 시간
    pump_function_at = models.DateTimeField(null=True, blank=True, default=None)
    humidifier_function_at = models.DateTimeField(null=True, blank=True, default=None)
    
    def __str__(self):
        return f"pump_function_at: {self.pump_function_at}, humidifier_function_at: {self.humidifier_function_at}"