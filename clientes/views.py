from django.shortcuts import render
from django.views.generic import DetailView, ListView

from .models import Cliente


def index(request):
    return render(request, 'clientes/index.html', {})


class ClienteListView(ListView):
    model = Cliente
    template_name = 'clientes/lista.html'
    context_object_name = 'clientes'
    paginate_by = 20
    ordering = ['pk']


class ClienteDetailView(DetailView):
    model = Cliente
    template_name = 'clientes/detalle.html'
    context_object_name = 'cliente'

# clientes/views.py — agregar imports al inicio:
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView, DeleteView, DetailView, ListView, UpdateView
)
from .forms import ClienteForm


class ClienteCreateView(LoginRequiredMixin, CreateView):
    """Formulario para crear un nuevo cliente."""

    model         = Cliente
    form_class    = ClienteForm
    template_name = 'clientes/crear.html'
    success_url   = reverse_lazy('clientes:lista')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            f'Cliente "{self.object.nombre}" creado exitosamente.'
        )
        return response


class ClienteUpdateView(LoginRequiredMixin, UpdateView):
    """Formulario para editar un cliente."""

    model         = Cliente
    form_class    = ClienteForm
    template_name = 'clientes/editar.html'
    pk_url_kwarg  = 'cliente_id'
    success_url   = reverse_lazy('clientes:lista')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            f'Cliente "{self.object.nombre}" actualizado.'
        )
        return response


class ClienteDeleteView(LoginRequiredMixin, DeleteView):
    """Confirmación y borrado de un cliente."""

    model         = Cliente
    template_name = 'clientes/eliminar.html'
    pk_url_kwarg  = 'cliente_id'
    success_url   = reverse_lazy('clientes:lista')

    def form_valid(self, form):
        nombre   = self.object.nombre
        response = super().form_valid(form)
        messages.success(self.request, f'Cliente "{nombre}" eliminado.')
        return response