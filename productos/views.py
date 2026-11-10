# productos/views.py
"""Vistas de la app productos — W07–W12."""
import openpyxl
from openpyxl.styles import Font, PatternFill
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView, DeleteView, DetailView, ListView, UpdateView
)

from .forms import ProductoForm
from .models import Categoria, Producto


class ProductoListView(ListView):
    """Lista de todos los productos."""
    model = Producto
    template_name = 'productos/lista.html'
    context_object_name = 'productos'


class ProductoDetailView(DetailView):
    """Detalle individual de un producto."""
    model = Producto
    template_name = 'productos/detalle.html'
    context_object_name = 'producto'
    pk_url_kwarg = 'producto_id'


class ProductoCreateView(LoginRequiredMixin, CreateView):
    """Formulario para crear un producto."""
    model = Producto
    form_class = ProductoForm
    template_name = 'productos/crear.html'
    success_url = reverse_lazy('productos:lista')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            f'Producto "{self.object.nombre}" creado exitosamente.'
        )
        return response


class ProductoUpdateView(LoginRequiredMixin, UpdateView):
    """Formulario para editar un producto."""
    model = Producto
    form_class = ProductoForm
    template_name = 'productos/editar.html'
    pk_url_kwarg = 'producto_id'
    success_url = reverse_lazy('productos:lista')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            f'Producto "{self.object.nombre}" actualizado.'
        )
        return response


class ProductoDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Eliminación de un producto."""
    model = Producto
    template_name = 'productos/eliminar.html'
    pk_url_kwarg = 'producto_id'
    success_url = reverse_lazy('productos:lista')
    permission_required = 'productos.delete_producto'
    raise_exception = True

    def form_valid(self, form):
        nombre = self.object.nombre
        response = super().form_valid(form)
        messages.success(self.request, f'Producto "{nombre}" eliminado.')
        return response


@login_required
def exportar_productos_excel(request):
    """Exporta el catálogo de productos a Excel (W12)."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Productos"

    headers = ["ID", "Nombre", "Categoría", "Precio", "Stock", "Activo"]
    ws.append(headers)

    header_fill = PatternFill(start_color="1B365D", end_color="1B365D", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font

    productos = Producto.objects.select_related('categoria').all()
    for p in productos:
        cat_nombre = p.categoria.nombre if p.categoria else "Sin categoría"
        ws.append([p.pk, p.nombre, cat_nombre, float(p.precio), p.stock, "Sí" if p.activo else "No"])

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response['Content-Disposition'] = 'attachment; filename="catalogo_productos.xlsx"'
    wb.save(response)
    return response