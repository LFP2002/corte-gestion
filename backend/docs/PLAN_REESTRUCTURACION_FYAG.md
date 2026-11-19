# PLAN — Reorganización estructural FYAG para CorteGestión

**Estado:** especificación original de trabajo. Implementación y verificaciones:
[REFACTORIZACION_FYAG.md](REFACTORIZACION_FYAG.md).
**Rama de trabajo:** `refactor/estructura-fyag`.
**Base:** `main` en CorteGestión.
**Referencia contrastada:** `LFP2002/Proyecto-FYAG`, que utiliza `backend/config`, `backend/apps/<dominio>`, documentación y CI por responsabilidad.

## Propósito

Reestructurar TODO CorteGestión como monolito modular Django en `backend/`, mantener plantillas y archivos estáticos centralizados en rutas únicas y conservar los datos, seguridad, permisos y funcionalidad existentes. CorteGestión sigue usando Django Templates: no crear React, `frontend/` ni una API DRF artificial.

## Estructura final obligatoria

```text
corte-gestion/
  .github/workflows/ci.yml
  backend/
    apps/
      __init__.py
      usuarios/
        __init__.py
        apps.py
        admin.py
        models.py
        forms.py
        views.py
        urls.py
        migrations/
        management/commands/
        tests/
      gestion/
        __init__.py
        apps.py
        admin.py (si existe)
        models.py
        forms.py
        services.py
        reports.py
        views.py
        urls.py
        migrations/
        templatetags/
        tests/
    config/
      __init__.py
      settings.py
      urls.py
      asgi.py
      wsgi.py
    templates/
      base.html
      403.html
      registration/
      usuarios/
      gestion/
    static/
      css/style.css
      js/operacion.js
    docs/
      (documentación vigente)
    scripts/
      docker_start.py
    Dockerfile
    requirements.txt
    manage.py
  scripts/
    preparar_entorno.ps1
    instalacion_nueva.ps1
    pruebas_mariadb.sh
    tests/
  compose.yaml
  .env.example
  .dockerignore
  .gitignore
  .gitattributes
  README.md
```

Preservar los archivos reales que no aparecen nombrados arriba y reubicar cada uno donde corresponda (sin dejarlos duplicados). El ejemplo no exige crear archivos innecesarios o vacíos.

## Invariantes fundamentales

1. **Identidad Django y esquema de datos:** registrar `apps.usuarios.apps.UsuariosConfig` con `name = 'apps.usuarios'`, `label = 'usuarios'`; crear/configurar `apps.gestion.apps.GestionConfig` con `name = 'apps.gestion'`, `label = 'gestion'`. Conservar `AUTH_USER_MODEL = 'usuarios.Usuario'`. Las migraciones existentes de `usuarios` y `gestion` se trasladan intactas, conservando nombres, dependencias y aplicación. No crear nuevas migraciones ni renombrar tablas, FKs o constraints. Los imports Python se actualizan al nuevo paquete; los identificadores de modelos y URLs se mantienen. Verificar `django_migrations`, `django_content_type` y permisos.
2. **Templates:** TODO HTML propio en `backend/templates/` con `registration/`, `usuarios/`, `gestion/`, además de `base.html`, `403.html`. No mantener directorios propios `templates/` dentro de `backend/apps/*` ni plantilla global duplicada. Mantener nombres lógicos de template, configurando `DIRS=[BASE_DIR/'templates']`. Conservar `APP_DIRS=True` para plantillas de `django.contrib.admin` y otras apps instaladas.
3. **Estáticos:** CSS, JavaScript e imágenes propios bajo `backend/static/`, namespaces por tipo, enlaces `{% static %}` corregidos. No dejar directorios `static/` repetidos en apps ni raíz.
4. **Docker:** seguir con Python 3.12, Django 5.2.x, MariaDB 11.4, phpMyAdmin y los servicios `web/db/phpmyadmin`. El `compose.yaml` y `.env` permanecen en raíz; actualizar `build.context`, `dockerfile`, `WORKDIR`, `COPY`, arranque, rutas y healthchecks. Mantener `name: corte-gestion`, puertos locales `127.0.0.1:8000` y `127.0.0.1:8081`. **Preservar exactamente el volumen externo `carniceria_django_mariadb_data` montado en `/var/lib/mysql`**. No `docker compose down -v`, `docker volume rm`, `docker system prune --volumes` ni inicialización vacía sobre datos existentes.
5. **Seguridad y reglas del negocio:** conservar roles dueño/empleado, login/logout, protección CSRF, validaciones, movimientos de stock, transacciones y concurrencia. Empleado: consultar todas las ventas y sus detalles sin editarlas, con indicadores del panel limitados a sus propias ventas; dueño: permisos gerenciales.
6. **Infraestructura y documentos:** ajustar `.github/workflows/ci.yml`, pruebas Windows PowerShell, scripts de instalación, `.dockerignore`, `.gitignore`, README y documentación reubicada bajo `backend/docs`. No exponer `.env`, respaldos, archivos SQL, datos personales, credenciales, volúmenes ni entorno virtual; no alterar secretos. Todos los comandos deben funcionar desde la raíz del repositorio.
7. **URLs:** mantener todos los paths HTTP, los nombres de rutas (`gestion:...`, `inicio`, `usuario_lista`, etc.), las vistas y el renderizado. `config.urls` debe importar/incluir `apps.usuarios.urls` y `apps.gestion.urls`.
8. **Migraciones e imports:** cambiar imports Python (por ejemplo `from gestion.models` a `from apps.gestion.models`), `unittest.mock.patch` y referencias a módulos según el nuevo path. **No reescribir automáticamente migraciones aplicadas.** Cualquier incompatibilidad por referencias serializadas debe resolverse y documentarse sin renumerar ni borrar historial.

