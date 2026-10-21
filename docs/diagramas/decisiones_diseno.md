# Decisiones de Diseño

Documento de decisiones de diseño del ERP (Sprint 1).

## Decisión 1: Usar Django como framework principal
**ID:** DD-001 / ADR-001
- **Estado:** Aceptada
- **Contexto:** Se necesita un framework con ORM, panel de administración y autenticación incluidos.
- **Decisión:** Usar Django.
- **Justificación:** Acelera el desarrollo y reduce código repetitivo.

## Decisión 2: SQLite en desarrollo, base de datos robusta en producción
**ID:** DD-002 / ADR-002
- **Estado:** Aceptada
- **Contexto:** El equipo necesita un entorno local sin configuración.
- **Decisión:** SQLite para desarrollo y pruebas; PostgreSQL en producción.
- **Justificación:** Cero configuración local y migración sencilla gracias al ORM.

## Decisión 3: API REST con Django REST Framework
**ID:** DD-003 / ADR-003
- **Estado:** Aceptada
- **Contexto:** Los módulos del ERP deben comunicarse entre sí y con clientes externos.
- **Decisión:** Exponer los datos mediante DRF.
- **Justificación:** Serializadores, vistas genéricas y autenticación integrados.

## Decisión 4: Modelo de datos normalizado con 8 entidades
**ID:** DD-004 / ADR-004
- **Estado:** Aceptada
- **Contexto:** Se busca evitar duplicación de información.
- **Decisión:** Normalizar el modelo hasta 3FN.
- **Justificación:** Integridad y consistencia de los datos.

## Decisión 5: Claves primarias autoincrementales
**ID:** DD-005 / ADR-005
- **Estado:** Aceptada
- **Contexto:** Simplicidad en relaciones entre entidades.
- **Decisión:** Usar `id` entero autoincremental en todas las tablas.
- **Justificación:** Compatible con el ORM de Django y fácil de depurar.

## Decisión 6: Pruebas automatizadas con el runner de Django
**ID:** DD-006 / ADR-006
- **Estado:** Aceptada
- **Contexto:** Cada sprint debe validar sus entregables.
- **Decisión:** Usar `python manage.py test` con una carpeta `tests/`.
- **Justificación:** Sin dependencias adicionales y fácil de integrar en CI.

## Decisión 7: Documentación en Markdown con diagramas Mermaid
**ID:** DD-007 / ADR-007
- **Estado:** Aceptada
- **Contexto:** La documentación debe vivir junto al código y versionarse.
- **Decisión:** Escribir docs en Markdown y diagramas ER en Mermaid.
- **Justificación:** Legible en GitHub y fácil de mantener.