# ventas/urls_tareas.py
from django.urls import path

from ventas import views_tareas

urlpatterns = [
    path('<str:nombre>/', views_tareas.ejecutar_tarea, name='ejecutar_tarea'),
]