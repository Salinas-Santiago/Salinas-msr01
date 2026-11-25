# Ficha de Sistematización — Espiral 6
## ERP Django · Espiral E6: Celery e Integraciones

| Campo | Contenido |
|---|---|
| **Número de espiral** | 6 |
| **Nombre del ciclo** | Celery e Integraciones |
| **Semanas** | W16 – W18 |
| **Fecha de inicio** | ___/___/_____ |
| **Fecha de cierre** | ___/___/_____ |
| **Responsable** | [Nombre del estudiante] |
| **Asesor** | MC. Román Fernando López González |

## 1. Objetivo del ciclo
Implementar procesamiento asíncrono con Celery para: correos
transaccionales de confirmación de pedido, alertas de stock bajo y
reportes diarios programados.

## 2. Tareas realizadas

| # | Tarea | Estado | Semana |
|---|---|---|---|
| 1 | pip install celery redis | ✅ | W16 |
| 2 | core/celery.py + core/__init__.py | ✅ | W16 |
| 3 | CELERY_* en settings.py | ✅ | W16 |
| 4 | Configuración de ejecución de Celery (ajustar a lo realizado) | ✅ | W16 |
| 5 | ventas/tasks.py (2 tareas placeholder) | ✅ | W16 |
| 6 | pip install django-anymail + SendGrid | ✅ | W17 |
| 7 | Template confirmacion_pedido.html + .txt | ✅ | W17 |
| 8 | Template alerta_stock.html + .txt | ✅ | W17 |
| 9 | enviar_confirmacion_pedido: correo real + idempotencia | ✅ | W17 |
| 10 | verificar_stock_bajo: alerta al admin | ✅ | W17 |
| 11 | Template reporte_ventas.html + .txt | ✅ | W18 |
| 12 | reporte_ventas_diario con annotate + Sum(F()) | ✅ | W18 |
| 13 | CELERY_BEAT_SCHEDULE (crontab + timedelta) | ✅ | W18 |
| 14 | Scheduler de tareas programadas (correr_programadas / Beat) | ✅ | W18 |

## 3. Evidencias
- Schedule: `python manage.py correr_programadas --listar`
- Tests: Ran 172 tests → OK
- Correo confirmación: enviado tras pago (idempotente)
- Alerta stock: enviada cuando stock < umbral
- Reporte: programado crontab(hour=8, minute=0), reporta el día anterior
- SendGrid → Activity: correos entregados

## 4. Criterios de aceptación

| Criterio | Estado |
|---|---|
| Las tareas se ejecutan sin bloquear la petición | ✅ |
| correo_enviado=True previene duplicados | ✅ |
| Alerta de stock enviada al admin | ✅ |
| reporte_ventas_diario en CELERY_BEAT_SCHEDULE | ✅ |
| verificar_stock_bajo en CELERY_BEAT_SCHEDULE | ✅ |
| 172 tests OK | ✅ |

## 5. Problemas encontrados
(completar durante la sesión; ejemplos reales: clave de SendGrid
escrita en settings.py bloqueada por GitHub, pywin32 en requirements.txt
rompió el deploy en Render, aviso anymail.W003 de SendGrid)

## 6. Lecciones aprendidas
1.
2.
3.

## 7. Tiempo total invertido

| Categoría | Horas |
|---|---|
| Diseño | |
| Implementación | |
| Pruebas | |
| Documentación | |
| **Total Espiral 6** | |