# ventas/tasks.py
"""Tareas asíncronas de la app ventas — W17.

W17 implementa el envío real de correos:
    - Confirmación de pago al cliente.
    - Alerta de stock bajo al administrador.

Idempotencia:
    Pedido.correo_enviado se "reclama" de forma atómica antes de enviar,
    así dos ejecuciones simultáneas nunca mandan dos correos.
"""
import logging
from decimal import Decimal, InvalidOperation

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger(__name__)


def _preparar_items(items_snapshot) -> list:
    """Normaliza items_snapshot y calcula el subtotal de cada producto."""
    items = []
    for it in items_snapshot or []:
        try:
            precio   = Decimal(str(it.get('precio', '0')))
            cantidad = int(it.get('cantidad', 0))
        except (InvalidOperation, ValueError, TypeError):
            precio, cantidad = Decimal('0'), 0
        items.append({
            'nombre':   it.get('nombre', ''),
            'precio':   precio,
            'cantidad': cantidad,
            'subtotal': precio * cantidad,
        })
    return items


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name='ventas.enviar_confirmacion_pedido',
)
def enviar_confirmacion_pedido(self, pedido_id: int) -> dict:
    """Envía el correo de confirmación de pago al cliente.

    Garantías:
        - Idempotente: si ya se envió (o se está enviando), no manda otro.
        - Reintento automático hasta 3 veces si el servicio de correo falla.

    Args:
        pedido_id: ID del Pedido confirmado.

    Returns:
        dict con estado, pedido_id y correo del destinatario.
    """
    from configuracion.models import ConfiguracionERP  # import local
    from ventas.models        import Pedido             # import local

    try:
        pedido = Pedido.objects.select_related('cliente').get(pk=pedido_id)
    except Pedido.DoesNotExist:
        logger.error(f'[correo_confirmacion] Pedido {pedido_id} no existe.')
        return {'estado': 'error', 'razon': 'Pedido no encontrado'}

    # ── Verificación rápida de idempotencia ─────────────────────────────
    if pedido.correo_enviado:
        logger.info(
            f'[correo_confirmacion] Pedido {pedido.numero_pedido}: '
            f'correo ya enviado anteriormente — skip.'
        )
        return {
            'estado':    'skip',
            'pedido_id': pedido_id,
            'razon':     'correo ya enviado',
        }

    correo_destino = pedido.cliente.correo
    if not correo_destino:
        logger.error(
            f'[correo_confirmacion] El cliente del pedido '
            f'{pedido.numero_pedido} no tiene correo.'
        )
        return {'estado': 'error', 'razon': 'Cliente sin correo'}

    # ── Reclamar el pedido de forma atómica ─────────────────────────────
    # Solo UNA ejecución consigue cambiar False → True.
    reclamado = (
        Pedido.objects
        .filter(pk=pedido_id, correo_enviado=False)
        .update(correo_enviado=True)
    )
    if not reclamado:
        return {
            'estado':    'skip',
            'pedido_id': pedido_id,
            'razon':     'otra ejecución ya lo está enviando',
        }

    try:
        config = ConfiguracionERP.get_instance()

        contexto = {
            'pedido':     pedido,
            'config':     config,
            'items':      _preparar_items(pedido.items_snapshot),
            'url_pedido': f'{settings.SITE_URL}/ventas/{pedido.pk}/',
        }

        # render_to_string sin request (las tareas Celery no tienen request)
        asunto = (
            f'Confirmación de pedido {pedido.numero_pedido} '
            f'— {config.nombre_empresa}'
        )
        texto_plano = render_to_string('emails/confirmacion_pedido.txt', contexto)
        html_body   = render_to_string('emails/confirmacion_pedido.html', contexto)

        mensaje = EmailMultiAlternatives(
            subject    = asunto,
            body       = texto_plano,          # versión texto plano (fallback)
            from_email = settings.DEFAULT_FROM_EMAIL,
            to         = [correo_destino],
        )
        mensaje.attach_alternative(html_body, 'text/html')
        mensaje.send()

    except Exception as exc:
        # Liberar la marca para que el reintento pueda volver a enviarlo
        Pedido.objects.filter(pk=pedido_id).update(correo_enviado=False)
        logger.error(
            f'[correo_confirmacion] Error al enviar correo para pedido '
            f'{pedido.numero_pedido}: {exc}'
        )
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))

    logger.info(
        f'[correo_confirmacion] Correo enviado a {correo_destino} '
        f'para pedido {pedido.numero_pedido}.'
    )
    return {
        'estado':    'ok',
        'pedido_id': pedido_id,
        'correo':    correo_destino,
    }


