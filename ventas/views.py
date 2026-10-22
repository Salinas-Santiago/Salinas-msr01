from decimal import Decimal

from django.shortcuts import render
from django.views.generic import DetailView, ListView

from .models import DetalleVenta, Venta


def index(request):
    return render(request, 'ventas/index.html', {})


class VentaListView(ListView):
    model = Venta
    template_name = 'ventas/lista.html'
    context_object_name = 'ventas'
    paginate_by = 20
    ordering = ['pk']


class VentaDetailView(DetailView):
    model = Venta
    pk_url_kwarg = 'venta_id'
    template_name = 'ventas/detalle.html'
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        filas = []
        total = Decimal('0')
        detalles = DetalleVenta.objects.filter(venta=self.object)
        for d in detalles.select_related('producto'):
            subtotal = d.cantidad * d.precio_unitario
            total += subtotal
            filas.append({
                'producto': d.producto,
                'cantidad': d.cantidad,
                'precio_unitario': d.precio_unitario,
                'subtotal': subtotal,
            })
        ctx['filas'] = filas
        ctx['total'] = total
        return ctx

# ventas/views.py — agregar imports al inicio:
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import DeleteView, DetailView, ListView

from .forms  import DetalleVentaForm, VentaForm
from .models import DetalleVenta, Venta


def crear_venta(request):
    """Crea un encabezado de venta con una línea de detalle.

    GET  → muestra los dos formularios vacíos.
    POST → valida ambos, guarda si correctos, muestra errores si no.

    Protección: redirige a login si no autenticado.
    Nota: para múltiples líneas usar formsets (implementar en Espiral 5).
    """
    if not request.user.is_authenticated:
        return redirect(
            f"{settings.LOGIN_URL}?next={request.path}"
        )

    venta_form   = VentaForm(request.POST or None)
    detalle_form = DetalleVentaForm(request.POST or None)

    if request.method == 'POST':
        if venta_form.is_valid() and detalle_form.is_valid():
            venta          = venta_form.save()
            detalle        = detalle_form.save(commit=False)
            detalle.venta  = venta
            # precio_unitario se auto-captura en save() si es None
            detalle.save()
            messages.success(
                request,
                f'Venta #{venta.pk} registrada. '
                f'Total: ${venta.total:.2f}'
            )
            return redirect('ventas:detalle', venta_id=venta.pk)

    return render(request, 'ventas/crear.html', {
        'venta_form':   venta_form,
        'detalle_form': detalle_form,
    })


class VentaDeleteView(LoginRequiredMixin, DeleteView):
    """Confirmación y borrado de una venta (y sus detalles en cascada)."""

    model         = Venta
    template_name = 'ventas/eliminar.html'
    pk_url_kwarg  = 'venta_id'
    success_url   = reverse_lazy('ventas:lista')

    def form_valid(self, form):
        pk       = self.object.pk
        response = super().form_valid(form)
        messages.success(self.request, f'Venta #{pk} eliminada.')
        return response