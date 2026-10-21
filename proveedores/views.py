from django.shortcuts import render
from django.views.generic import DetailView, ListView

from .models import Proveedor


def index(request):
    return render(request, 'proveedores/index.html', {})


class ProveedorListView(ListView):
    model = Proveedor
    template_name = 'proveedores/lista.html'
    context_object_name = 'proveedores'
    paginate_by = 20
    ordering = ['pk']


class ProveedorDetailView(DetailView):
    model = Proveedor
    template_name = 'proveedores/detalle.html'
    context_object_name = 'proveedor'

# proveedores/views.py — agregar imports al inicio:
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView, DeleteView, DetailView, ListView, UpdateView
)
from .forms import ProveedorForm


class ProveedorCreateView(LoginRequiredMixin, CreateView):
    """Formulario para crear un proveedor."""

    model         = Proveedor
    form_class    = ProveedorForm
    template_name = 'proveedores/crear.html'
    success_url   = reverse_lazy('proveedores:lista')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            f'Proveedor "{self.object.nombre}" creado exitosamente.'
        )
        return response


class ProveedorUpdateView(LoginRequiredMixin, UpdateView):
    """Formulario para editar un proveedor."""

    model         = Proveedor
    form_class    = ProveedorForm
    template_name = 'proveedores/editar.html'
    pk_url_kwarg  = 'proveedor_id'
    success_url   = reverse_lazy('proveedores:lista')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            f'Proveedor "{self.object.nombre}" actualizado.'
        )
        return response


class ProveedorDeleteView(LoginRequiredMixin, DeleteView):
    """Confirmación y borrado de un proveedor."""

    model         = Proveedor
    template_name = 'proveedores/eliminar.html'
    pk_url_kwarg  = 'proveedor_id'
    success_url   = reverse_lazy('proveedores:lista')

    def form_valid(self, form):
        nombre   = self.object.nombre
        response = super().form_valid(form)
        messages.success(self.request, f'Proveedor "{nombre}" eliminado.')
        return response