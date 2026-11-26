
# ventas/tasks.py
"""Tareas asíncronas de ventas: W16, W17 y W18."""

import logging
from decimal import Decimal
from datetime import timedelta
from django.template.loader import render_to_string
from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail, EmailMultiAlternatives
from django.db.models import Sum
from django.utils import timezone

logger = logging.getLogger(__name__)


# ============================================================
# W16 + W17: CONFIRMACION DE PEDIDO
# ============================================================

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="ventas.enviar_confirmacion_pedido",
)
def enviar_confirmacion_pedido(self, pedido_id: int) -> dict:
    from ventas.models import Pedido

    try:
        pedido = Pedido.objects.select_related("cliente").get(pk=pedido_id)

        # No enviar confirmaciones de pedidos que no estén pagados.
        if pedido.estado != "pagado":
            logger.warning(
                "[Celery] Pedido %s no está pagado. Estado: %s",
                pedido.numero_pedido,
                pedido.estado,
            )
            return {
                "estado": "skip",
                "razon": "Pedido no pagado",
                "pedido_id": pedido_id,
            }

        # Evitar correos repetidos cuando ya se confirmó el envío.
        if pedido.correo_enviado:
            logger.info(
                "[Celery] Pedido %s ya tiene correo enviado.",
                pedido.numero_pedido,
            )
            return {"estado": "skip", "pedido_id": pedido_id}

        snapshot = pedido.items_snapshot or []
        subtotal = Decimal("0.00")

        for item in snapshot:
            precio = Decimal(str(item.get("precio", 0)))
            cantidad = int(item.get("cantidad", 0))
            subtotal += precio * cantidad

        total = Decimal(str(pedido.total_pagado or 0))

        asunto = f"Confirmación de Pedido {pedido.numero_pedido}"

        mensaje = (
            f"Hola {pedido.cliente.nombre},\n\n"
            f"Tu pedido {pedido.numero_pedido} ha sido procesado.\n"
            f"Subtotal: ${subtotal:.2f}\n"
            f"Total pagado: ${total:.2f}\n\n"
            "Gracias por tu compra."
        )

        html = f"""
        <!DOCTYPE html>
        <html lang="es">
        <body>
            <h2>Confirmación de pedido</h2>
            <p>Hola {pedido.cliente.nombre}, tu pedido
               <strong>{pedido.numero_pedido}</strong> ha sido procesado.</p>
            <p>Subtotal: <strong>${subtotal:.2f}</strong></p>
            <p>Total pagado: <strong>${total:.2f}</strong></p>
            <p>Gracias por tu compra.</p>
        </body>
        </html>
        """

        correo = EmailMultiAlternatives(
            subject=asunto,
            body=mensaje,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[pedido.cliente.correo],
        )

        correo.attach_alternative(html, "text/html")

        # Comprobar que el backend haya aceptado al menos un envío.
        enviados = correo.send(fail_silently=False)

        if enviados != 1:
            raise RuntimeError(
                f"El backend no confirmó el envío del pedido "
                f"{pedido.numero_pedido}. Resultado: {enviados}"
            )

        pedido.correo_enviado = True
        pedido.save(update_fields=["correo_enviado"])

        logger.info(
            "[Celery] Confirmación aceptada por el backend para pedido %s",
            pedido.numero_pedido,
        )

        return {"estado": "ok", "pedido_id": pedido_id}

    except Pedido.DoesNotExist:
        logger.error("[Celery] Pedido %s no existe.", pedido_id)
        return {"estado": "error", "razon": "Pedido no encontrado"}

    except Exception as exc:
        logger.exception(
            "[Celery] Error enviando confirmación del pedido %s",
            pedido_id,
        )
        raise self.retry(exc=exc)



# ============================================================
# W16 + W17: VERIFICACION Y ALERTA DE STOCK
# ============================================================

def _productos_stock_bajo(umbral=5):
    from productos.models import Producto

    return list(
        Producto.objects.filter(
            activo=True,
            stock__lt=umbral,
        ).values("id", "nombre", "stock")
    )


def _obtener_destinatarios_stock():
    """
    Obtiene los destinatarios de alertas de inventario.

    Orden de prioridad:
    1. ALERTA_STOCK_DESTINATARIOS
    2. ADMIN_EMAIL
    3. ADMINS
    """

    destinatarios = getattr(
        settings,
        "ALERTA_STOCK_DESTINATARIOS",
        [],
    ) or []

    if destinatarios:
        return destinatarios

    admin_email = getattr(settings, "ADMIN_EMAIL", "")

    if admin_email:
        return [admin_email]

    admins = getattr(settings, "ADMINS", []) or []

    return [
        email
        for _, email in admins
        if email
    ]


