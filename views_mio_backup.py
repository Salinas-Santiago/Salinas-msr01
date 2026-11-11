# catalogo/views.py  —  W13 + W14 completo
from decimal import Decimal

import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.views.generic import ListView

from productos.models import Producto
from ventas.models import Pedido
from .checkout_utils import (
    armar_items,
    calcular_totales,
    generar_numero_pedido,
    obtener_o_crear_cliente,
)

# Clave secreta de Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


# ═══════════════════════════════════════════════════════════════════
# W13: helpers del carrito (guardado en la sesión)
# Estructura: {str(pk): {'nombre': str, 'precio': str, 'cantidad': int}}
# ═══════════════════════════════════════════════════════════════════
def _obtener_carrito(request) -> dict:
    return request.session.get('carrito', {})


def _guardar_carrito(request, carrito: dict) -> None:
    request.session['carrito'] = carrito
    request.session.modified = True


def _leer_cantidad(request, defecto: int = 1) -> int:
    try:
        return max(int(request.POST.get('cantidad', defecto)), 0)
    except (TypeError, ValueError):
        return defecto


# ═══════════════════════════════════════════════════════════════════
# W13: catálogo y carrito
# ═══════════════════════════════════════════════════════════════════
class CatalogoView(ListView):
    model               = Producto
    template_name       = 'catalogo/catalogo.html'
    context_object_name = 'productos'


def ver_carrito(request):
    carrito = _obtener_carrito(request)
    return render(request, 'catalogo/carrito.html', {
        'carrito': carrito,
        'items':   armar_items(carrito),
        'totales': calcular_totales(carrito) if carrito else None,
    })


@require_POST
def agregar_al_carrito(request, producto_id: int):
    producto = get_object_or_404(Producto, pk=producto_id)
    cantidad = _leer_cantidad(request, 1) or 1
    carrito  = _obtener_carrito(request)
    clave    = str(producto.pk)

    actual = carrito.get(clave, {}).get('cantidad', 0)
    nueva  = min(actual + cantidad, producto.stock)   # no pasar del stock

    if nueva <= 0:
        messages.warning(request, f'"{producto.nombre}" no tiene stock.')
        return redirect('catalogo:catalogo')

    carrito[clave] = {
        'nombre':   producto.nombre,
        'precio':   str(producto.precio),
        'cantidad': nueva,
    }
    _guardar_carrito(request, carrito)
    messages.success(request, f'"{producto.nombre}" agregado al carrito.')
    return redirect('catalogo:carrito')


@require_POST
def remover_del_carrito(request, producto_id: int):
    carrito = _obtener_carrito(request)
    carrito.pop(str(producto_id), None)
    _guardar_carrito(request, carrito)
    return redirect('catalogo:carrito')


@require_POST
def actualizar_cantidad(request, producto_id: int):
    producto = get_object_or_404(Producto, pk=producto_id)
    cantidad = _leer_cantidad(request, 1)
    carrito  = _obtener_carrito(request)
    clave    = str(producto_id)

    if clave in carrito:
        if cantidad <= 0:
            carrito.pop(clave)
        else:
            carrito[clave]['cantidad'] = min(cantidad, producto.stock)
        _guardar_carrito(request, carrito)
    return redirect('catalogo:carrito')


@require_POST
def vaciar_carrito(request):
    _guardar_carrito(request, {})
    messages.info(request, 'Carrito vaciado.')
    return redirect('catalogo:carrito')


# ═══════════════════════════════════════════════════════════════════
# W14: checkout con Stripe
# ═══════════════════════════════════════════════════════════════════
@login_required
def checkout(request):
    """GET: resumen con IVA. POST: crea Pedido + PaymentIntent."""
    carrito = _obtener_carrito(request)
    if not carrito:
        messages.warning(request, 'Tu carrito está vacío.')
        return redirect('catalogo:catalogo')

    totales         = calcular_totales(carrito)
    items           = armar_items(carrito)
    publishable_key = settings.STRIPE_PUBLISHABLE_KEY

    if request.method == 'POST':
        try:
            # 1. Cliente del ERP
            cliente = obtener_o_crear_cliente(request.user)

            # 2. Pedido pendiente
            pedido = Pedido.objects.create(
                numero_pedido = generar_numero_pedido(),
                cliente       = cliente,
                estado        = 'pendiente',
                total_pagado  = totales['total'],
            )

            # 3. PaymentIntent (monto en centavos)
            intent = stripe.PaymentIntent.create(
                amount          = int(totales['total'] * 100),
                currency        = 'mxn',
                metadata        = {
                    'pedido_id':  pedido.pk,
                    'pedido_num': pedido.numero_pedido,
                    'cliente':    cliente.nombre,
                },
                idempotency_key = f'pedido-{pedido.pk}',
            )

            # 4. client_secret al template
            return render(request, 'catalogo/checkout.html', {
                'carrito':         carrito,
                'items':           items,
                'totales':         totales,
                'pedido':          pedido,
                'client_secret':   intent.client_secret,
                'publishable_key': publishable_key,
            })

        except stripe.StripeError as exc:   # stripe 16.x
            messages.error(
                request,
                f'Error al conectar con Stripe: {exc.user_message or exc}'
            )
            return redirect('catalogo:pago_error')

        except Exception as exc:
            messages.error(
                request,
                f'Error inesperado en el proceso de pago: {exc}'
            )
            return redirect('catalogo:pago_error')

    # GET: solo resumen
    return render(request, 'catalogo/checkout.html', {
        'carrito':         carrito,
        'items':           items,
        'totales':         totales,
        'client_secret':   None,
        'publishable_key': publishable_key,
    })


def pago_exitoso(request, pedido_id: int):
    """Confirmación: vacía el carrito y muestra el pedido."""
    pedido = get_object_or_404(Pedido, pk=pedido_id)

    _guardar_carrito(request, {})
    messages.success(
        request,
        f'¡Pago exitoso! Tu pedido {pedido.numero_pedido} '
        f'está confirmado. Total: ${pedido.total_pagado}'
    )
    return render(request, 'catalogo/pago_exitoso.html', {'pedido': pedido})


def pago_error(request):
    """Error de pago: permite reintentar."""
    return render(request, 'catalogo/pago_error.html')