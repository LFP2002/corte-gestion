# CorteGestión — Estructura del proyecto

Se mantienen los paquetes principales en la raíz, sin `src/` ni capas adicionales.
La organización no cambia aplicaciones Django, URLs funcionales, modelos,
migraciones, permisos ni reglas de negocio.

## Responsabilidad de cada carpeta

| Carpeta | Contenido y responsabilidad |
|---|---|
| `config/` | Settings, URLs principales y puntos de entrada ASGI/WSGI. |
| `gestion/` | Modelos, formularios, vistas, rutas, servicios transaccionales y consultas de reportes. Se conservan los módulos existentes. |
| `gestion/migrations/` | Historial de esquema existente, sin modificaciones por esta refactorización. |
| `gestion/templates/gestion/` | Plantillas exclusivas del negocio: catálogos, formularios, operaciones, stock, reportes y paginación. |
| `gestion/static/gestion/js/` | `operacion.js`, propio de compras/ventas, con namespace para evitar colisiones entre apps. |
| `gestion/tests/` | Suite de gestión dividida por responsabilidad. |
| `usuarios/` | Modelo personalizado `usuarios.Usuario`, autenticación, permisos, formularios y rutas actuales. |
| `usuarios/management/commands/` | Comandos actuales de creación segura del dueño y alias compatible. |
| `usuarios/migrations/` | Migración inicial preservada. |
| `usuarios/templates/usuarios/` | Plantillas del panel y administración de usuarios, conservadas en su ubicación. |
| `usuarios/tests/` | Autenticación, permisos y comandos de usuarios. |
| `templates/` | Solo plantillas compartidas: `base.html`, `403.html` y `registration/`. |
| `static/css/` | CSS global compartido, sin cambios de contenido o diseño. |
| `scripts/` | Preparación local del entorno y permisos de pruebas MariaDB. |
| `docs/` | Documentación existente de arquitectura, auditoría, entrega y verificación. |
| `.vscode/` | Preferencias del editor; oculta entornos, cachés y artefactos sin afectar la ejecución. |

En la raíz permanecen `Dockerfile`, `compose.yaml`, `docker_start.py`, `manage.py`,
`requirements.txt`, `.env.example` y `README.md`. Docker sigue copiando el proyecto
a `/app`; no fue necesario cambiar el arranque ni la configuración de Django.

## Dónde agregar pruebas

### Gestión — 31 escenarios existentes

- `test_catalogos.py`: CRUD de productos/proveedores y acceso al catálogo.
- `test_compras.py`: registro de compras, validación, totales y rollback.
- `test_ventas.py`: ventas, validación, totales, rollback y persistencia al consultar.
- `test_inventario.py`: entradas/salidas, saldo de 9,5 kg y protección del historial.
- `test_reportes.py`: agregaciones y límites de semana/mes.
- `test_seguridad.py`: controles transversales de servicios, vistas y CSRF.
- `test_concurrencia.py`: conexiones reales y bloqueo transaccional con MariaDB.
- `test_rendimiento.py`: medición informativa de POSTs; no valida por sí sola RNF2.
- `base.py`: preparación común (`BaseNegocio`, `BaseVentas`), sin métodos `test_*`.

### Usuarios — 7 escenarios existentes

- `test_autenticacion.py`: login/logout y registro público cerrado.
- `test_permisos.py`: autorización y protección del último dueño activo.
- `test_comandos.py`: creación segura e idempotente del primer dueño.
- `base.py`: preparación común de usuarios, sin escenarios propios.

Los `__init__.py` de ambos paquetes se mantienen vacíos. No importar clases de
pruebas de un módulo de tests a otro: Django/unittest podría descubrirlas de nuevo.
Compartir únicamente datos y helpers en `base.py`. Los archivos nuevos deben llamarse
`test_<responsabilidad>.py`; usar TestCase salvo que la prueba necesite transacciones
y conexiones independientes, como la concurrencia existente con TransactionTestCase.

```powershell
# Suite completa (después de reconstruir la imagen)
docker compose exec web python manage.py test --verbosity 2
# Solo una responsabilidad
docker compose exec web python manage.py test gestion.tests.test_inventario --verbosity 2
docker compose exec web python manage.py test usuarios.tests.test_autenticacion --verbosity 2
```

