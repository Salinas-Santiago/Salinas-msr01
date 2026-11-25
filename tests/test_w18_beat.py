"""Suite de pruebas W18 — Tareas programadas y reporte diario.

Verifica la configuración del schedule, la ejecución de la tarea
y el envío del correo de reporte.

Ejecutar con:
    python manage.py test tests.test_w18_beat --verbosity=2

Resultado esperado:
    Ran 8 tests in X.XXXs
    OK
"""
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone

from clientes.models      import Cliente
from configuracion.models import ConfiguracionERP
from productos.models     import Categoria, Producto
from ventas.models        import DetalleVenta, Pedido, Venta
from ventas.tasks         import reporte_ventas_diario

EMAIL_SETTINGS = {
    'EMAIL_BACKEND':                'django.core.mail.backends.locmem.EmailBackend',
    'CELERY_TASK_ALWAYS_EAGER':     True,
    'CELERY_TASK_EAGER_PROPAGATES': True,
    'REPORTE_VENTAS_DESTINATARIOS': ['admin@test.com'],
    'DEFAULT_FROM_EMAIL':           'test@erp.com',
    'SITE_URL':                     'http://testserver',
}


class BeatScheduleConfigTest(TestCase):
    """Verifica la configuración de CELERY_BEAT_SCHEDULE."""

    def test_beat_schedule_tiene_verificar_stock(self):
        """El schedule debe incluir verificar_stock_bajo."""
        schedule = settings.CELERY_BEAT_SCHEDULE
        tareas   = [v['task'] for v in schedule.values()]
        self.assertIn('ventas.verificar_stock_bajo', tareas)

    def test_beat_schedule_tiene_reporte_diario(self):
        """El schedule debe incluir reporte_ventas_diario."""
        schedule = settings.CELERY_BEAT_SCHEDULE
        tareas   = [v['task'] for v in schedule.values()]
        self.assertIn('ventas.reporte_ventas_diario', tareas)

    def test_reporte_usa_crontab(self):
        """El reporte diario debe usar crontab (no timedelta)."""
        from celery.schedules import crontab
        schedule = settings.CELERY_BEAT_SCHEDULE
        for nombre, config in schedule.items():
            if config['task'] == 'ventas.reporte_ventas_diario':
                self.assertIsInstance(
                    config['schedule'], crontab,
                    "reporte_ventas_diario debe usar crontab, no timedelta"
                )
                break

    def test_verificar_stock_usa_timedelta(self):
        """verificar_stock_bajo debe usar timedelta (intervalo)."""
        schedule = settings.CELERY_BEAT_SCHEDULE
        for nombre, config in schedule.items():
            if config['task'] == 'ventas.verificar_stock_bajo':
                self.assertIsInstance(
                    config['schedule'], timedelta,
                    "verificar_stock_bajo debe usar timedelta"
                )
                break


@override_settings(**EMAIL_SETTINGS)
class ReporteVentasTest(TestCase):
    """Tests de la tarea reporte_ventas_diario (dias_atras=0 = hoy)."""

    def setUp(self):
        mail.outbox = []
        ConfiguracionERP.get_instance()
        cat       = Categoria.objects.create(nombre='Cat Rep')
        self.prod = Producto.objects.create(
            nombre='Producto Reporte', precio=Decimal('500.00'),
            stock=10, categoria=cat
        )
        cli = Cliente.objects.create(
            nombre='Cliente Rep', correo='rep@test.com'
        )
        # Una venta de HOY (para el top de productos)
        venta = Venta.objects.create(cliente=cli)
        DetalleVenta.objects.create(
            venta=venta, producto=self.prod,
            cantidad=3, precio_unitario=Decimal('500.00')
        )
        # Un pedido pagado de HOY (para los KPIs)
        Pedido.objects.create(
            numero_pedido = 'PED-REP-001',
            cliente       = cli,
            estado        = 'pagado',
            total_pagado  = Decimal('1500.00'),
        )

    def test_reporte_envia_correo_al_admin(self):
        """La tarea debe enviar correo al administrador."""
        reporte_ventas_diario.delay(dias_atras=0)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('admin@test.com', mail.outbox[0].to)

    def test_reporte_asunto_contiene_fecha(self):
        """El asunto debe contener la fecha del reporte."""
        reporte_ventas_diario.delay(dias_atras=0)
        fecha_str = timezone.localdate().strftime('%d/%m/%Y')
        self.assertIn(fecha_str, mail.outbox[0].subject)

    def test_reporte_sin_ventas_envia_correo_con_cero(self):
        """Aunque no haya ventas, el reporte se envía y muestra 0 pedidos."""
        Pedido.objects.all().delete()
        DetalleVenta.objects.all().delete()

        reporte_ventas_diario.delay(dias_atras=0)

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Pedidos pagados: 0', mail.outbox[0].body)

    def test_reporte_devuelve_totales_correctos(self):
        """La tarea devuelve el conteo, el total y el top correctos."""
        resultado = reporte_ventas_diario.delay(dias_atras=0).get()

        self.assertEqual(resultado['total_pedidos'], 1)
        self.assertEqual(
            Decimal(resultado['total_facturado']), Decimal('1500.00')
        )
        self.assertEqual(len(resultado['top_productos']), 1)
        self.assertEqual(resultado['top_productos'][0]['unidades'], 3)