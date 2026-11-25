"""Suite de pruebas W18 — Celery Beat y Tarea de Reporte Diario."""
from decimal import Decimal
from datetime import timedelta
from celery.schedules import crontab
from django.conf import settings
from django.core import mail
from django.test import TestCase, override_settings
from configuracion.models import ConfiguracionERP
from ventas.tasks import reporte_ventas_diario

EMAIL_SETTINGS = {
    'EMAIL_BACKEND': 'django.core.mail.backends.locmem.EmailBackend',
    'CELERY_TASK_ALWAYS_EAGER': True,
    'CELERY_TASK_EAGER_PROPAGATES': True,
    'ADMINS': [('Admin Test', 'admin@test.com')],
    'DEFAULT_FROM_EMAIL': 'test@erp.com',
}


class BeatScheduleConfigTest(TestCase):
    """Verifica la configuración del programador Celery Beat."""

    def test_schedule_contiene_tareas_requeridas(self):
        """CELERY_BEAT_SCHEDULE debe contener las tareas de stock y reporte diario."""
        schedule = settings.CELERY_BEAT_SCHEDULE
        tareas = [v['task'] for v in schedule.values()]
        self.assertIn('ventas.verificar_stock_bajo', tareas)
        self.assertIn('ventas.reporte_ventas_diario', tareas)

    def test_reporte_usa_crontab(self):
        """La tarea de reporte de ventas debe programarse mediante crontab."""
        schedule = settings.CELERY_BEAT_SCHEDULE
        item = schedule['reporte-ventas-diario-8am']
        self.assertIsInstance(item['schedule'], crontab)


@override_settings(**EMAIL_SETTINGS)
class ReporteVentasTest(TestCase):
    """Pruebas de la tarea de reporte diario de ventas."""

    def setUp(self):
        mail.outbox = []
        ConfiguracionERP.get_instance()

    def test_reporte_diario_ejecucion_y_envio(self):
        """Ejecuta la tarea e inspecciona el correo generado."""
        res = reporte_ventas_diario.delay()
        self.assertIn('total_pedidos', res.get())
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('admin@test.com', mail.outbox[0].to)
