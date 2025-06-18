

from django.urls import path
from django.contrib import admin
from . import views

urlpatterns = [


    path('kakao/webhook/', views.kakao_webhook, name='kakao_webhook'),
    path('sensor/receive/', views.receive_sensor_data, name='receive_sensor_data'), # 라즈베리파이 서버에서 접근
    path('soil_moisture_threshold/', views.get_soil_moisture_threshold, name='get_soil_moisture_threshold'), # 라즈베리파이 서버에서 접근
    path('humidity_threshold/', views.get_humidity_threshold, name='get_humidity_threshold'), # 라즈베리파이 서버에서 접근
    path('setting_values/', views.get_setting_values, name='get_setting_values'),
    path('number/receive/', views.receive_number, name='receive_number')
    
]
