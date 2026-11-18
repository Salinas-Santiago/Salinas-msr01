# ventas/tasks.py
"""Tareas asíncronas de la app ventas — W16.

W16: placeholders que solo registran en el log.
W17: envío real de correo con SendGrid.
W18: tareas programadas con Celery Beat.
"""
import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name='ventas.enviar_confirmacion_pedido',
)
def enviar_confirmacion_pedido(self, pedido_id: int) -> dict:
    """Envía el correo de confirmación de pedido al cliente (placeholder)."""
    from ventas.models import Pedido   # import local evita circularidad

    try:
        pedido = Pedido.objects.select_related('cliente').get(pk=pedido_id)
    except Pedido.DoesNotExist:
        logger.error(
            f'[Tarea enviar_confirmacion] Pedido {pedido_id} no existe.'
        )
        return {'estado': 'error', 'pedido_id': pedido_id}

    logger.info(
        f'[Tarea enviar_confirmacion] Procesando pedido '
        f'{pedido.numero_pedido} para {pedido.cliente.correo}. '
        f'Total: ${pedido.total_pagado}. '
        f'Timestamp: {timezone.now().isoformat()}'
    )

    return {
        'estado':    'ok',
        'pedido_id': pedido_id,
        'numero':    pedido.numero_pedido,
        'cliente':   pedido.cliente.correo,
    }


@shared_task(
    bind=True,
    max_retries=1,
    name='ventas.verificar_stock_bajo',
)
def verificar_stock_bajo(self, umbral: int = 5) -> dict:
    """Detecta productos con stock por debajo del umbral (placeholder)."""
    from productos.models import Producto   # import local

    productos_bajos = list(
        Producto.objects
        .filter(activo=True, stock__lt=umbral)
        .values('pk', 'nombre', 'stock')
        .order_by('stock')
    )

    if productos_bajos:
        logger.warning(
            f'[Tarea verificar_stock] {len(productos_bajos)} producto(s) '
            f'con stock < {umbral}: '
            f'{[p["nombre"] for p in productos_bajos]}'
        )
    else:
        logger.info(
            f'[Tarea verificar_stock] Todos los productos tienen '
            f'stock >= {umbral}. OK.'
        )

    return {
        'umbral':          umbral,
        'productos_bajos': productos_bajos,
        'total':           len(productos_bajos),
    }
