# ventas/tasks.py
"""Tareas asíncronas para la app ventas con envío real de correo e idempotencia."""
import logging
from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name='ventas.enviar_confirmacion_pedido'
)
def enviar_confirmacion_pedido(self, pedido_id: int) -> dict:
    """Envía el correo de confirmación de pedido garantizando idempotencia."""
    from configuracion.models import ConfiguracionERP
    from ventas.models import Pedido

    try:
        pedido = Pedido.objects.select_related('cliente').get(pk=pedido_id)
    except Pedido.DoesNotExist:
        logger.error(f"[correo_confirmacion] Pedido {pedido_id} no encontrado.")
        return {'estado': 'error', 'razon': 'Pedido no encontrado'}

    # ── CONTROL DE IDEMPOTENCIA ──────────────────────────────────────────
    if pedido.correo_enviado:
        logger.info(f"[correo_confirmacion] Pedido {pedido.numero_pedido}: correo ya enviado previamente. Omitiendo.")
        return {'estado': 'skip', 'pedido_id': pedido_id, 'razon': 'Correo ya enviado'}

    config = ConfiguracionERP.get_instance()
    contexto = {
        'pedido': pedido,
        'config': config,
        'items': pedido.items_snapshot or [],
    }

    asunto = f"Confirmación de pedido {pedido.numero_pedido} — {config.nombre_empresa}"
    texto_plano = render_to_string('emails/confirmacion_pedido.txt', contexto)
    html_body = render_to_string('emails/confirmacion_pedido.html', contexto)

    correo = EmailMultiAlternatives(
        subject=asunto,
        body=texto_plano,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[pedido.cliente.correo]
    )
    correo.attach_alternative(html_body, 'text/html')

    try:
        correo.send()
        logger.info(f"[correo_confirmacion] Correo enviado a {pedido.cliente.correo} para pedido {pedido.numero_pedido}.")
        pedido.correo_enviado = True
        pedido.save(update_fields=['correo_enviado'])
        return {'estado': 'ok', 'pedido_id': pedido_id, 'correo': pedido.cliente.correo}
    except Exception as exc:
        logger.error(f"[correo_confirmacion] Error en el envío: {exc}")
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=1,
    name='ventas.verificar_stock_bajo'
)
def verificar_stock_bajo(self, umbral: int = 5) -> dict:
    """Verifica el stock de productos y envía alerta al administrador si cae por debajo del umbral."""
    from productos.models import Producto
    from configuracion.models import ConfiguracionERP

    productos_bajos = list(
        Producto.objects.filter(activo=True, stock__lt=umbral).values('pk', 'nombre', 'stock')
    )

    if not productos_bajos:
        logger.info(f"[stock_bajo] Sin productos con stock menor a {umbral}.")
        return {'umbral': umbral, 'total': 0, 'productos_bajos': []}

    if settings.ADMINS:
        config = ConfiguracionERP.get_instance()
        contexto = {
            'productos_bajos': productos_bajos,
            'total_productos': len(productos_bajos),
            'umbral': umbral,
            'config': config,
        }

        asunto = f"[ALERTA] {len(productos_bajos)} productos con stock bajo"
        texto_plano = render_to_string('emails/alerta_stock.txt', contexto)
        html_body = render_to_string('emails/alerta_stock.html', contexto)

        _, admin_email = settings.ADMINS[0]
        correo = EmailMultiAlternatives(
            subject=asunto,
            body=texto_plano,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[admin_email]
        )
        correo.attach_alternative(html_body, 'text/html')
        try:
            correo.send()
            logger.info(f"[stock_bajo] Alerta enviada a {admin_email}.")
        except Exception as exc:
            logger.error(f"[stock_bajo] Error enviando alerta: {exc}")

    return {'umbral': umbral, 'total': len(productos_bajos), 'productos_bajos': productos_bajos}
