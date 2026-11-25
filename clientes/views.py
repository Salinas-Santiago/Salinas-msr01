"""Vistas de la app clientes — W07 + W08 + W09."""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView, DeleteView, DetailView, ListView, UpdateView
)

from .forms import ClienteForm
from .models import Cliente


class ClienteListView(ListView):
    model               = Cliente
    template_name       = 'clientes/lista.html'
    context_object_name = 'clientes'


class ClienteDetailView(DetailView):
    model               = Cliente
    template_name       = 'clientes/detalle.html'
    context_object_name = 'cliente'
    pk_url_kwarg        = 'cliente_id'


class ClienteCreateView(LoginRequiredMixin, CreateView):
    model         = Cliente
    form_class    = ClienteForm
    template_name = 'clientes/crear.html'
    success_url   = reverse_lazy('clientes:lista')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request, f'Cliente "{self.object.nombre}" creado exitosamente.'
        )
        return response


class ClienteUpdateView(LoginRequiredMixin, UpdateView):
    model         = Cliente
    form_class    = ClienteForm
    template_name = 'clientes/editar.html'
    pk_url_kwarg  = 'cliente_id'
    success_url   = reverse_lazy('clientes:lista')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request, f'Cliente "{self.object.nombre}" actualizado.'
        )
        return response


class ClienteDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Anónimo → 302 a login. Autenticado sin permiso → 403."""

    model               = Cliente
    template_name       = 'clientes/eliminar.html'
    pk_url_kwarg        = 'cliente_id'
    success_url         = reverse_lazy('clientes:lista')
    permission_required = 'clientes.delete_cliente'

    def form_valid(self, form):
        nombre   = self.object.nombre
        response = super().form_valid(form)
        messages.success(self.request, f'Cliente "{nombre}" eliminado.')
        return response