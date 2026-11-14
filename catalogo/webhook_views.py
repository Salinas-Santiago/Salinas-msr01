# catalogo/webhook_views.py
"""Endpoint de webhook para recibir eventos de Stripe — W15.

Verificación de seguridad:
    Stripe firma cada evento con STRIPE_WEBHOOK_SECRET.
    stripe.Webhook.construct_event() verifica la firma.
    Si la firma es inválida → 400 (Stripe no reintenta).
    Si la firma es válida → procesar el evento → 200.

Eventos manejados:
    payment_intent.succeeded     → Pedido.estado = 'pagado'
                                    Descontar stock de productos
    payment_intent.payment_failed → Pedido.estado = 'cancelado'

Compatibilidad:
    En stripe-python >= 13 los objetos del evento (PaymentIntent, etc.)
    ya NO son diccionarios y no tienen .get(). Por eso se convierten a
    dict con _a_dict() antes de pasarlos a los handlers. La función
    también acepta dicts normales, así que los tests con mocks siguen
    funcionando.
"""
import logging

import stripe
from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from productos.models import Producto
from ventas.models    import Pedido

logger = logging.getLogger(__name__)


def _a_dict(obj) -> dict:
    """Convierte un objeto de Stripe a dict (o devuelve el dict tal cual)."""
    if hasattr(obj, 'to_dict'):
        return obj.to_dict()
    return obj


@csrf_exempt
@require_POST
def stripe_webhook(request) -> HttpResponse:
    """Recibe y procesa eventos de Stripe.

    Returns:
        HttpResponse: 200 si el evento fue procesado correctamente,
                      400 si la firma es inválida o el payload es inválido.
    """
    payload    = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')

    # ── 1. Verificar firma ─────────────────────────────────────────────────
    try:
        event = stripe.Webhook.construct_event(
            payload    = payload,
            sig_header = sig_header,
            secret     = settings.STRIPE_WEBHOOK_SECRET,
        )
    except ValueError:
        logger.warning('Webhook: payload inválido recibido.')
        return HttpResponse('Payload inválido.', status=400)
    except stripe.error.SignatureVerificationError:
        logger.warning('Webhook: firma inválida — posible ataque.')
        return HttpResponse('Firma inválida.', status=400)

    # ── 2. Despachar por tipo de evento ────────────────────────────────────
    tipo = event['type']
    logger.info(f'Webhook recibido: {tipo}')

    objeto = _a_dict(event['data']['object'])

    if tipo == 'payment_intent.succeeded':
        _manejar_pago_exitoso(objeto)

    elif tipo == 'payment_intent.payment_failed':
        _manejar_pago_fallido(objeto)

    else:
        logger.debug(f'Evento ignorado: {tipo}')

    return HttpResponse(status=200)


# ── HANDLERS INTERNOS ──────────────────────────────────────────────────────

def _manejar_pago_exitoso(payment_intent: dict) -> None:
    """Marca el Pedido como 'pagado' y descuenta el stock.

    Todo ocurre en una transacción: si falla el descuento de stock,
    el pedido NO queda marcado como pagado y Stripe reintentará.
    """
    pedido_id = _extraer_pedido_id(payment_intent)
    if pedido_id is None:
        return

    try:
        with transaction.atomic():
            try:
                pedido = Pedido.objects.select_for_update().get(pk=pedido_id)
            except Pedido.DoesNotExist:
                logger.error(
                    f'Webhook: Pedido {pedido_id} no encontrado en BD.'
                )
                return

            if pedido.estado != 'pagado':
                pedido.estado = 'pagado'
                pedido.save(update_fields=['estado'])
                logger.info(
                    f'Pedido {pedido.numero_pedido} actualizado a "pagado".'
                )
                _descontar_stock(pedido)
            else:
                logger.info(
                    f'Pedido {pedido.numero_pedido} ya estaba pagado — '
                    f'idempotente, sin cambios.'
                )
    except Exception:
        logger.exception(
            f'Webhook: error procesando pago del pedido {pedido_id}.'
        )
        raise


def _manejar_pago_fallido(payment_intent: dict) -> None:
    """Marca el Pedido como 'cancelado' si seguía pendiente."""
    pedido_id = _extraer_pedido_id(payment_intent)
    if pedido_id is None:
        return

    try:
        pedido = Pedido.objects.get(pk=pedido_id)
    except Pedido.DoesNotExist:
        logger.error(f'Webhook: Pedido {pedido_id} no encontrado.')
        return

    if pedido.estado == 'pendiente':
        pedido.estado = 'cancelado'
        pedido.save(update_fields=['estado'])
        logger.info(
            f'Pedido {pedido.numero_pedido} cancelado por pago fallido.'
        )


def _extraer_pedido_id(payment_intent: dict) -> int | None:
    """Extrae el pedido_id del metadata del PaymentIntent."""
    metadata  = payment_intent.get('metadata') or {}
    pedido_id = metadata.get('pedido_id')

    if not pedido_id:
        logger.warning(
            f'Webhook: PaymentIntent sin pedido_id en metadata. '
            f'ID de PaymentIntent: {payment_intent.get("id")}'
        )
        return None

    try:
        return int(pedido_id)
    except (ValueError, TypeError):
        logger.error(f'Webhook: pedido_id inválido: {pedido_id!r}')
        return None


def _descontar_stock(pedido: 'Pedido') -> None:
    """Descuenta el stock de los productos del pedido con F() (atómico)."""
    items = pedido.items_snapshot or []

    if not items:
        logger.warning(
            f'Pedido {pedido.numero_pedido}: items_snapshot vacío, '
            f'no hay stock que descontar.'
        )

    for item in items:
        producto_id = item.get('producto_id')
        cantidad    = int(item.get('cantidad', 0))

        if not producto_id or cantidad <= 0:
            logger.warning(
                f'Pedido {pedido.numero_pedido}: item inválido en '
                f'snapshot: {item!r}'
            )
            continue

        filas_actualizadas = Producto.objects.filter(
            pk=producto_id,
            stock__gte=cantidad    # solo si hay stock suficiente
        ).update(
            stock=F('stock') - cantidad
        )

        if filas_actualizadas:
            logger.info(
                f'Stock decrementado: Producto {producto_id} '
                f'- {cantidad} unidades.'
            )
        else:
            logger.warning(
                f'Producto {producto_id}: stock insuficiente para '
                f'decrementar {cantidad} unidades.'
            )