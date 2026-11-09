# CorteGestión

**Sistema de Gestión para Carnicerías** · MVP · Evaluación 3 INACAP.

Aplicación Django Templates para usuarios, productos, proveedores, compras, ventas,
inventario y reportes semanales/mensuales. Python 3.12, Django 5.2 LTS,
MariaDB 11.4 LTS y phpMyAdmin oficial. No requiere XAMPP, Python ni MariaDB en Windows.

## Inicio en Windows (PowerShell)

Requisitos: Docker Desktop iniciado, motor de contenedores Linux / WSL2 y Docker Compose v2.
Ejecutar desde la carpeta raíz del proyecto, preferentemente llamada `corte-gestion`.
El nombre Compose se fija como **`corte-gestion`**, con independencia del nombre de carpeta.

### Instalación nueva desde GitHub (sin datos previos)

```powershell
git clone https://github.com/LFP2002/corte-gestion.git
Set-Location corte-gestion
powershell -ExecutionPolicy Bypass -File .\\scripts\\instalacion_nueva.ps1
docker compose exec web python manage.py crear_dueno
```

El script comprueba Docker, solicita escribir `NUEVA`, prepara el entorno local,
crea el volumen **solo si no existe** y levanta los servicios. Si encuentra un
volumen existente, se detiene sin alterarlo. **Nunca usar esta inicialización
para recuperar una instalación previa**: en ese caso verifique su volumen y
restaure un respaldo si corresponde. No ejecute `docker compose down -v`.

### Instalación existente con volumen conservado

```powershell
# Solo crea .env si no existe, con secretos criptográficamente aleatorios.
powershell -ExecutionPolicy Bypass -File .\scripts\preparar_entorno.ps1
# Debe existir el volumen conservado; si falta en una instalación existente, detenerse.
docker volume inspect carniceria_django_mariadb_data
docker compose config --quiet
docker compose up -d --build --wait
docker compose logs web
docker compose exec web python manage.py crear_dueno
```

El último comando pide usuario, correo y contraseña oculta, dos veces. Aplica los
validadores Django, no permite sobrescribir cuentas y, si ya existe un dueño activo,
termina sin cambios ni preguntas. Un bloqueo de MariaDB evita dos altas simultáneas.
No hay usuarios ni contraseñas predeterminados. `crear_demo` es solo un alias seguro
del mismo comando; no genera cuentas demo. El dueño crea empleados en **Usuarios**.

MariaDB reutiliza el volumen externo **`carniceria_django_mariadb_data`**, cuyo nombre
histórico se conserva para proteger los datos. Compose falla si no existe: no crea
silenciosamente otro volumen vacío. Para una instalación realmente nueva, sin datos
previos y **solo tras confirmar que no se trata de recuperar una instalación existente**,
crear explícitamente ese volumen con `docker volume create carniceria_django_mariadb_data`
antes de iniciar. En otra máquina, recuperar primero el respaldo mediante un
procedimiento de restauración; crear un volumen vacío no recupera datos.

- Aplicación: **http://localhost:8000** (redirige al login).
- phpMyAdmin: **http://localhost:8081**. Iniciar con `DB_USER` y `DB_PASSWORD` de su
  `.env` local; servidor preconfigurado `db`. No usar el login de la aplicación.
- MariaDB **no publica** 3306 en Windows. Django conecta internamente con `db:3306`.

Alternativa al script: copiar `.env.example` a `.env` y completar las tres claves
vacías con secretos propios. No compartir `.env`, capturarlo en pantalla ni subirlo a Git.
El script no rota valores existentes. Para cambiar credenciales de una BD ya inicializada
hay que cambiar también la cuenta dentro de MariaDB: editar `.env` solamente no lo hace.

`web` espera el healthcheck de InnoDB, comprueba conexión real, ejecuta migraciones
y arranca `runserver`. Si falla, revisar `docker compose logs web db`.
La primera descarga/compilación puede tardar varios minutos. No se ejecutan
`makemigrations` automáticamente ni se borra información.

## Uso y roles

| Operación | Dueño | Empleado |
|---|---|---|
| Consultar productos, precios y stock | Sí | Sí |
| Registrar venta y consultar sus ventas | Sí | Sí |
| Consultar ventas de otros usuarios | Sí | No (404) |
| CRUD productos, proveedores y usuarios | Sí | No (403) |
| Registrar / consultar compras | Sí | No (403) |
| Reportes y movimientos de inventario | Sí | No (403 / ocultos) |

La ruta pública `/registro/` no existe (GET/POST → 404). Todo cambio exige sesión,
permisos de servidor y CSRF. Logout usa POST. Las contraseñas se almacenan mediante
hash Django, no cifrado reversible. Se impide quitar el último dueño activo y
eliminar la propia cuenta. Los usuarios con historial se **desactivan** al editar.
Un producto/proveedor con historial no se elimina: se marca inactivo. Un producto
inactivo no aparece en nuevas operaciones, pero conserva su stock e historial.

