# CorteGestión — Resumen de archivos de la entrega

## Creados

- Infraestructura: `Dockerfile`, `compose.yaml`, `docker_start.py`, `.dockerignore`,
  `.gitignore`, `.gitattributes`, `.env.example`.
- Configuración local privada: `.env` (generado, no distribuible ni incluido en imagen).
- Negocio: `gestion/__init__.py`, `models.py`, `services.py`, `forms.py`, `views.py`,
  `urls.py`, `reports.py` y `gestion/migrations/0001_initial.py`,
  `0002_detalleventa_venta_and_more.py`, `__init__.py`.
- Pruebas: `gestion/tests/` (catálogos, compras, ventas, inventario, reportes,
  seguridad, concurrencia y rendimiento) y `usuarios/tests/`.
- Alta segura: `usuarios/management/commands/crear_dueno.py`.
- Interfaz: `templates/403.html`, `gestion/templates/gestion/` (catálogo, formularios,
  confirmación de eliminación, operaciones, detalles, inventario, reportes,
  paginación) y `gestion/static/gestion/js/operacion.js`.
- Utilidades: `scripts/preparar_entorno.ps1`, `scripts/pruebas_mariadb.sh`.
- Documentación: `docs/AUDITORIA.md`, `ARQUITECTURA.md`, `VERIFICACION.md`, `ENTREGA.md`.

## Modificados

- `requirements.txt`: Django 5.2 LTS actualizado y mysqlclient; sin PyMySQL/cryptography.
- `config/settings.py`, `config/urls.py`: entorno obligatorio, MariaDB estricta,
  instalación de `gestion` y rutas nuevas.
- `usuarios/forms.py`, `views.py`, `urls.py`, `admin.py`, `tests.py`: cierre del registro,
  autorización, validación de claves, protección/desactivación del último dueño,
  protección histórica y pruebas.
- `usuarios/management/commands/crear_demo.py`: alias seguro sin claves fijas.
- `templates/base.html`, `templates/registration/login.html`,
  `usuarios/templates/usuarios/inicio.html`, `lista.html`, `static/css/style.css`:
  navegación, panel, mensajes y mejoras responsivas conservando la identidad visual.
- `README.md`: instalación exacta, uso, migraciones, tests, demostración y mantenimiento.

## Retirado con justificación

`templates/registration/registro.html` y la vista/formulario de registro público:
permitían crear cuentas abiertas y concedían automáticamente el primer rol dueño.
Se reemplazan por comando seguro y creación de usuarios autorizada al dueño.
El comando demo conserva su nombre por compatibilidad, pero no las claves inseguras.

## Preservado

`usuarios/models.py`, su migración inicial, el resto de migraciones originales,
la configuración WSGI/ASGI, los templates útiles del CRUD y el entorno `.venv`.
No se modificaron datos de XAMPP, no se borraron bases/volúmenes existentes,
no hubo push ni operaciones Git (la carpeta no es repositorio).

Pruebas, resultados y límites conocidos: `VERIFICACION.md`. No se dejan usuarios
demo ni contraseñas de aplicación predeterminadas; falta el alta interactiva del dueño.
