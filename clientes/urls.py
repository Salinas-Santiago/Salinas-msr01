from django.urls import path

from . import views

app_name = 'clientes'

urlpatterns = [
    path('', views.index, name='inicio'),
    path('lista/', views.ClienteListView.as_view(), name='lista'),
    path('<int:pk>/', views.ClienteDetailView.as_view(), name='detalle'),
]
