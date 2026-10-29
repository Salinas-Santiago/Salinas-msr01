from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView

from .forms import ProductoForm
from .models import Producto


# 2. VISTAS

class ProductoListView(ListView):
    model = Producto
    template_name = 'productos/lista.html'
    context_object_name = 'productos'
    paginate_by = 20


class ProductoDetailView(DetailView):
    model = Producto
    pk_url_kwarg = 'producto_id'
    template_name = 'productos/detalle.html'   # el nombre real de tu archivo
    
# productos/views.py — agregar los imports al inicio del archivo:
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView, DeleteView, DetailView, ListView, UpdateView
)

from .forms import ProductoForm


class ProductoCreateView(LoginRequiredMixin, CreateView):
    """Formulario para crear un nuevo producto.

    LoginRequiredMixin PRIMERO en la herencia (obligatorio).
    Redirige a /accounts/login/ si el usuario no está autenticado.
    """

    model         = Producto
    form_class    = ProductoForm
    template_name = 'productos/crear.html'
    success_url   = reverse_lazy('productos:lista')  # reverse_lazy (no reverse)

    def form_valid(self, form):
        """Agrega mensaje flash de éxito al guardar."""
        response = super().form_valid(form)
        messages.success(
            self.request,
            f'Producto "{self.object.nombre}" creado exitosamente.'
        )
        return response


class ProductoUpdateView(LoginRequiredMixin, UpdateView):
    """Formulario para editar un producto existente."""

    model         = Producto
    form_class    = ProductoForm
    template_name = 'productos/editar.html'
    pk_url_kwarg  = 'producto_id'
    success_url   = reverse_lazy('productos:lista')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            f'Producto "{self.object.nombre}" actualizado.'
        )
        return response


class ProductoDeleteView(LoginRequiredMixin, DeleteView):
    """Confirmación y borrado de un producto.

    SOLO acepta POST. El template debe incluir
    un formulario con {% csrf_token %} para evitar CSRF.
    """

    model         = Producto
    template_name = 'productos/eliminar.html'
    pk_url_kwarg  = 'producto_id'
    success_url   = reverse_lazy('productos:lista')

    def form_valid(self, form):
        nombre   = self.object.nombre
        response = super().form_valid(form)
        messages.success(
            self.request,
            f'Producto "{nombre}" eliminado.'
        )
        return response

# productos/views.py — actualizar el import al inicio:
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from core.mixins import LoginPermissionRequiredMixin

class ProductoDeleteView(LoginPermissionRequiredMixin, DeleteView):
    model               = Producto
    template_name       = 'productos/eliminar.html'
    pk_url_kwarg        = 'producto_id'
    success_url         = reverse_lazy('productos:lista')
    permission_required = 'productos.delete_producto'
    # sin raise_exception