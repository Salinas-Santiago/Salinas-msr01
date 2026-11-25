"""Vistas de la app productos — W07 + W08 + W09 + W12."""
import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView, DeleteView, DetailView, ListView, UpdateView
)

from .forms import ProductoForm
from .models import Producto


# ── Lectura (W07) ─────────────────────────────────────────────────────────

class ProductoListView(ListView):
    model               = Producto
    template_name       = 'productos/lista.html'
    context_object_name = 'productos'
    paginate_by         = 20
    ordering            = ['nombre']


class ProductoDetailView(DetailView):
    model               = Producto
    template_name       = 'productos/detalle.html'
    context_object_name = 'producto'
    pk_url_kwarg        = 'producto_id'


# ── Escritura (W08) ───────────────────────────────────────────────────────

class ProductoCreateView(LoginRequiredMixin, CreateView):
    model         = Producto
    form_class    = ProductoForm
    template_name = 'productos/crear.html'
    success_url   = reverse_lazy('productos:lista')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request, f'Producto "{self.object.nombre}" creado exitosamente.'
        )
        return response


class ProductoUpdateView(LoginRequiredMixin, UpdateView):
    model         = Producto
    form_class    = ProductoForm
    template_name = 'productos/editar.html'
    pk_url_kwarg  = 'producto_id'
    success_url   = reverse_lazy('productos:lista')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request, f'Producto "{self.object.nombre}" actualizado.'
        )
        return response


# ── Borrado con permisos (W09) ────────────────────────────────────────────

class ProductoDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Anónimo → 302 a login. Autenticado sin permiso → 403."""

    model               = Producto
    template_name       = 'productos/eliminar.html'
    pk_url_kwarg        = 'producto_id'
    success_url         = reverse_lazy('productos:lista')
    permission_required = 'productos.delete_producto'
    # NO poner raise_exception = True (convierte el 302 en 403)

    def form_valid(self, form):
        nombre   = self.object.nombre
        response = super().form_valid(form)
        messages.success(self.request, f'Producto "{nombre}" eliminado.')
        return response


# ── Excel (W12) ───────────────────────────────────────────────────────────

@login_required
def exportar_excel(request):
    """Genera y descarga el catálogo de productos en .xlsx."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Inventario ERP"

    headers = ["ID", "Nombre", "Categoría", "Proveedor", "Precio ($)", "Stock", "Estado"]
    ws.append(headers)

    header_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="0A2342", end_color="0A2342", fill_type="solid")
    for col in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")

    productos = Producto.objects.select_related('categoria', 'proveedor').all()
    for p in productos:
        ws.append([
            p.pk,
            p.nombre,
            p.categoria.nombre if p.categoria else "Sin categoría",
            p.proveedor.nombre if p.proveedor else "Sin proveedor",
            float(p.precio),
            p.stock,
            "Activo" if p.activo else "Inactivo",
        ])

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response['Content-Disposition'] = 'attachment; filename="inventario_productos.xlsx"'
    wb.save(response)
    return response