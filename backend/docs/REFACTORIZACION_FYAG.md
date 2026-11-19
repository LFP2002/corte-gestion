# CorteGestión — Refactorización estructural FYAG

## Alcance y resultado local

Trabajo exclusivo en `refactor/estructura-fyag`, sin modificar ni fusionar `main`.
Plan original leído completo; referencia contrastada mediante GitHub API:
`LFP2002/Proyecto-FYAG/backend/{config,apps,docs}`. Solo se adoptó organización;
no se copiaron funciones, dependencias, aplicaciones ni frontend independiente.

Código movido físicamente, sin paquetes de compatibilidad ni copias legacy.
Se conservan dos aplicaciones y todas las reglas de negocio.

## Inventario de movimientos

Cada correspondencia de directorio incluye **todos sus archivos**, incluidos
`__init__.py`, migraciones y pruebas, salvo las excepciones indicadas.

| Origen | Destino |
|---|---|
| `config/**` | `backend/config/**` |
| `usuarios/**` | `backend/apps/usuarios/**`, excepto HTML |
| `gestion/**` | `backend/apps/gestion/**`, excepto HTML y JS |
| `usuarios/templates/usuarios/*.html` | `backend/templates/usuarios/*.html` |
| `gestion/templates/gestion/*.html` | `backend/templates/gestion/*.html` |
| `templates/**` | `backend/templates/**` |
| `static/css/style.css` | `backend/static/css/style.css` |
| `gestion/static/gestion/js/operacion.js` | `backend/static/js/operacion.js` |
| `docs/*.md` | `backend/docs/*.md` |
| `manage.py` | `backend/manage.py` |
| `requirements.txt` | `backend/requirements.txt` |
| `Dockerfile` | `backend/Dockerfile` |
| `docker_start.py` | `backend/scripts/docker_start.py` |

Creados: `backend/apps/__init__.py`, `backend/apps/gestion/apps.py`,
`backend/apps/gestion/tests/test_estructura.py`, `scripts/tests/test_estructura.ps1`
y este informe. `ESTRUCTURA_PROYECTO.md` se reemplazó por documentación vigente.
Se retiraron las carpetas vacías anteriores; **no se eliminó funcionalidad**.
El diff de la PR ofrece el inventario individual de renombrados.

Actualizados: AppConfigs, `INSTALLED_APPS`, inclusiones de URLs, imports absolutos
de producción/pruebas/comandos y destinos `patch()`. `AUTH_USER_MODEL` y etiquetas
siguen siendo `usuarios.Usuario`, `usuarios` y `gestion`. Los imports relativos
internos, nombres de URL y nombres lógicos de templates se conservan.

`BASE_DIR` ahora es `backend/`; las configuraciones existentes `DIRS` y
`STATICFILES_DIRS` resuelven las ubicaciones centrales sin cambios artificiales.
Solo cambió la referencia estática del formulario: `gestion/js/operacion.js` →
`js/operacion.js`. CSS y JS conservan exactamente sus bytes originales.

Compose declara `backend/Dockerfile` con contexto raíz. Docker copia únicamente
`backend/` a `/app`; el comando de gestión dentro del contenedor **no cambia**.
Arranque en `scripts/docker_start.py`, con ruta de imports y directorio de trabajo
resueltos desde el propio archivo. Scripts de instalación y permisos existentes
se conservan porque operan desde raíz y sus comandos Docker siguen siendo válidos.
Se verificaron sus escenarios Windows y se agregó una prueba de estructura.
`.gitignore` y `.dockerignore` existentes ya excluyen secretos, backups y cachés;
se conservaron, comprobando además que la imagen no contiene `.env` ni `.venv`.

CI se activa también por push a la rama de refactorización y comprueba la nueva
estructura en Windows. Se retiró la eliminación explícita de volumen de la limpieza
del runner; los runners hospedados son efímeros. Ningún volumen local fue eliminado.
README actualizado; informes anteriores marcados como registros históricos.

