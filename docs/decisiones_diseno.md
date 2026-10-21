# Decisiones de Diseño

Documento de decisiones de diseño del ERP (Sprint 1).

### D-01: Usar Django como framework principal
- **Estado:** Aceptada
- **Contexto:** Se necesita un framework con ORM, panel de administración y autenticación incluidos.
- **Decisión:** Usar Django.
- **Justificación:** Acelera el desarrollo y reduce código repetitivo.

### D-02: SQLite en desarrollo, base de datos robusta en producción
- **Estado:** Aceptada
- **Contexto:** El equipo necesita un entorno local sin configuración.
- **Decisión:** SQLite para desarrollo y pruebas; PostgreSQL en producción.
- **Justificación:** Cero configuración local y migración sencilla gracias al ORM.

### D-03: API REST con Django REST Framework
- **Estado:** Aceptada
- **Contexto:** Los módulos del ERP deben comunicarse entre sí y con clientes externos.
- **Decisión:** Exponer los datos mediante DRF.
- **Justificación:** Serializadores, vistas genéricas y autenticación integrados.

### D-04: Modelo de datos normalizado con 8 entidades
- **Estado:** Aceptada
- **Contexto:** Se busca evitar duplicación de información.
- **Decisión:** Normalizar el modelo hasta 3FN.
- **Justificación:** Integridad y consistencia de los datos.

### D-05: Claves primarias autoincrementales
- **Estado:** Aceptada
- **Contexto:** Simplicidad en las relaciones entre entidades.
- **Decisión:** Usar `id` entero autoincremental en todas las tablas.
- **Justificación:** Compatible con el ORM de Django y fácil de depurar.

### D-06: Pruebas automatizadas con el runner de Django
- **Estado:** Aceptada
- **Contexto:** Cada sprint debe validar sus entregables.
- **Decisión:** Usar `python manage.py test` con una carpeta `tests/`.
- **Justificación:** Sin dependencias adicionales y fácil de integrar en CI.
