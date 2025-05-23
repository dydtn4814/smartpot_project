

from django.urls import path
from django.contrib import admin
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
  
    path('kakao/webhook/', views.kakao_webhook, name='kakao_webhook'),
   
    path("sensor/", views.sensor_data),
]