## Ejecución por fases y evidencias

1. Rama limpia al inicio. Docker Desktop estaba detenido: se inició el motor Linux,
   se inspeccionó el volumen existente y se arrancó únicamente `db` para respaldar.
2. Baseline con imagen original: `check --database default` sin problemas;
   `makemigrations --check --dry-run`: `No changes detected`; **50 tests, OK (7,667 s)**.
3. Después de mover paquetes y recursos, `check` con backend montado: OK;
   **50 tests originales, OK (8,001 s)**. Sin modificar cuerpos ni aserciones para
   facilitar el refactor: únicamente rutas de imports/mocks.
4. Imagen reorganizada construida y arrancada: tres servicios saludables.
5. Validación integral sobre imagen nueva, sin montaje: resultados siguientes.

| Comprobación ejecutada | Resultado |
|---|---|
| `docker compose config --quiet` | Salida 0 |
| `docker compose up -d --build --wait` | Construcción y arranque correctos |
| `docker compose exec -T web python manage.py check --database default` | 0 problemas |
| `docker compose exec -T web python manage.py makemigrations --check --dry-run` | `No changes detected` |
| `docker compose exec -T web python manage.py test --verbosity 2` | **55 tests, OK (7,590 s)**, sin omisiones |
| `findstatic css/style.css js/operacion.js --verbosity 2` | Una ubicación por recurso: `/app/static/` |
| `powershell -ExecutionPolicy Bypass -File scripts/tests/test_instalacion_nueva.ps1` | 3 escenarios aprobados, sin Docker destructivo |
| `powershell -ExecutionPolicy Bypass -File scripts/tests/test_estructura.ps1` | Estructura, recursos y volumen aprobados |
| `git diff --check` | Sin errores de whitespace |
| Imagen | Python 3.12.16, Django 5.2.19; sin `.env` ni `.venv` |

Las cinco pruebas nuevas verifican identidad/tablas, origen central de cada HTML,
estáticos únicos, descubrimiento de las tres migraciones propias y módulos de URLs.
Las cincuenta previas conservan autenticación, roles, CSRF, stock, rollback,
concurrencia real MariaDB, reportes, dashboard, CLP e historial global del empleado.

### Navegador real

Microsoft Edge headless mediante Playwright (herramienta temporal fuera del repo):
login operativo a 1440 y 390 px, HTTP 200, CSS cargado y reglas accesibles,
JS HTTP 200, CSRF y campo contraseña presentes, sin desbordamiento horizontal.
phpMyAdmin HTTP 200; no se inició sesión administrativa en su interfaz.

Se levantó además un servidor temporal en `127.0.0.1:8002` contra **la copia
restaurada**, nunca contra los datos operativos para escrituras. Con cuentas
sintéticas solo en esa copia se verificó:

- Login y logout de dueño/empleado.
- Panel, productos, ventas y stock de ambos roles a 1440 y 390 px.
- Proveedores, compras, reportes y usuarios del dueño; empleado recibe 403.
- Exactamente una sección activa por pantalla y CSS resuelto.
- Formularios de compra/venta: JS cargado, agregar línea, actualizar TOTAL_FORMS
  y precargar precio de venta al elegir producto; sin errores JS.

El contenedor temporal fue detenido y retirado; sus credenciales temporales fueron
eliminadas. Las pruebas automatizadas ejecutan los POST y mensajes sobre el esquema
de pruebas, sin crear operaciones en la base real. No se declara revisión humana
de usabilidad, sesión GUI phpMyAdmin ni validación RNF2 con personal del negocio.

## Base de datos: comparación antes/después

Volumen externo **`carniceria_django_mariadb_data`**, creado el 2026-11-09,
montado en `/var/lib/mysql`, sin modificación de nombre ni reinicialización.
Base operativa: `carniceria`, MariaDB 11.4. Puertos conservados: 8000 y 8081,
solo loopback. Servicios conservados: `web`, `db`, `phpmyadmin`.

