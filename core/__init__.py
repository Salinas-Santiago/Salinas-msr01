# core/__init__.py
"""Carga de la aplicación Celery al iniciar Django."""
from .celery import app as celery_app

__all__ = ('celery_app',)