def _enviar_alerta_stock(productos):
    destinatarios = _obtener_destinatarios_stock()

    if not productos or not destinatarios:
        logger.warning(
            "[Celery] No se envió alerta de stock: "
            "sin productos o destinatarios."
        )
        return 0

    lineas = [
        f"- {p['nombre']}: {p['stock']} unidades"
        for p in productos
    ]

    mensaje = (
        "Se detectaron productos con stock bajo:\n\n"
        + "\n".join(lineas)
    )

    asunto = "Alerta de inventario bajo"

    enviados = send_mail(
        asunto,
        mensaje,
        settings.DEFAULT_FROM_EMAIL,
        destinatarios,
        fail_silently=False,
    )

    logger.info(
        "[Celery] Alerta de stock enviada. Correos enviados: %s",
        enviados,
    )

    return enviados


@shared_task(
    bind=True,
    name="ventas.verificar_stock_bajo",
)
def verificar_stock_bajo(self, umbral: int = 5) -> dict:
    productos = _productos_stock_bajo(umbral)

    logger.info(
        "[Celery] Se encontraron %s productos bajo el umbral %s.",
        len(productos),
        umbral,
    )

    enviados = 0

    if productos:
        enviados = _enviar_alerta_stock(productos)

    return {
        "umbral": umbral,
        "total": len(productos),
        "productos": productos,
        "correos_enviados": enviados,
    }


# ============================================================
# TAREA EXTERNA: ALERTA DESPUES DE VENTA (6 HORAS)
# ============================================================

def alertar_stock_tras_venta():
    productos = _productos_stock_bajo(5)

    if not productos:
        return {
            "estado": "sin_stock_bajo",
            "total": 0,
        }

    clave = "erp_alerta_stock_tras_venta"

    # Enfriamiento de seis horas para evitar correos repetidos
    if cache.get(clave):
        logger.info(
            "[Celery] Alerta de stock dentro del enfriamiento."
        )
        return {
            "estado": "skip",
            "razon": "enfriamiento",
            "total": len(productos),
        }

    enviados = _enviar_alerta_stock(productos)

    if enviados:
        cache.set(clave, True, timeout=6 * 60 * 60)

    return {
        "estado": "ok" if enviados else "sin_destinatarios",
        "total": len(productos),
    }


# ============================================================
# W18: REPORTE DIARIO DE VENTAS
# ============================================================

# ventas/tasks.py — Añadir al final del archivo

@shared_task(
    bind=True,
    max_retries=2,
    name='ventas.reporte_ventas_diario'
)
def reporte_ventas_diario(self) -> dict:
    """Calcula métricas diarias mediante SQL y envía un reporte por correo al administrador."""
    from decimal import Decimal
    from django.db.models import DecimalField, ExpressionWrapper, F, Sum
    from django.utils import timezone
    from configuracion.models import ConfiguracionERP
    from ventas.models import DetalleVenta, Pedido

    hoy = timezone.localdate()
    config = ConfiguracionERP.get_instance()

    pedidos_hoy = Pedido.objects.filter(fecha_pedido__date=hoy, estado='pagado')
    total_pedidos = pedidos_hoy.count()
    total_facturado = pedidos_hoy.aggregate(total=Sum('total_pagado'))['total'] or Decimal('0.00')

    top_productos = list(
        DetalleVenta.objects.filter(venta__fecha__date=hoy)
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

    if settings.ADMINS:
        contexto = {
            'fecha': hoy.strftime('%d/%m/%Y'),
            'config': config,
            'total_pedidos': total_pedidos,
            'total_facturado': total_facturado,
            'top_productos': top_productos,
        }

        asunto = f"Reporte de Ventas {hoy.strftime('%d/%m/%Y')} — {config.nombre_empresa}"
        texto_plano = render_to_string('emails/reporte_ventas.txt', contexto)
        html_body = render_to_string('emails/reporte_ventas.html', contexto)

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
            logger.info(f"[reporte_diario] Reporte enviado a {admin_email}.")
        except Exception as exc:
            logger.error(f"[reporte_diario] Error enviando reporte: {exc}")

    return {
        'fecha': str(hoy),
        'total_pedidos': total_pedidos,
        'total_facturado': str(total_facturado),
        'top_productos': top_productos,
    }


@shared_task(name="ventas.probar_sendgrid")
def probar_sendgrid(destinatario: str) -> dict:
    """
    Comprueba el envío de correo mediante Celery y SendGrid.
    No modifica pedidos ni inventario.
    """
    try:
        resultado = send_mail(
            subject="Prueba Celery + SendGrid - ERP Django",
            message=(
                "El servicio de correo del ERP funciona correctamente.\n\n"
                "Este mensaje fue enviado mediante una tarea de Celery."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[destinatario],
            fail_silently=False,
        )

        logger.info(
            "[Celery] Prueba SendGrid enviada a %s. Resultado: %s",
            destinatario,
            resultado,
        )

        return {
            "estado": "ok" if resultado == 1 else "sin_envio",
            "resultado": resultado,
        }

    except Exception:
        logger.exception("[Celery] Error en la prueba de SendGrid.")
        raise
