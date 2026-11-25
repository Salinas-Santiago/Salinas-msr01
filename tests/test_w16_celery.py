"""Suite de pruebas W16 — Infraestructura Celery y Tareas Asíncronas."""
from decimal import Decimal
from django.test import TestCase, override_settings
from clientes.models import Cliente
from configuracion.models import ConfiguracionERP
from productos.models import Categoria, Producto
from ventas.models import Pedido
from ventas.tasks import enviar_confirmacion_pedido, verificar_stock_bajo


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'
)
class CeleryTasksTest(TestCase):
    """Pruebas de tareas Celery ejecutadas sincrónicamente con ALWAYS_EAGER."""

    def setUp(self):
        ConfiguracionERP.get_instance()
        self.cat = Categoria.objects.create(nombre='Cat Celery')
        self.prod = Producto.objects.create(
            nombre='Teclado', precio=Decimal('100.00'), stock=2, categoria=self.cat
        )
        self.cli = Cliente.objects.create(
            nombre='Cliente Celery', correo='celery@test.com'
        )
        self.pedido = Pedido.objects.create(
            numero_pedido='PED-CELERY-01',
            cliente=self.cli,
            estado='pagado',
            total_pagado=Decimal('100.00')
        )

    def test_enviar_confirmacion_pedido_task(self):
        """La tarea de confirmación de pedido se ejecuta correctamente."""
        res = enviar_confirmacion_pedido.delay(self.pedido.pk)
        data = res.get()
        self.assertEqual(data['estado'], 'ok')
        self.assertEqual(data['pedido_id'], self.pedido.pk)

    def test_enviar_confirmacion_pedido_inexistente(self):
        """Maneja adecuadamente pedidos inexistentes."""
        res = enviar_confirmacion_pedido.delay(9999)
        data = res.get()
        self.assertEqual(data['estado'], 'error')

    def test_verificar_stock_bajo_task(self):
        """Detecta productos por debajo del umbral especificado."""
        res = verificar_stock_bajo.delay(umbral=5)
        data = res.get()
        self.assertEqual(data['total'], 1)
        self.assertEqual(data['productos'][0]['id'], self.prod.pk)