Respaldo privado: `backups/estructura-fyag/antes.sql`, **25.182 bytes**,
SHA256 `7d7263fbfcac5d676dc00710f6d9647242045552290955bcfa7f584c904c13ff`.
Exportado con transacción consistente, rutinas, eventos, triggers y datos binarios;
restaurado con éxito en `cortegestion_respaldo_verificacion`. Se comprobaron los
recuentos de **todas** las tablas restauradas antes de usar esa copia en navegador.
El esquema aislado se conserva intencionadamente; no se borró ninguna base existente.

`despues.sql` es **idéntico byte a byte** a `antes.sql`: mismo esquema completo,
índices, constraints, datos y relaciones; no solo recuentos. Los SHA256 de todos
los archivos de migración Python propios también coinciden con el estado original.
No se crearon ni se regeneraron migraciones. Historial: **21 migraciones aplicadas**.
Content types: **13**; permisos: **52**, con los mismos IDs y app labels.
Grupos y vinculaciones siguen sin filas, tal como al inicio.

| Tabla | Antes | Después |
|---|---:|---:|
| auth_group | 0 | 0 |
| auth_group_permissions | 0 | 0 |
| auth_permission | 52 | 52 |
| django_admin_log | 0 | 0 |
| django_content_type | 13 | 13 |
| django_migrations | 21 | 21 |
| django_session | 0 | 0 |
| gestion_compra | 2 | 2 |
| gestion_detallecompra | 2 | 2 |
| gestion_detalleventa | 3 | 3 |
| gestion_movimientostock | 5 | 5 |
| gestion_producto | 2 | 2 |
| gestion_proveedor | 1 | 1 |
| gestion_venta | 2 | 2 |
| usuarios_usuario | 2 | 2 |
| usuarios_usuario_groups | 0 | 0 |
| usuarios_usuario_user_permissions | 0 | 0 |

Respaldo, snapshots de identidad/recuentos y hashes permanecen ignorados bajo
`backups/`; no se publican SQL, datos personales, secretos ni contenido de `.env`.

## GitHub y pendientes

Publicación y verificación remota se registrarán al crear la PR borrador.
No hacer merge automáticamente. No hay fallos automatizados locales conocidos.
Los límites de revisión humana/RNF2 anteriores no son resultados aprobados.

## Ejecutar desde un clon nuevo

Desde PowerShell, con Docker Desktop Linux iniciado:

```powershell
git clone --branch refactor/estructura-fyag https://github.com/LFP2002/corte-gestion.git
Set-Location corte-gestion
```

**Equipo con datos previos:** recuperar de forma privada el `.env` original (no
generar contraseñas nuevas para una BD ya inicializada). El volumen debe existir;
si no existe, detenerse y recuperar el respaldo mediante un procedimiento de
restauración, no inicializar uno vacío.

```powershell
docker volume inspect carniceria_django_mariadb_data
docker compose config --quiet
docker compose up -d --build --wait
docker compose exec -T web python manage.py check --database default
docker compose exec -T web python manage.py makemigrations --check --dry-run
docker compose cp scripts/pruebas_mariadb.sh db:/tmp/pruebas_mariadb.sh
docker compose exec -T db sh /tmp/pruebas_mariadb.sh
docker compose exec -T web python manage.py test --verbosity 2
```

**Equipo realmente nuevo, sin datos que recuperar:** ejecutar
`powershell -ExecutionPolicy Bypass -File .\scripts\instalacion_nueva.ps1`, confirmar
`NUEVA`, después `docker compose exec web python manage.py crear_dueno`.
El instalador rechaza un volumen preexistente y no sobrescribe `.env`.

Actualizar un clon existente limpio: `git switch refactor/estructura-fyag`,
`git pull --ff-only`, respaldar antes de reconstruir y ejecutar las validaciones
anteriores desde raíz. Detener con `docker compose stop`; nunca eliminar volúmenes.
Abrir http://localhost:8000 y http://localhost:8081.

## Árbol completo de archivos versionados

