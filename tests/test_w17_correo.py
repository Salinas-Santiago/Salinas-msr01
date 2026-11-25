"""Suite de pruebas W17 — Verificación de envíos transaccionales con mail.outbox."""
from decimal import Decimal
from django.core import mail
from django.test import TestCase, override_settings
from clientes.models import Cliente
from configuracion.models import ConfiguracionERP
from productos.models import Categoria, Producto
from ventas.models import Pedido
from ventas.tasks import enviar_confirmacion_pedido, verificar_stock_bajo

EMAIL_SETTINGS = {
    'EMAIL_BACKEND': 'django.core.mail.backends.locmem.EmailBackend',
    'CELERY_TASK_ALWAYS_EAGER': True,
    'CELERY_TASK_EAGER_PROPAGATES': True,
    'ADMINS': [('Admin Test', 'admin@test.com')],
    'DEFAULT_FROM_EMAIL': 'test@erp.com',
}


@override_settings(**EMAIL_SETTINGS)
class CorreoTransaccionalTest(TestCase):
    """Pruebas de envío e idempotencia de correos."""

    def setUp(self):
        mail.outbox = []
        ConfiguracionERP.get_instance()
        self.cat = Categoria.objects.create(nombre='Cat W17')
        self.prod = Producto.objects.create(
            nombre='Teclado W17', precio=Decimal('150.00'), stock=2, categoria=self.cat
        )
        self.cli = Cliente.objects.create(nombre='Cliente W17', correo='w17@test.com')
        self.pedido = Pedido.objects.create(
            numero_pedido='PED-W17-001',
            cliente=self.cli,
            estado='pagado',
            total_pagado=Decimal('150.00'),
            correo_enviado=False,
            items_snapshot=[{'nombre': 'Teclado W17', 'precio': '150.00', 'cantidad': 1}]
        )

    def test_envio_correo_confirmacion_exitoso(self):
        """Envía el correo de confirmación y actualiza correo_enviado a True."""
        res = enviar_confirmacion_pedido.delay(self.pedido.pk)
        self.assertEqual(res.get()['estado'], 'ok')
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.cli.correo, mail.outbox[0].to)
        
        self.pedido.refresh_from_db()
        self.assertTrue(self.pedido.correo_enviado)

    def test_idempotencia_correo_duplicado_no_se_reenvia(self):
        """Si correo_enviado es True, la tarea omite el envío secundario."""
        self.pedido.correo_enviado = True
        self.pedido.save()

        res = enviar_confirmacion_pedido.delay(self.pedido.pk)
        self.assertEqual(res.get()['estado'], 'skip')
        self.assertEqual(len(mail.outbox), 0)

    def test_alerta_stock_bajo_envia_correo_admin(self):
        """Genera correo de alerta si hay productos con stock menor al umbral."""
        res = verificar_stock_bajo.delay(umbral=5)
        self.assertEqual(res.get()['total'], 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('admin@test.com', mail.outbox[0].to)
