from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('thank-you/', views.thank_you, name='thank_you'),
    path('webhook/telegram/', views.telegram_webhook, name='telegram_webhook'),
    path('inventory/', views.inventory, name='inventory'),
]

