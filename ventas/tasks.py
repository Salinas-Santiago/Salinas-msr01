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

# ventas/tasks.py — agregar al final del archivo

@shared_task(
    bind=True,
    name='ventas.reporte_ventas_diario',
)
def reporte_ventas_diario(self, dias_atras: int = 1) -> dict:
    """Genera y envía el reporte de ventas de un día al administrador.

    Se programa a las 8:00 AM (CELERY_BEAT_SCHEDULE) y por defecto
    reporta el día ANTERIOR (dias_atras=1), que ya está completo.

    Cálculos realizados en SQL (no en Python):
        - Total de pedidos pagados del día
        - Total facturado (suma de total_pagado)
        - Top 5 productos por ingreso del día

    Args:
        dias_atras: 1 = ayer (default), 0 = hoy.

    Returns:
        dict con fecha, total_pedidos, total_facturado, top_productos
        y correo_enviado.
    """
    from datetime import timedelta

    from django.db.models import (
        DecimalField, ExpressionWrapper, F, Sum,
    )

    from configuracion.models import ConfiguracionERP       # import local
    from ventas.models        import DetalleVenta, Pedido   # import local

    fecha  = timezone.localdate() - timedelta(days=dias_atras)
    config = ConfiguracionERP.get_instance()

    # ── 1. KPIs del día ───────────────────────────────────────────────
    pedidos = Pedido.objects.filter(
        fecha_pedido__date=fecha,
        estado='pagado',
    )
    total_pedidos   = pedidos.count()
    total_facturado = pedidos.aggregate(
        total=Sum('total_pagado')
    )['total'] or Decimal('0.00')

    # ── 2. Top 5 productos por ingreso del día ─────────────────────────
    top_productos = list(
        DetalleVenta.objects
        .filter(venta__fecha__date=fecha)
        .values(nombre=F('producto__nombre'))
        .annotate(
            unidades=Sum('cantidad'),
            ingreso=Sum(
                ExpressionWrapper(
                    F('cantidad') * F('precio_unitario'),
                    output_field=DecimalField(max_digits=12, decimal_places=2)
                )
            )
        )
        .order_by('-ingreso')[:5]
    )

    logger.info(
        f'[reporte_diario] {fecha}: {total_pedidos} pedidos, '
        f'${total_facturado} facturados, '
        f'{len(top_productos)} productos top.'
    )

    # ── 3. Enviar correo si hay destinatarios configurados ─────────────
    correo_enviado = False
    if settings.REPORTE_VENTAS_DESTINATARIOS:
        correo_enviado = _enviar_reporte_ventas(
            fecha, total_pedidos, total_facturado, top_productos, config
        )

    # Resultado serializable (sin Decimal) para Celery
    return {
        'fecha':           str(fecha),
        'total_pedidos':   total_pedidos,
        'total_facturado': str(total_facturado),
        'top_productos': [
            {
                'nombre':   p['nombre'],
                'unidades': p['unidades'],
                'ingreso':  str(p['ingreso']),
            }
            for p in top_productos
        ],
        'correo_enviado':  correo_enviado,
    }


def _enviar_reporte_ventas(
    fecha, total_pedidos, total_facturado, top_productos, config
) -> bool:
    """Envía el reporte de ventas a los destinatarios configurados.

    Args:
        fecha:           Objeto date del día reportado.
        total_pedidos:   Número de pedidos pagados.
        total_facturado: Decimal con la suma total.
        top_productos:   Lista de dicts con nombre, unidades, ingreso.
        config:          Instancia de ConfiguracionERP.

    Returns:
        True si el correo se envió, False si falló (el error se registra).
    """
    fecha_str = fecha.strftime('%d/%m/%Y')

    contexto = {
        'fecha':           fecha_str,
        'config':          config,
        'total_pedidos':   total_pedidos,
        'total_facturado': total_facturado,
        'top_productos':   top_productos,
        'url_admin':       f'{settings.SITE_URL}/admin/',
    }

    asunto      = f'Reporte de ventas del {fecha_str} — {config.nombre_empresa}'
    texto_plano = render_to_string('emails/reporte_ventas.txt',  contexto)
    html_body   = render_to_string('emails/reporte_ventas.html', contexto)

    mensaje = EmailMultiAlternatives(
        subject    = asunto,
        body       = texto_plano,
        from_email = settings.DEFAULT_FROM_EMAIL,
        to         = list(settings.REPORTE_VENTAS_DESTINATARIOS),
    )
    mensaje.attach_alternative(html_body, 'text/html')

    try:
        mensaje.send()
    except Exception as exc:
        logger.error(f'[reporte_diario] Error al enviar reporte: {exc}')
        return False

    logger.info(
        f'[reporte_diario] Reporte enviado a '
        f'{settings.REPORTE_VENTAS_DESTINATARIOS}.'
    )
    return True

def alertar_stock_tras_venta(umbral: int = 5, horas: int = 6) -> bool:
    """Alerta de stock bajo disparada por una venta (Opción A).

    Ejecuta verificar_stock_bajo y, si se envió la alerta, no vuelve a
    enviar otra durante `horas` horas. Nunca rompe el flujo de la venta.

    Returns:
        True si se envió una alerta, False en cualquier otro caso.
    """
    from django.core.cache import cache

    clave = 'alerta_stock_tras_venta'
    if cache.get(clave):
        return False                      # ya se alertó hace poco

    try:
        resultado = verificar_stock_bajo.apply(
            kwargs={'umbral': umbral}
        ).get()
    except Exception as exc:
        logger.error(f'[stock_tras_venta] Error: {exc}')
        return False

    if resultado.get('alerta_enviada'):
        cache.set(clave, True, timeout=horas * 3600)
        return True
    return False

from django.db import transaction
from ventas.tasks import alertar_stock_tras_venta

# ... aquí va tu código que descuenta el stock ...

transaction.on_commit(alertar_stock_tras_venta)