# productos/views.py
"""Vistas de la app productos — W07 + W08 + W09 + W11 + W12."""
import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView, DeleteView, DetailView, ListView, UpdateView
)

from .forms import ProductoForm
from .models import Producto


# ── W07: lectura ───────────────────────────────────────────────────────────
class ProductoListView(ListView):
    """Lista de productos, 20 por página."""
    model               = Producto
    template_name       = 'productos/lista.html'
    context_object_name = 'productos'
    paginate_by         = 20

    def get_queryset(self):
        return Producto.objects.select_related('categoria', 'proveedor')


class ProductoDetailView(DetailView):
    """Detalle de un producto."""
    model         = Producto
    template_name = 'productos/detalle.html'
    pk_url_kwarg  = 'producto_id'


# ── W08: crear y editar ────────────────────────────────────────────────────
class ProductoCreateView(LoginRequiredMixin, CreateView):
    model         = Producto
    form_class    = ProductoForm
    template_name = 'productos/crear.html'
    success_url   = reverse_lazy('productos:lista')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            f'Producto "{self.object.nombre}" creado exitosamente.'
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
            self.request,
            f'Producto "{self.object.nombre}" actualizado.'
        )
        return response


# ── W09: eliminar con permisos ─────────────────────────────────────────────
class ProductoDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Borrado de producto.

    Sin sesión       → redirige al login (302).
    Sin el permiso   → HTTP 403 (raise_exception=True).
    """
    model               = Producto
    template_name       = 'productos/eliminar.html'
    pk_url_kwarg        = 'producto_id'
    success_url         = reverse_lazy('productos:lista')
    permission_required = 'productos.delete_producto'
    raise_exception     = True

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect_to_login(
                self.request.get_full_path(),
                self.get_login_url(),
                self.get_redirect_field_name(),
            )
        return super().handle_no_permission()

    def form_valid(self, form):
        nombre   = self.object.nombre
        response = super().form_valid(form)
        messages.success(self.request, f'Producto "{nombre}" eliminado.')
        return response


# ── W12: exportar inventario a Excel ───────────────────────────────────────
@login_required
def exportar_excel(request):
    """Genera y descarga un libro de Excel (.xlsx) con el catálogo de productos."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Inventario ERP"

    headers = ["ID", "Nombre", "Categoría", "Proveedor", "Precio ($)", "Stock", "Estado"]
    ws.append(headers)

    header_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="0A2342", end_color="0A2342", fill_type="solid")

    for col in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col)
        cell.font      = header_font
        cell.fill      = header_fill
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

    for i, ancho in enumerate([8, 35, 22, 25, 14, 10, 12], start=1):
        ws.column_dimensions[get_column_letter(i)].width = ancho
    ws.freeze_panes = "A2"

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response['Content-Disposition'] = 'attachment; filename="inventario_productos.xlsx"'
    wb.save(response)
    return response