# Sprint 5 Retrospective — ERP Django
## Semanas W16–W18 · Espiral 6: Celery e Integraciones

**Fecha:** ___/___/_____

## ¿Qué funcionó bien? (Keep)
1. El campo correo_enviado en Pedido, reclamado con un UPDATE atómico,
   resolvió el problema de duplicados sin un sistema externo.
2. @override_settings(EMAIL_BACKEND=locmem) hizo los tests de correo
   triviales: mail.outbox captura todo sin enviar nada.
3. Definir las tareas programadas en un solo CELERY_BEAT_SCHEDULE
   permitió ejecutarlas igual con o sin Redis.

## ¿Qué mejorar? (Improve)
1. Documentar mejor el procedimiento de arranque de los procesos.
2. Disponer de un Redis (local o en la nube) para ejecutar worker y
   Beat reales; sin broker solo se pudo simular el scheduler.
3. Revisar que el top de productos del reporte use la misma fuente
   de datos que los KPIs (Pedido vs Venta).

## Acción de mejora (Kaizen) para Sprint 6
> "En el Sprint 6 (Dashboard), pre-calcularé los KPIs con annotate
>  desde el principio, sin iterar en Python."

## Velocidad del Sprint 5

| HU | Pts plan. | Pts ent. |
|---|---|---|
| HU-E6-01 Infraestructura Celery | 3 | 3 |
| HU-E6-02 Tareas sin bloquear HTTP | 2 | 2 |
| HU-E6-03 Correo confirmación post-pago | 5 | 5 |
| HU-E6-04 Alerta stock bajo | 3 | 3 |
| HU-E6-05 Reporte diario programado | 3 | 3 |
| HU-E6-06 Monitorear tareas | 2 | 2 |
| **Total** | **18** | **18** |

**Velocidad Sprint 5:** 18 puntos
**Velocidad acumulada (S0–S5):** 123 puntos