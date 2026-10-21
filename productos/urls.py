from django.urls import path

from . import views

app_name = 'productos'

urlpatterns = [
    path('', views.index, name='inicio'),
    path('lista/', views.ProductoListView.as_view(), name='lista'),
    path('<int:pk>/', views.ProductoDetailView.as_view(), name='detalle'),
]