## Referencias y mantenimiento

- Los nombres de templates siguen siendo `gestion/catalogo.html`, etc. Las vistas,
  `{% extends %}` y `{% include %}` no necesitan nuevas rutas: `APP_DIRS=True` ya
  busca dentro de las apps instaladas. No duplicar estas plantillas globalmente.
- El CSS se referencia con `{% static 'css/style.css' %}`.
- El script se referencia con `{% static 'gestion/js/operacion.js' %}`.
- Sus URLs resultantes son `/static/css/style.css` y
  `/static/gestion/js/operacion.js`; las URLs funcionales no cambian.
- Las pruebas usan imports absolutos de `gestion.models`, `gestion.services`,
  `gestion.reports` y `usuarios.models`; los helpers se importan desde `.base`.
  Los destinos de `patch()` siguen apuntando a los módulos de producción originales.
- `.venv/` permanece intacta en su ubicación, ignorada por Git y Docker. No moverla
  ni incluirla en la imagen. `.env` y credenciales locales siguen fuera del repositorio.
- No guardar exports de base, claves privadas, cachés ni logs junto a código fuente.
  `.gitignore` y `.dockerignore` excluyen sus patrones habituales.

Después de mover recursos, comprobar `findstatic`, resolución de templates y
ejecutar las pruebas. Después de editar código, reconstruir con
`docker compose up -d --build --wait`: el código no se monta por defecto.
No generar migraciones para cambios de ubicación de pruebas/templates/estáticos.

## Verificación de esta refactorización

La revisión inicial encontró **38 pruebas aprobadas en 6,134 s**, usando la imagen
existente y MariaDB real. No existe repositorio Git, por lo que no se creó rama.
Se guardaron fuera del proyecto hashes de archivos y representaciones AST de los
38 escenarios, sin copiar contenidos de secretos.

Antes de retirar los archivos anteriores, se ejecutaron explícitamente los nuevos
paquetes: **38 pruebas aprobadas en 6,501 s**. Los 38 métodos de prueba conservaron
exactamente cuerpos, aserciones y decoradores, sin duplicados. Tras mover plantillas
y estáticos, los paquetes volvieron a pasar: **38 pruebas en 6,440 s**; `findstatic`
resolvió una sola ubicación para cada recurso nuevo.

Validación final sobre la imagen reconstruida:

| Comprobación ejecutada | Resultado |
|---|---|
| `docker compose config --quiet` | Código de salida 0. |
| `docker compose up -d --build --wait` | Construcción y arranque correctos; web y db saludables. |
| `docker compose exec web python manage.py check --database default` | `System check identified no issues (0 silenced).` |
| `docker compose exec web python manage.py makemigrations --check --dry-run` | `No changes detected`. |
| `docker compose exec web python manage.py test --verbosity 2` | `Ran 38 tests in 6.679s` — `OK`, sin omisiones. |

Se verificaron login/logout, compras, ventas, stock, reportes, concurrencia y
persistencia mediante los escenarios originales contra MariaDB. Desde Windows,
`/` (redirige al login), `/login/`, `/static/css/style.css`,
`/static/gestion/js/operacion.js` y phpMyAdmin respondieron HTTP 200.
Las nueve plantillas de gestión se resuelven desde la app, sin copias globales.

Los hashes confirmaron que permanecen intactos modelos, migraciones, servicios,
formularios, vistas, URLs, comandos, configuración Docker, dependencias y secretos.
CSS y JavaScript son idénticos byte a byte. La firma del esquema consultado en
MariaDB y los recuentos de todas las tablas de gestión/usuarios coinciden antes y
después. La imagen no contiene `.env` ni `.venv`.

No se borraron datos de aplicación ni volúmenes. El runner utiliza exclusivamente
su base de pruebas, creada y destruida de la forma habitual. No se ejecutaron
comandos de reinicio destructivo ni se modificaron secretos. No hay errores conocidos
pendientes de esta refactorización; no se realizó inspección visual/interactiva en
navegador ni se revalidó RNF2 con personal del negocio. Esos límites previos se mantienen.