Las compras y ventas se confirman una sola vez al guardar: no hay borradores,
edición, eliminación, devoluciones ni anulaciones en este MVP. No hay facturación
electrónica; la compra admite referencia libre del documento. Revise antes de confirmar
y no repita el envío si la conexión se interrumpe: consulte primero el historial.

Los formularios admiten varios productos con **Agregar producto** y permiten omitir
líneas marcando **Eliminar**. Cantidades en kg admiten `2,5` o `2.5`, hasta 3 decimales.
Precios hasta 2 decimales, por kg/unidad; las ventas precargan el precio del catálogo,
editable antes de confirmar. No se aplica IVA ni se representa utilidad contable.
Una misma línea no puede repetirse: agrupe la cantidad por producto.

## Demostración obligatoria

1. Crear el primer dueño con el comando anterior e iniciar sesión.
2. **Proveedores → Nuevo registro**: crear un proveedor activo.
3. **Productos → Nuevo registro**: nombre `Posta rosada`, unidad `kg`, precio `8000`.
4. **Registrar compra**: proveedor, fecha actual, documento opcional, producto,
   cantidad `12`, precio `5000`. Confirmar: total `60000`.
5. **Stock**: verificar `12,000 kg`.
6. **Registrar venta**: producto, cantidad `2,5`, precio `8000`. Confirmar: total `20000`.
7. **Stock**: verificar `9,500 kg` y movimientos `+12` / `-2,5`.
8. **Reportes**: elegir semana o mes y una fecha que incluya las operaciones;
   comprobar total del proveedor y cantidad vendida `2,5 kg`.
9. Actualizar navegador / cerrar sesión y volver a entrar: los registros continúan.
10. phpMyAdmin → base `carniceria`: revisar `usuarios_usuario`, `gestion_producto`,
    `gestion_proveedor`, `gestion_compra`, `gestion_detallecompra`, `gestion_venta`,
    `gestion_detalleventa` y `gestion_movimientostock`. **Solo consultar**: modificar
    stock directamente rompe la trazabilidad.
11. Como dueño crear un empleado, salir y entrar con él. Comprobar venta y consulta
    de existencias, ausencia de administración y 403 al abrir `/compras/`,
    `/proveedores/`, `/usuarios/` o `/reportes/` directamente.

Este procedimiento supone un producto nuevo sin operaciones previas. Si ya existe,
su stock acumula compras y ventas; no se reinicia para repetir la demostración.

## Migraciones y mantenimiento

```powershell
docker compose exec web python manage.py check
docker compose exec web python manage.py showmigrations
docker compose exec web python manage.py migrate --noinput
docker compose exec web python manage.py makemigrations --check --dry-run
```

Se conserva intacta `usuarios/migrations/0001_initial.py`; `gestion` tiene migraciones
aditivas para compras y ventas. Para nuevos cambios de modelos, generar migraciones
con el código local montado (Windows):

```powershell
docker compose run --rm --no-deps -v "${PWD}:/app" web python manage.py makemigrations
docker compose up -d --build --wait
```

El código se copia a la imagen, no se monta por defecto: tras editar archivos,
reconstruir `web` con `docker compose up -d --build --wait`. La configuración instala
la versión de seguridad disponible de Django `>=5.2.19,<5.3`; revisar actualizaciones
y reconstruir periódicamente con `docker compose build --pull --no-cache web`.
La imagen se ejecuta como usuario no root. `mysqlclient` se compila con las librerías
MariaDB de Debian; no se necesita PyMySQL ni cryptography.

## Pruebas reales con MariaDB

Las pruebas crean y destruyen **solo** `test_carniceria`, no la base de la aplicación.
El usuario de aplicación normalmente no tiene permisos en esa base. Habilitarlos
explícitamente una vez, con el script que usa la credencial root desde el entorno
del contenedor sin imprimirla:

```powershell
docker compose cp scripts/pruebas_mariadb.sh db:/tmp/pruebas_mariadb.sh
docker compose exec db sh /tmp/pruebas_mariadb.sh
docker compose exec web python manage.py test --verbosity 2
# Pruebas de código local aún no copiado a la imagen:
docker compose run --rm --no-deps -v "${PWD}:/app" web python manage.py test --verbosity 2
```

No usar una base `test_carniceria` con información valiosa. Si cambia DB_NAME, el
script concede permisos sobre `test_<DB_NAME>`. No concede privilegios globales.

La suite incluye login, registro cerrado, roles, CSRF, CRUD, totales, coma decimal,
compras/ventas, rollback, historial protegido, reportes con límites calendario,
persistencia tras nuevas consultas y dos ventas concurrentes con conexiones reales.
`gestion.tests.test_rendimiento` mide POSTs de 1, 5 y 20 líneas (5 repeticiones por operación).
**Eso no valida RNF2**: falta medir tiempos de digitación y probar con el personal
del negocio, navegador real y carga representativa. Véase `docs/VERIFICACION.md`.