No incluye `.git/`, `.env`, `.venv`, respaldos, cachés ni herramientas temporales.

```text
corte-gestion/
├── .github/workflows/ci.yml
├── .vscode/settings.json
├── .dockerignore
├── .env.example
├── .gitattributes
├── .gitignore
├── README.md
├── compose.yaml
├── backend/
│   ├── Dockerfile
│   ├── manage.py
│   ├── requirements.txt
│   ├── apps/
│   │   ├── __init__.py
│   │   ├── gestion/
│   │   │   ├── __init__.py
│   │   │   ├── apps.py
│   │   │   ├── forms.py
│   │   │   ├── models.py
│   │   │   ├── reports.py
│   │   │   ├── services.py
│   │   │   ├── urls.py
│   │   │   ├── views.py
│   │   │   ├── migrations/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── 0001_initial.py
│   │   │   │   └── 0002_detalleventa_venta_and_more.py
│   │   │   ├── templatetags/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── moneda.py
│   │   │   │   └── navegacion.py
│   │   │   └── tests/
│   │   │       ├── __init__.py
│   │   │       ├── base.py
│   │   │       ├── test_catalogos.py
│   │   │       ├── test_compras.py
│   │   │       ├── test_concurrencia.py
│   │   │       ├── test_estructura.py
│   │   │       ├── test_formato.py
│   │   │       ├── test_interfaz.py
│   │   │       ├── test_inventario.py
│   │   │       ├── test_navegacion.py
│   │   │       ├── test_rendimiento.py
│   │   │       ├── test_reportes.py
│   │   │       ├── test_seguridad.py
│   │   │       └── test_ventas.py
│   │   └── usuarios/
│   │       ├── __init__.py
│   │       ├── admin.py
│   │       ├── apps.py
│   │       ├── forms.py
│   │       ├── models.py
│   │       ├── urls.py
│   │       ├── views.py
│   │       ├── management/
│   │       │   ├── __init__.py
│   │       │   └── commands/
│   │       │       ├── __init__.py
│   │       │       ├── crear_demo.py
│   │       │       └── crear_dueno.py
│   │       ├── migrations/
│   │       │   ├── __init__.py
│   │       │   └── 0001_initial.py
│   │       └── tests/
│   │           ├── __init__.py
│   │           ├── base.py
│   │           ├── test_autenticacion.py
│   │           ├── test_comandos.py
│   │           ├── test_panel.py
│   │           └── test_permisos.py
│   ├── config/
│   │   ├── __init__.py
│   │   ├── asgi.py
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── docs/
│   │   ├── ARQUITECTURA.md
│   │   ├── AUDITORIA.md
│   │   ├── CAMBIO_IDENTIDAD.md
│   │   ├── ENTREGA.md
│   │   ├── ESTRUCTURA_PROYECTO.md
│   │   ├── PLAN_REESTRUCTURACION_FYAG.md
│   │   ├── REFACTORIZACION_FYAG.md
│   │   └── VERIFICACION.md
│   ├── scripts/docker_start.py
│   ├── static/
│   │   ├── css/style.css
│   │   └── js/operacion.js
│   └── templates/
│       ├── 403.html
│       ├── base.html
│       ├── gestion/
│       │   ├── catalogo.html
│       │   ├── eliminar.html
│       │   ├── form.html
│       │   ├── operacion_detalle.html
│       │   ├── operacion_form.html
│       │   ├── operaciones.html
│       │   ├── paginacion.html
│       │   ├── reportes.html
│       │   └── stock.html
│       ├── registration/
│       │   ├── acceso_base.html
│       │   └── login.html
│       └── usuarios/
│           ├── eliminar.html
│           ├── form.html
│           ├── inicio.html
│           └── lista.html
└── scripts/
    ├── instalacion_nueva.ps1
    ├── preparar_entorno.ps1
    ├── pruebas_mariadb.sh
    └── tests/
        ├── test_estructura.ps1
        └── test_instalacion_nueva.ps1
```
