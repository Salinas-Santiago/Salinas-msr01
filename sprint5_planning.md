## Sprint Backlog — actualización W17

| Tarea | Estado |
|---|---|
| pip install celery redis flower | ✅ W16 |
| core/celery.py + tareas placeholder | ✅ W16 |
| pip install django-anymail | ✅ W17 |
| EMAIL_BACKEND por variable de entorno (consola / anymail / SMTP) | ✅ W17 |
| correo_enviado en Pedido + migración 0004 | ✅ W17 |
| Template confirmacion_pedido.html + .txt (correo de pago) | ✅ W17 |
| Template alerta_stock.html + .txt (correo de stock bajo) | ✅ W17 |
| enviar_confirmacion_pedido: correo real + idempotencia atómica | ✅ W17 |
| verificar_stock_bajo: alerta al admin | ✅ W17 |
| Comando probar_correos | ✅ W17 |
| 9 tests con mail.outbox | ✅ W17 |
| Celery Beat + tareas programadas | ⏳ W18 |
