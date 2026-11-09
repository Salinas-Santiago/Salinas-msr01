# ventas/views.py
"""Vistas de la app ventas — W07 + W08 + W09 + W12."""
import io

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.views.generic import DeleteView, DetailView, ListView

from xhtml2pdf import pisa

from configuracion.models import ConfiguracionERP
from .forms import DetalleVentaForm, VentaForm
from .models import DetalleVenta, Venta


# ── W07: lectura ───────────────────────────────────────────────────────────
class VentaListView(ListView):
    """Lista de ventas."""
    model         = Venta
    template_name = 'ventas/lista.html'

    def get_queryset(self):
        return Venta.objects.select_related('cliente')


class VentaDetailView(DetailView):
    """Detalle de una venta con sus líneas."""
    model         = Venta
    template_name = 'ventas/detalle.html'
    pk_url_kwarg  = 'venta_id'

    def get_queryset(self):
        return (
            Venta.objects
            .select_related('cliente')
            .prefetch_related('detalles__producto')
        )


# ── W08 + W09: crear venta ─────────────────────────────────────────────────
@login_required
@permission_required('ventas.add_venta', raise_exception=True)
def crear_venta(request):
    """Crea un encabezado de venta con una línea de detalle."""
    venta_form   = VentaForm(request.POST or None)
    detalle_form = DetalleVentaForm(request.POST or None)

    if request.method == 'POST':
        if venta_form.is_valid() and detalle_form.is_valid():
            venta         = venta_form.save()
            detalle       = detalle_form.save(commit=False)
            detalle.venta = venta
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


# ── W09: eliminar venta ────────────────────────────────────────────────────
class VentaDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model               = Venta
    template_name       = 'ventas/eliminar.html'
    pk_url_kwarg        = 'venta_id'
    success_url         = reverse_lazy('ventas:lista')
    permission_required = 'ventas.delete_venta'
    raise_exception     = True

    def form_valid(self, form):
        pk       = self.object.pk
        response = super().form_valid(form)
        messages.success(self.request, f'Venta #{pk} eliminada.')
        return response


# ── W12: factura en PDF ────────────────────────────────────────────────────
@login_required
def venta_pdf(request, venta_id: int):
    """Genera y descarga la factura de una venta en formato PDF."""
    venta = get_object_or_404(
        Venta.objects
        .select_related('cliente')
        .prefetch_related('detalles__producto'),
        pk=venta_id
    )
    config = ConfiguracionERP.get_instance()

    html_string = render_to_string('ventas/factura_pdf.html', {
        'venta':  venta,
        'config': config,
    })
    buffer = io.BytesIO()

    pisa_status = pisa.CreatePDF(html_string, dest=buffer)
    if pisa_status.err:
        return HttpResponse('Error al generar el PDF de la factura', status=500)

    buffer.seek(0)
    response = HttpResponse(buffer.read(), content_type='application/pdf')
    response['Content-Disposition'] = (
        f'attachment; filename="factura_{venta.pk:05d}.pdf"'
    )
    return response