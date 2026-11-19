# CorteGestión — Estructura vigente

Monolito modular Django Templates. Se adoptan las convenciones `backend/config/`,
`backend/apps/` y `backend/docs/` de Proyecto-FYAG, sin copiar dependencias ni funciones.

| Ubicación desde la raíz | Responsabilidad |
|---|---|
| `backend/config/` | Settings, URLs principales, ASGI y WSGI. |
| `backend/apps/usuarios/` | Autenticación, roles, cuentas y comandos de gestión. |
| `backend/apps/gestion/` | Productos, proveedores, compras, ventas, stock y reportes. |
| `backend/apps/*/migrations/` | Historial original, trasladado sin modificar. |
| `backend/apps/*/tests/` | Pruebas por responsabilidad y helpers en `base.py`. |
| `backend/templates/` | Única ubicación de HTML propio: compartidos, registration, usuarios y gestion. |
| `backend/static/css/` | CSS global original. |
| `backend/static/js/` | JavaScript de formularios de operaciones. |
| `backend/scripts/docker_start.py` | Conexión, migraciones y arranque de desarrollo. |
| `backend/Dockerfile`, `backend/requirements.txt` | Imagen Python 3.12 y dependencias existentes. |
| `backend/manage.py` | Entrada Django local; dentro de Docker: `/app/manage.py`. |
| `backend/docs/` | Documentación vigente y registros históricos identificados como tales. |
| `scripts/` | Instalación Windows, preparación de entorno y permisos de pruebas MariaDB. |
| `compose.yaml`, `.env` | Infraestructura y secretos locales en raíz; `.env` ignorado. |

## Identidades e imports

- Paquetes Python: `apps.usuarios` y `apps.gestion`; imports absolutos y mocks usan esos prefijos.
- AppConfig: `apps.usuarios.apps.UsuariosConfig` y `apps.gestion.apps.GestionConfig`.
- Etiquetas Django **sin cambios**: `usuarios`, `gestion`; `AUTH_USER_MODEL='usuarios.Usuario'`.
- Las referencias `to='gestion.producto'`, dependencias de migraciones, tablas,
  content types, permisos y namespaces de URL **no son rutas Python**: no renombrarlas.
- `DIRS=[BASE_DIR/'templates']`; `APP_DIRS=True` conserva el admin de Django.
- Nombres lógicos de templates conservados, por ejemplo `gestion/catalogo.html`.
- Recursos: `{% static 'css/style.css' %}` y `{% static 'js/operacion.js' %}`.
- No crear templates ni estáticos dentro de las aplicaciones.

## Comandos desde la raíz

```powershell
docker compose config --quiet
docker compose up -d --build --wait
docker compose exec -T web python manage.py check --database default
docker compose exec -T web python manage.py makemigrations --check --dry-run
docker compose exec -T web python manage.py test --verbosity 2
docker compose exec -T web python manage.py test apps.gestion.tests.test_inventario --verbosity 2
docker compose exec -T web python manage.py test apps.usuarios.tests.test_autenticacion --verbosity 2
# Código local sin reconstrucción (el montaje sustituye solo /app):
docker compose run --rm --no-deps -v "${PWD}/backend:/app" web python manage.py check
# Ejecución con Python local requiere dependencias y variables de entorno ya cargadas:
python backend/manage.py check
```

Agregar `test_<responsabilidad>.py` dentro de cada aplicación; no importar clases de
tests entre módulos (duplica descubrimiento). Usar `TransactionTestCase` para conexiones
concurrentes reales. La suite usa `test_<DB_NAME>`, nunca el esquema operativo.

Docker construye con contexto raíz y Dockerfile explícito, pero copia **solo backend/**
a `/app`. `.env`, respaldos, entorno virtual y scripts de infraestructura no se incluyen.
No hay montaje de código predeterminado: reconstruir tras modificar archivos.

Volumen externo invariable: `carniceria_django_mariadb_data`, montado en `/var/lib/mysql`.
Puertos: `127.0.0.1:8000` y `127.0.0.1:8081`; MariaDB no publica puerto al host.
No inicializar una instalación existente ni eliminar volúmenes.

Árbol completo, inventario de movimientos y resultados: [REFACTORIZACION_FYAG.md](REFACTORIZACION_FYAG.md).
