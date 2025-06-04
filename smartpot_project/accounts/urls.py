

from django.urls import path
from django.contrib import admin
from . import views

urlpatterns = [


    path('kakao/webhook/', views.kakao_webhook, name='kakao_webhook'),
    path('sensor/receive/', views.receive_sensor_data, name='receive_sensor_data'),
    path('setting/soil_moisture_threshold/', views.set_soil_moisture_threshold, name='set_soil_moisture_threshold'),
    path('soil_moisture_threshold/', views.get_soil_moisture_threshold, name='get_soil_moisture_threshold'),
  
]
