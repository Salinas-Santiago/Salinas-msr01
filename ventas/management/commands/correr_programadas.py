# ventas/management/commands/correr_programadas.py
"""Ejecuta las tareas de CELERY_BEAT_SCHEDULE sin Redis ni worker.

Sustituto sencillo de `celery beat` para desarrollo (no es Celery Beat).
Usa las mismas reglas de programación (crontab / timedelta) de Celery.

Ejemplos:
    python manage.py correr_programadas --listar
    python manage.py correr_programadas --ahora
    python manage.py correr_programadas

IMPORTANTE: corre UNA sola copia; si hay dos, cada tarea se ejecuta dos veces
y se envían correos duplicados.
"""
import time

from celery import current_app
from celery.schedules import maybe_schedule
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone


class Command(BaseCommand):
    help = 'Ejecuta las tareas programadas de CELERY_BEAT_SCHEDULE sin Redis.'

    def add_arguments(self, parser):
        parser.add_argument('--listar', action='store_true',
                            help='Muestra el schedule configurado y termina.')
        parser.add_argument('--ahora', action='store_true',
                            help='Ejecuta TODAS las tareas una vez ahora y termina.')
        parser.add_argument('--intervalo', type=int, default=30,
                            help='Cada cuántos segundos revisa si toca alguna (default: 30).')

    def handle(self, *args, **opts):
        import ventas.tasks  # noqa: F401  (registra las tareas en Celery)

        entradas = getattr(settings, 'CELERY_BEAT_SCHEDULE', {})
        if not entradas:
            raise CommandError('CELERY_BEAT_SCHEDULE está vacío.')

        if opts['listar']:
            self.stdout.write(f'Zona horaria de Celery: {current_app.conf.timezone}')
            for nombre, cfg in entradas.items():
                prog = maybe_schedule(cfg['schedule'])
                self.stdout.write(f"- {nombre}: {cfg['task']}  ->  {prog}")
            return

        if opts['ahora']:
            for nombre, cfg in entradas.items():
                self._ejecutar(nombre, cfg)
            return

        # ── Bucle del scheduler ────────────────────────────────────────
        self.stdout.write(self.style.SUCCESS(
            f"Scheduler activo ({len(entradas)} tareas). Ctrl+C para detener."
        ))
        ultimo = {nombre: current_app.now() for nombre in entradas}
        try:
            while True:
                for nombre, cfg in entradas.items():
                    prog = maybe_schedule(cfg['schedule'])
                    toca, _ = prog.is_due(ultimo[nombre])
                    if toca:
                        ultimo[nombre] = current_app.now()
                        self._ejecutar(nombre, cfg)
                time.sleep(opts['intervalo'])
        except KeyboardInterrupt:
            self.stdout.write('\nScheduler detenido.')

    def _ejecutar(self, nombre, cfg):
        """Ejecuta una tarea en este mismo proceso (sin broker)."""
        try:
            tarea = current_app.tasks[cfg['task']]
        except KeyError:
            raise CommandError(f"La tarea {cfg['task']} no está registrada.")

        hora = timezone.localtime().strftime('%H:%M:%S')
        self.stdout.write(f'[{hora}] Ejecutando {nombre} ({cfg["task"]})...')
        resultado = tarea.apply(
            args=cfg.get('args', ()),
            kwargs=cfg.get('kwargs', {}),
        )
        valor = resultado.get(propagate=False)
        if resultado.failed():
            self.stdout.write(self.style.ERROR(f'    ERROR: {valor}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'    OK: {valor}'))