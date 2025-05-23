

from django.urls import path
from django.contrib import admin
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('kakao/login/', views.login_kakao, name='kakao_login'),
    path('kakao/callback/', views.kakao_callback, name='kakao_callback'),
    path('kakao/webhook/', views.kakao_webhook, name='kakao_webhook'),
    path('kakao/send_message/', views.send_kakao_message, name='kakao_send_message'),
    path("sensor/", views.sensor_data),
]
