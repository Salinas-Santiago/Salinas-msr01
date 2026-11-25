[35mcore/celery.py[m[36m:[m[32m8[m[36m:[m    # Iniciar worker (procesa [1;31mtareas[m)
[35mcore/celery.py[m[36m:[m[32m11[m[36m:[m    # Iniciar worker + Beat (procesa [1;31mtareas[m + [1;31mtareas[m programadas)
[35mcore/celery.py[m[36m:[m[32m31[m[36m:[m# Auto-descubrir [1;31mtareas[m en todos los archivos tasks.py de las apps instaladas
[35mcore/settings.py[m[36m:[m[32m238[m[36m:[m# core/settings.py — [1;31mtareas[m programadas (W18)
[35mcore/settings.py[m[36m:[m[32m394[m[36m:[m# ── CELERY — Cola de [1;31mtareas[m asíncronas (broker de archivos) ───────────────
[35mcore/settings.py[m[36m:[m[32m430[m[36m:[m# Celery en desarrollo: ejecutar las [1;31mtareas[m de inmediato, sin Redis ni worker.
[35mcore/settings.py[m[36m:[m[32m437[m[36m:[m# core/settings.py — [1;31mtareas[m programadas (W18)
[35mcore/settings.py[m[36m:[m[32m464[m[36m:[m# Token que protege las direcciones /[1;31mtareas[m/... (vacío = deshabilitadas)
[35mcore/urls.py[m[36m:[m[32m28[m[36m:[m    path('[1;31mtareas[m/', include('ventas.urls_[1;31mtareas[m')),
[35mtests/test_w16_celery.py[m[36m:[m[32m1[m[36m:[m"""Suite de pruebas W16 — Celery y [1;31mtareas[m asíncronas (sin Redis).
[35mtests/test_w16_celery.py[m[36m:[m[32m31[m[36m:[m    def test_[1;31mtareas[m_registradas_en_celery(self):
[35mtests/test_w16_celery.py[m[36m:[m[32m33[m[36m:[m        [1;31mtareas[m = celery_app.tasks.keys()
[35mtests/test_w16_celery.py[m[36m:[m[32m34[m[36m:[m        self.assertIn('ventas.enviar_confirmacion_pedido', [1;31mtareas[m)
[35mtests/test_w16_celery.py[m[36m:[m[32m35[m[36m:[m        self.assertIn('ventas.verificar_stock_bajo', [1;31mtareas[m)
[35mtests/test_w16_celery.py[m[36m:[m[32m39[m[36m:[m    """Tests de la lógica de las [1;31mtareas[m, ejecutadas con .apply()."""
[35mtests/test_w16_celery.py[m[36m:[m[32m75[m[36m:[m    """Verifica que las vistas invocan las [1;31mtareas[m con .delay()."""
[35mtests/test_w18_beat.py[m[36m:[m[32m43[m[36m:[m        [1;31mtareas[m   = [v['task'] for v in schedule.values()]
[35mtests/test_w18_beat.py[m[36m:[m[32m44[m[36m:[m        self.assertIn('ventas.verificar_stock_bajo', [1;31mtareas[m)
[35mtests/test_w18_beat.py[m[36m:[m[32m49[m[36m:[m        [1;31mtareas[m   = [v['task'] for v in schedule.values()]
[35mtests/test_w18_beat.py[m[36m:[m[32m50[m[36m:[m        self.assertIn('ventas.reporte_ventas_diario', [1;31mtareas[m)
[35mventas/management/commands/correr_programadas.py[m[36m:[m[32m2[m[36m:[m"""Ejecuta las [1;31mtareas[m de CELERY_BEAT_SCHEDULE sin Redis ni worker.
[35mventas/management/commands/correr_programadas.py[m[36m:[m[32m25[m[36m:[m    help = 'Ejecuta las [1;31mtareas[m programadas de CELERY_BEAT_SCHEDULE sin Redis.'
[35mventas/management/commands/correr_programadas.py[m[36m:[m[32m31[m[36m:[m                            help='Ejecuta TODAS las [1;31mtareas[m una vez ahora y termina.')
[35mventas/management/commands/correr_programadas.py[m[36m:[m[32m36[m[36m:[m        import ventas.tasks  # noqa: F401  (registra las [1;31mtareas[m en Celery)
[35mventas/management/commands/correr_programadas.py[m[36m:[m[32m56[m[36m:[m            f"Scheduler activo ({len(entradas)} [1;31mtareas[m). Ctrl+C para detener."
[35mventas/tasks.py[m[36m:[m[32m114[m[36m:[m        # render_to_string sin request (las [1;31mtareas[m Celery no tienen request)
[35mventas/urls_tareas.py[m[36m:[m[32m1[m[36m:[m# ventas/urls_[1;31mtareas[m.py
[35mventas/urls_tareas.py[m[36m:[m[32m4[m[36m:[mfrom ventas import views_[1;31mtareas[m
[35mventas/urls_tareas.py[m[36m:[m[32m7[m[36m:[m    path('<str:nombre>/', views_[1;31mtareas[m.ejecutar_tarea, name='ejecutar_tarea'),
[35mventas/views_tareas.py[m[36m:[m[32m1[m[36m:[m# ventas/views_[1;31mtareas[m.py
[35mventas/views_tareas.py[m[36m:[m[32m2[m[36m:[m"""Direcciones protegidas por token para ejecutar [1;31mtareas[m desde fuera.
[35mventas/views_tareas.py[m[36m:[m[32m5[m[36m:[m    POST /[1;31mtareas[m/reporte/   → reporte de ventas del día anterior
[35mventas/views_tareas.py[m[36m:[m[32m6[m[36m:[m    POST /[1;31mtareas[m/stock/     → revisión de stock bajo
[35mventas/views_tareas.py[m[36m:[m[32m62[m[36m:[m        logger.error(f'[[1;31mtareas[m] Error en {nombre}: {exc}')
