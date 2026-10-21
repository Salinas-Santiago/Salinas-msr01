from django.urls import path

from . import views

app_name = 'ventas'

urlpatterns = [
    path('', views.index, name='inicio'),
    path('lista/', views.VentaListView.as_view(), name='lista'),
    path('<int:pk>/', views.VentaDetailView.as_view(), name='detalle'),
]
