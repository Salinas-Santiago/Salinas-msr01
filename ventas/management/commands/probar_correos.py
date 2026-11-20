# ventas/management/commands/probar_correos.py
"""Prueba el envío real de correos desde la terminal.

Ejemplos:
    python manage.py probar_correos --simple tucorreo@gmail.com
    python manage.py probar_correos --pedido 1
    python manage.py probar_correos --pedido 1 --reenviar
    python manage.py probar_correos --stock
    python manage.py probar_correos --stock --umbral 9999
"""
from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError

from ventas.models import Pedido
from ventas.tasks import enviar_confirmacion_pedido, verificar_stock_bajo


class Command(BaseCommand):
    help = 'Prueba el envío de correos: simple, confirmación de pago o stock bajo.'

    def add_arguments(self, parser):
        parser.add_argument('--simple', metavar='CORREO',
                            help='Envía un correo de prueba a esta dirección.')
        parser.add_argument('--pedido', type=int, metavar='ID',
                            help='Envía la confirmación de pago del pedido ID.')
        parser.add_argument('--reenviar', action='store_true',
                            help='Con --pedido: vuelve a enviarlo aunque ya se haya enviado.')
        parser.add_argument('--stock', action='store_true',
                            help='Ejecuta verificar_stock_bajo y envía la alerta si procede.')
        parser.add_argument('--umbral', type=int, default=5,
                            help='Umbral de stock para --stock (default: 5).')

    def handle(self, *args, **opts):
        if not (opts['simple'] or opts['pedido'] or opts['stock']):
            raise CommandError('Indica --simple CORREO, --pedido ID o --stock.')

        self.stdout.write(f"Backend de correo: {settings.EMAIL_BACKEND}")
        self.stdout.write(f"Remitente:         {settings.DEFAULT_FROM_EMAIL}")

        if opts['simple']:
            enviados = send_mail(
                'Prueba ERP Django',
                'Si lees esto, el correo funciona.',
                None,                      # None = DEFAULT_FROM_EMAIL
                [opts['simple']],
            )
            self.stdout.write(self.style.SUCCESS(
                f"Correo simple: {enviados} enviado(s) a {opts['simple']}"
            ))

        if opts['pedido']:
            if opts['reenviar']:
                Pedido.objects.filter(pk=opts['pedido']).update(correo_enviado=False)
            # .apply() corre la tarea aquí mismo: no requiere Redis ni worker
            resultado = enviar_confirmacion_pedido.apply(args=[opts['pedido']]).get()
            self.stdout.write(self.style.SUCCESS(f'Confirmación de pago: {resultado}'))

        if opts['stock']:
            resultado = verificar_stock_bajo.apply(
                kwargs={'umbral': opts['umbral']}
            ).get()
            self.stdout.write(self.style.SUCCESS(
                f"Stock bajo: {resultado['total']} producto(s), "
                f"alerta_enviada={resultado['alerta_enviada']}"
            ))
