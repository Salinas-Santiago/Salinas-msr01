"""Tests de las tareas disparadas desde fuera (Opciones A y B).

Ejecutar con:
    python manage.py test tests.test_extra_tareas_externas --verbosity=2

Resultado esperado:
    Ran 7 tests in X.XXXs
    OK
"""
from decimal import Decimal

from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings

from configuracion.models import ConfiguracionERP
from productos.models     import Categoria, Producto
from ventas.tasks         import alertar_stock_tras_venta

TOKEN = 'token-de-prueba'

AJUSTES = {
    'EMAIL_BACKEND':                'django.core.mail.backends.locmem.EmailBackend',
    'TAREAS_TOKEN':                 TOKEN,
    'ALERTA_STOCK_DESTINATARIOS':   ['admin@test.com'],
    'REPORTE_VENTAS_DESTINATARIOS': ['admin@test.com'],
    'DEFAULT_FROM_EMAIL':           'test@erp.com',
    'SITE_URL':                     'http://testserver',
}


@override_settings(**AJUSTES)
class EndpointTareasTest(TestCase):
    """Tests de POST /tareas/<nombre>/ (Opción B)."""

    def setUp(self):
        mail.outbox = []
        ConfiguracionERP.get_instance()

    def test_sin_token_responde_403(self):
        respuesta = self.client.post('/tareas/reporte/')
        self.assertEqual(respuesta.status_code, 403)
        self.assertEqual(len(mail.outbox), 0)

    def test_token_incorrecto_responde_403(self):
        respuesta = self.client.post(
            '/tareas/reporte/', HTTP_X_TAREAS_TOKEN='otro-token'
        )
        self.assertEqual(respuesta.status_code, 403)
        self.assertEqual(len(mail.outbox), 0)

    def test_get_responde_405(self):
        respuesta = self.client.get(
            '/tareas/reporte/', HTTP_X_TAREAS_TOKEN=TOKEN
        )
        self.assertEqual(respuesta.status_code, 405)

    def test_reporte_con_token_envia_correo(self):
        respuesta = self.client.post(
            '/tareas/reporte/', HTTP_X_TAREAS_TOKEN=TOKEN
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.json()['ok'])
        self.assertEqual(len(mail.outbox), 1)

    def test_tarea_desconocida_responde_404(self):
        respuesta = self.client.post(
            '/tareas/otra-cosa/', HTTP_X_TAREAS_TOKEN=TOKEN
        )
        self.assertEqual(respuesta.status_code, 404)


@override_settings(**AJUSTES)
class AlertaTrasVentaTest(TestCase):
    """Tests de alertar_stock_tras_venta (Opción A)."""

    def setUp(self):
        mail.outbox = []
        cache.clear()
        ConfiguracionERP.get_instance()
        self.cat = Categoria.objects.create(nombre='Cat Venta')

    def test_envia_alerta_y_respeta_el_enfriamiento(self):
        Producto.objects.create(
            nombre='Casi agotado', precio=Decimal('10.00'),
            stock=1, categoria=self.cat
        )
        alertar_stock_tras_venta()
        self.assertEqual(len(mail.outbox), 1)

        alertar_stock_tras_venta()          # dentro de las 6 h: no repite
        self.assertEqual(len(mail.outbox), 1)

    def test_sin_stock_bajo_no_envia_ni_activa_enfriamiento(self):
        Producto.objects.create(
            nombre='Bien surtido', precio=Decimal('10.00'),
            stock=50, categoria=self.cat
        )
        alertar_stock_tras_venta()
        self.assertEqual(len(mail.outbox), 0)

        # Si después baja el stock, la alerta SÍ debe salir
        Producto.objects.filter(nombre='Bien surtido').update(stock=1)
        alertar_stock_tras_venta()
        self.assertEqual(len(mail.outbox), 1)