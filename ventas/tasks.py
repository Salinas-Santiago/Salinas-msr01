
# ventas/tasks.py
"""Tareas asíncronas de ventas: W16, W17 y W18."""

import logging
from decimal import Decimal
from datetime import timedelta

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

        # Evitar correos duplicados
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
        correo.send(fail_silently=False)

        pedido.correo_enviado = True
        pedido.save(update_fields=["correo_enviado"])

        logger.info(
            "[Celery] Confirmación enviada para pedido %s",
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

@shared_task(
    bind=True,
    name="ventas.reporte_ventas_diario",
)
def reporte_ventas_diario(self, dias_atras=0):
    from ventas.models import Pedido, Venta, DetalleVenta

    fecha = timezone.localdate() - timedelta(days=dias_atras)

    # Pedidos pagados del día
    pedidos = Pedido.objects.filter(estado="pagado")

    campos_pedido = {f.name for f in Pedido._meta.get_fields()}

    campo_fecha_pedido = next(
        (
            nombre
            for nombre in (
                "fecha",
                "fecha_creacion",
                "created_at",
                "fecha_pedido",
            )
            if nombre in campos_pedido
        ),
        None,
    )

    if campo_fecha_pedido:
        campo = getattr(Pedido, campo_fecha_pedido).field

        if campo.get_internal_type() == "DateTimeField":
            pedidos = pedidos.filter(
                **{f"{campo_fecha_pedido}__date": fecha}
            )
        else:
            pedidos = pedidos.filter(
                **{campo_fecha_pedido: fecha}
            )

    total_pedidos = pedidos.count()

    total_facturado = pedidos.aggregate(
        total=Sum("total_pagado")
    )["total"] or Decimal("0.00")

    # Ventas del día
    ventas = Venta.objects.all()

    campos_venta = {f.name for f in Venta._meta.get_fields()}

    campo_fecha_venta = next(
        (
            nombre
            for nombre in (
                "fecha",
                "fecha_venta",
                "created_at",
                "fecha_creacion",
            )
            if nombre in campos_venta
        ),
        None,
    )

    if campo_fecha_venta:
        campo = getattr(Venta, campo_fecha_venta).field

        if campo.get_internal_type() == "DateTimeField":
            ventas = ventas.filter(
                **{f"{campo_fecha_venta}__date": fecha}
            )
        else:
            ventas = ventas.filter(
                **{campo_fecha_venta: fecha}
            )

    detalles = DetalleVenta.objects.filter(venta__in=ventas)

    productos_acumulados = {}

    for detalle in detalles.select_related("producto"):
        producto_id = detalle.producto_id
        nombre = detalle.producto.nombre

        if producto_id not in productos_acumulados:
            productos_acumulados[producto_id] = {
                "nombre": nombre,
                "unidades": 0,
            }

        productos_acumulados[producto_id]["unidades"] += detalle.cantidad

    top_productos = sorted(
        productos_acumulados.values(),
        key=lambda item: item["unidades"],
        reverse=True,
    )[:10]

    fecha_str = fecha.strftime("%d/%m/%Y")

    asunto = f"Reporte diario de ventas - {fecha_str}"

    mensaje = (
        f"Reporte de ventas del {fecha_str}\n\n"
        f"Pedidos pagados: {total_pedidos}\n"
        f"Total facturado: ${total_facturado:.2f}\n\n"
        "Productos más vendidos:\n"
    )

    if top_productos:
        for producto in top_productos:
            mensaje += (
                f"- {producto['nombre']}: "
                f"{producto['unidades']} unidades\n"
            )
    else:
        mensaje += "No hubo productos vendidos.\n"

    destinatarios = getattr(
        settings,
        "REPORTE_VENTAS_DESTINATARIOS",
        [],
    )

    if destinatarios:
        send_mail(
            asunto,
            mensaje,
            settings.DEFAULT_FROM_EMAIL,
            destinatarios,
            fail_silently=False,
        )

    logger.info(
        "[Celery] Reporte diario generado para %s",
        fecha_str,
    )

    return {
        "fecha": fecha_str,
        "total_pedidos": total_pedidos,
        "total_facturado": str(total_facturado),
        "top_productos": top_productos,
    }