## Detener y reiniciar sin perder datos

```powershell
docker compose stop
docker compose start
# También conserva datos:
docker compose down
docker compose up -d --wait
```

El proyecto Compose se fija con `name: corte-gestion`; ya no depende del nombre
de la carpeta. El recurso lógico `mariadb_data` apunta explícitamente al volumen
externo `carniceria_django_mariadb_data`, montado en `/var/lib/mysql`. Sus etiquetas
históricas pueden seguir indicando `carniceria_django`: eso no cambia sus datos.

**No ejecutar `docker compose down -v` para detener o actualizar el proyecto.**
Esa opción elimina volúmenes administrados por Compose. El volumen actual es externo
y Compose no lo elimina, pero tampoco debe borrarse con `docker volume rm` ni con
limpiezas de Docker Desktop.
Un volumen persistente no sustituye una copia de seguridad: exportar desde phpMyAdmin
antes de cambios de esquema/importaciones. Este trabajo no importó ni modificó datos
de una antigua instalación XAMPP. Respaldarla por separado antes de cualquier migración.

## Arquitectura y alcance

- `usuarios`: modelo personalizado preservado, autenticación, roles y administración de cuentas.
- `gestion/models.py`: esquema relacional y restricciones de integridad.
- `gestion/services.py`: transacciones atómicas, bloqueo de productos en orden de PK,
  validación de datos, cálculo de importes y movimientos explícitos, sin señales.
- `gestion/forms.py` / `views.py`: entrada validada y permisos; los templates no actualizan stock.
- `gestion/reports.py`: agregaciones SQL y períodos calendario; listados paginados,
  detalles con `select_related` / `prefetch_related`, opciones de productos reutilizadas.
- `templates/`: plantillas compartidas; `gestion/templates/gestion/` y
  `usuarios/templates/usuarios/`: plantillas específicas de cada app.
- `static/css/style.css` y `gestion/static/gestion/js/operacion.js`: identidad visual
  burdeos/crema conservada y JavaScript pequeño sin framework adicional.
- `gestion/tests/` y `usuarios/tests/`: pruebas organizadas por responsabilidad.
  Estructura y ubicación de futuras pruebas: `docs/ESTRUCTURA_PROYECTO.md`.

Modelo y decisiones: `docs/ARQUITECTURA.md`. Auditoría inicial: `docs/AUDITORIA.md`.
Evidencia y limitaciones de verificación: `docs/VERIFICACION.md`.
Cambio de identidad y respaldo histórico verificado:
`docs/CAMBIO_IDENTIDAD.md`.

Es un entorno académico de **desarrollo local**, no un despliegue público. `runserver`,
DEBUG y phpMyAdmin no son adecuados para Internet; con DEBUG=False hace falta además
un servidor de estáticos/WSGI, HTTPS, gestión de secretos, copias y controles operativos.
`/admin/` queda restringido a usuarios activos con `is_staff` **y rol dueño**; el dueño
inicial no es staff/superusuario y administra todo el MVP desde sus pantallas normales.
No conceder esos privilegios para uso cotidiano.


## Integración continua en GitHub

El flujo `.github/workflows/ci.yml` se ejecuta en pushes a `main`, pull requests
hacia `main` y manualmente desde Actions. En un runner Linux desechable crea un
`.env` temporal con secretos aleatorios, un volumen de MariaDB exclusivo de ese
runner, construye los tres servicios, verifica Django/migraciones y ejecuta la
suite completa contra MariaDB. El flujo **no utiliza** los volúmenes ni las
credenciales del computador del desarrollador. Comprobar sus resultados en
**GitHub → Actions** antes de aprobar una pull request. Que CI apruebe no sustituye
la revisión visual ni la validación de RNF2 con usuarios.


## Mejoras de interfaz (rama de evaluación)

- Inicio con indicadores de productos activos, productos agotados, cantidad de ventas
  e importe vendido hoy. El dueño ve las ventas del negocio; cada empleado ve
  **solo sus propias ventas**. Las métricas son consultas de lectura y no cambian el inventario.
- Precios e importes se muestran con el filtro de plantillas `clp`
  (`gestion/templatetags/moneda.py`): `$60.000` si no hay centavos;
  `$1.234,50` si el valor registrado tiene fracción. El Decimal almacenado
  conserva toda su precisión y los formularios de registro no cambian.
- Catálogo e inventario distinguen «Agotado», «Activo/Disponible» e «Inactivo»;
  formularios de búsqueda compactos, tablas mejor rotuladas y paginación visible
  solo cuando existe más de una página.
- Antes de aprobar el cambio, comprobar manualmente panel, catálogos, stock,
  historial y reportes en escritorio y móvil. Los formularios de compra y venta
  siguen pendientes de revisión visual específica; sus servicios permanecen intactos.