## Secuencia de trabajo exigida

**Fase 0 — Inventario y baseline:** comprobar `git status`, estado real de rama, 50 pruebas Django/MariaDB, `check`, `makemigrations --check --dry-run`; enumerar ubicación efectiva de todos los templates, estáticos, imports y scripts; registrar número de filas por tabla, estado de `django_migrations`, volumen y nombre de la base; crear respaldo SQL verificado en `backups/` (ignorado por Git) antes de mover nada. Si el entorno está fallando, documentarlo.

**Fase 1 — Backend y paquetes:** mover físicamente Django a `backend/`, agrupar apps en `backend/apps/`, actualizar AppConfig con etiquetas estables y todos los imports. Ejecutar `python manage.py check` desde `backend/`.

**Fase 2 — Frontend de Django:** centralizar templates en `backend/templates/` y estáticos en `backend/static/`, corregir enlaces, vista de errores, login, CSS, JS y resolver colisiones de nombres. Mantener diseños y comportamiento.

**Fase 3 — Infraestructura:** mover dependencias y Dockerfile, actualizar Compose y `backend/scripts/docker_start.py`, instalación Windows, pruebas PowerShell y CI. Comprobar `docker compose config --quiet` y arrancar contra el volumen existente sin reinicializar datos.

**Fase 4 — Pruebas:** ejecutar `docker compose up -d --build --wait`, `docker compose exec -T web python manage.py check --database default`, `docker compose exec -T web python manage.py makemigrations --check --dry-run`, `docker compose exec -T web python manage.py test --verbosity 2`; verificar mínimo 50 pruebas y añadir checks de rutas/templates/estáticos/DB si son útiles. Comparar esquema, migraciones y recuentos antes/después. Probar login, owner, empleado, consulta global de ventas, compras, inventario y reportes; GET HTTP y recursos CSS/JS. Validar CI en GitHub sobre la rama mediante PR **borrador** hacia main. No afirmar éxitos no ejecutados.

**Fase 5 — Limpieza y entrega:** remover rutas vacías y duplicados después de validar, mover docs a `backend/docs`, dejar un árbol de directorios real y actualizado, documentar comandos desde raíz y cambios de import. Mantener `main` intacta, no hacer merge automático, no borrar datos, no crear `frontend/` sin necesidad.

## Criterios de aceptación

- **Una** ubicación de templates propios (`backend/templates`) y **una** de estáticos (`backend/static`).
- Django y apps íntegramente bajo `backend/` con `backend/apps/usuarios` y `backend/apps/gestion`.
- 0 migraciones nuevas o pendientes; mismo número de tablas, filas y relaciones, usuarios e historial de operaciones intactos.
- 50+ tests aprobados con MariaDB real; workflow Django/MariaDB + Windows verdes.
- Login, roles, vistas, rutas, CSS, JS y manejo de formularios verificados.
- Docker desde raíz con volumen externo intacto; `.env` local e ignorado.
- No carpetas legacy `config`, `gestion`, `usuarios`, `templates`, `static` o `docker_start.py` en raíz tras comprobar la reorganización.
- Pull request **draft** y reporte técnico de riesgos/excepciones; esperar autorización antes de merge.
