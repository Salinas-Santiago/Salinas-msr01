# core/celery.py
"""Configuración principal de Celery para el proyecto ERP Django."""
import os
from celery import Celery

# Establecer las configuraciones de Django por defecto para Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

app = Celery('core')

# Usar cadenas con prefijo 'CELERY_' para configurar Celery desde settings.py
app.config_from_object('django.conf:settings', namespace='CELERY')

# Cargar automáticamente módulos tasks.py en todas las apps registradas
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