@shared_task(
    bind=True,
    max_retries=1,
    name='ventas.verificar_stock_bajo',
)
def verificar_stock_bajo(self, umbral: int = 5) -> dict:
    """Verifica productos con stock bajo y envía alerta al administrador.

    Args:
        umbral: cantidad mínima antes de alertar (default: 5).

    Returns:
        dict con umbral, total, productos_bajos y si se envió la alerta.
    """
    from productos.models import Producto   # import local

    productos_bajos = list(
        Producto.objects
        .filter(activo=True, stock__lt=umbral)
        .values('pk', 'nombre', 'stock', 'categoria__nombre')
        .order_by('stock')
    )

    if not productos_bajos:
        logger.info(
            f'[stock_bajo] Todos los productos tienen stock ≥ {umbral}. OK.'
        )
        return {
            'umbral': umbral, 'total': 0,
            'productos_bajos': [], 'alerta_enviada': False,
        }

    logger.warning(
        f'[stock_bajo] {len(productos_bajos)} producto(s) con stock < {umbral}.'
    )

    alerta_enviada = False
    if settings.ALERTA_STOCK_DESTINATARIOS:
        alerta_enviada = _enviar_alerta_stock(productos_bajos, umbral)

    return {
        'umbral':          umbral,
        'total':           len(productos_bajos),
        'productos_bajos': productos_bajos,
        'alerta_enviada':  alerta_enviada,
    }


def _enviar_alerta_stock(productos_bajos: list, umbral: int) -> bool:
    """Envía el correo de alerta de stock bajo a los destinatarios.

    Args:
        productos_bajos: lista de dicts con nombre, stock y categoría.
        umbral:          umbral mínimo configurado.

    Returns:
        True si el correo se envió, False si falló (el error se registra).
    """
    from configuracion.models import ConfiguracionERP   # import local

    config = ConfiguracionERP.get_instance()

    contexto = {
        'productos_bajos': productos_bajos,
        'total_productos': len(productos_bajos),
        'umbral':          umbral,
        'fecha':           timezone.localtime().strftime('%d/%m/%Y %H:%M'),
        'url_admin':       f'{settings.SITE_URL}/admin/productos/producto/',
        'config':          config,
    }

    asunto = f'[ALERTA] {len(productos_bajos)} producto(s) con stock < {umbral}'
    texto_plano = render_to_string('emails/alerta_stock.txt',  contexto)
    html_body   = render_to_string('emails/alerta_stock.html', contexto)

    mensaje = EmailMultiAlternatives(
        subject    = asunto,
        body       = texto_plano,
        from_email = settings.DEFAULT_FROM_EMAIL,
        to         = list(settings.ALERTA_STOCK_DESTINATARIOS),
    )
    mensaje.attach_alternative(html_body, 'text/html')

    try:
        mensaje.send()
    except Exception as exc:
        logger.error(f'[stock_bajo] Error al enviar alerta: {exc}')
        return False

    logger.info(
        f'[stock_bajo] Alerta enviada a {settings.ALERTA_STOCK_DESTINATARIOS}. '
        f'{len(productos_bajos)} productos.'
    )
    return True
