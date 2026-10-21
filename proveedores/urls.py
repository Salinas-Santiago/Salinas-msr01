from django.urls import path

from . import views

app_name = 'proveedores'

urlpatterns = [
    path('', views.index, name='inicio'),
    path('lista/', views.ProveedorListView.as_view(), name='lista'),
    path('<int:pk>/', views.ProveedorDetailView.as_view(), name='detalle'),
]
