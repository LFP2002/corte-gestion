# CorteGestión — Cambio de identidad

**Sistema de Gestión para Carnicerías**. Identificador técnico: `corte-gestion`.

## Qué cambió y qué se conserva

- Marca visible en título del navegador, encabezado, acceso y panel principal.
- Nombre Compose: `carniceria_django` → `corte-gestion`, fijado en `compose.yaml`.
- Documentación actualizada; no fue necesario modificar scripts genéricos.
- Se conservan `config`, `usuarios`, `gestion`, modelos, migraciones, rutas,
  permisos, reglas de negocio, pruebas, CSS y JavaScript. No hay nuevas dependencias.
- La base sigue llamándose `carniceria`; usuario y credenciales de MariaDB no cambian.
  `.env` no fue editado ni incluido en la imagen. La carpeta raíz no fue renombrada.

## Volumen y datos inspeccionados

Se identificó el contenedor original `carniceria_django-db-1`, que montaba el volumen
real **`carniceria_django_mariadb_data`** en `/var/lib/mysql`.
Docker Desktop informa su ubicación dentro de la VM Linux como:

```text
/var/lib/docker/volumes/carniceria_django_mariadb_data/_data
```

No es una ruta de archivos de Windows. No mover ni editar sus archivos manualmente.
El volumen continúa existiendo con ese mismo nombre, contenido y ubicación después
del cambio; el contenedor nuevo es `corte-gestion-db-1`.

Estado encontrado antes del cambio, confirmado después:

| Registros | Cantidad |
|---|---:|
| Usuarios de aplicación | 0 |
| Productos y proveedores | 0 |
| Compras, ventas, detalles y movimientos de stock | 0 |
| Permisos Django | 52 |
| Tipos de contenido Django | 13 |
| Migraciones aplicadas | 21 |

Las 17 tablas conservan exactamente sus recuentos y hashes de filas, incluidas las
tablas vacías. No se atribuye a la migración una pérdida de usuarios o de operaciones:
**no existían antes**. No se crearon datos demo para disimular ese estado.

El Compose actual usa:

```yaml
name: corte-gestion
# ... servicios actuales sin cambios de conexión ...
volumes:
  mariadb_data:
    external: true
    name: carniceria_django_mariadb_data
```

`external: true` impide que Compose cree silenciosamente un volumen vacío si falta
el existente. Sus etiquetas históricas pueden seguir indicando el proyecto anterior.
No renombrar el volumen para que su nombre coincida con la marca, ni ejecutar dos
servidores MariaDB simultáneamente sobre él. No usar `-p carniceria_django` ni una
variable `COMPOSE_PROJECT_NAME` para arrancar otra copia del proyecto.

## Respaldo verificado antes del cambio

Se detuvieron los servicios de aplicación/phpMyAdmin para evitar escrituras durante
la transición, manteniendo MariaDB disponible para el respaldo. Se exportó la base
con `mariadb-dump --single-transaction --routines --events --triggers --hex-blob`,
sin imprimir contraseñas. La copia local quedó en:

```text
backups/cambio-identidad-20261108-215843/carniceria.sql
```

SHA-256 del respaldo:

```text
1B36F04CDCF446EF689E838A0A8031A004D46A71D50019674E287021A30E912F
```

Se restauró en un contenedor MariaDB 11.4 aislado, con almacenamiento temporal y
sin montar el volumen original. `mariadb-check` devolvió **OK para las 17 tablas**.
Una nueva exportación canónica de sus datos coincidió byte a byte con la exportación
canónica de la base original. SHA-256 de ambas:

```text
4E43ED0982FDC705661A2C499AB1D44D47907073F899C23723EDEFF972CF1359
```

La carpeta contiene también `datos-originales.sql`, `datos-restaurados.sql` y
`VERIFICADO.txt`. Son archivos locales privados, ignorados por Git y por el contexto
Docker; no se distribuyen con la aplicación. Conservar otra copia en una ubicación
segura: un respaldo en el mismo equipo no protege ante pérdida del disco.
No publicar dumps, aunque en esta instalación todavía no existan usuarios comerciales.

Comprobar la integridad del archivo sin revelar su contenido:

```powershell
Get-FileHash -Algorithm SHA256 .\backups\cambio-identidad-20261108-215843\carniceria.sql
```

El contenedor aislado de verificación se detuvo y retiró al terminar. Nunca se
restauró sobre la base original ni se borraron bases/volúmenes existentes.

## Transición ejecutada y verificaciones

Después de verificar el respaldo, se retiraron los contenedores/red del proyecto
anterior con `docker compose -p carniceria_django down`, **sin opciones de volúmenes**,
y se levantó el nuevo proyecto reutilizando el volumen externo.

| Comprobación ejecutada | Resultado |
|---|---|
| `docker compose config --quiet` | Correcto, código 0. |
| `docker compose up -d --build --wait` | Nuevo proyecto `corte-gestion`, tres servicios levantados. |
| `docker compose exec web python manage.py check --database default` | Sin problemas, 0 silenciados. |
| `docker compose exec web python manage.py makemigrations --check --dry-run` | `No changes detected`. |
| `docker compose exec web python manage.py test --verbosity 2` | **38 pruebas en 6,563 s — OK**, sin omisiones. |
| Inspección del montaje nuevo | Mismo volumen físico anterior. |
| Comparación de las 17 tablas | Mismos registros y hashes antes/después. |
| HTTP login y estáticos desde Windows | 200, marca/subtítulo/título comprobados. |
| phpMyAdmin | HTTP 200, login HTTP con credenciales del entorno y consulta de tablas correctos. |

El login/logout de Django y los permisos se verificaron con las pruebas existentes
en `test_carniceria`, no creando cuentas en la base real. Al no haber usuarios
operativos, el primer dueño debe crearse interactivamente cuando el responsable
lo decida: `docker compose exec web python manage.py crear_dueno`.

Los hashes de archivos confirmaron que no cambiaron secretos, modelos, migraciones,
servicios, formularios, vistas, rutas, permisos, comandos, pruebas, CSS o JavaScript.
No se generaron migraciones ni se modificó el esquema. No se ejecutaron commits,
push ni acciones de GitHub; esta carpeta no es un repositorio Git.

## Renombrar la carpeta raíz en Windows — pendiente manual

No ejecutar mientras VS Code, OpenCode u otros procesos estén trabajando dentro
de la carpeta. Guardar el trabajo, terminar esta sesión y cerrar los editores.
Abrir después una PowerShell independiente:

```powershell
Set-Location 'C:\Users\jugue\OneDrive\Documentos\Universidad\Ingenieria de software\carniceria_django'
# Retira contenedores/red, NO el volumen externo. No agregar -v.
docker compose down
Set-Location ..
Rename-Item -LiteralPath '.\carniceria_django' -NewName 'corte-gestion'
Set-Location '.\corte-gestion'
docker volume inspect carniceria_django_mariadb_data
docker compose config --quiet
docker compose up -d --build --wait
docker compose exec web python manage.py check --database default
```

Si la inspección no encuentra el volumen, **detenerse y recuperar el volumen o
restaurar el respaldo**; no crear un volumen vacío para ocultar el problema.
Si Windows impide renombrar, comprobar procesos abiertos y sincronización OneDrive,
sin forzar borrados. No modificar `.env`, nombres de BD ni volumen para renombrar
la carpeta. Volver a abrir VS Code/OpenCode en `corte-gestion` al terminar.
`.venv` se conserva, pero Docker no depende de ella ni de sus rutas locales antiguas.

Accesos sin cambios: http://localhost:8000 y http://localhost:8081.
El nombre Compose explícito y el volumen externo hacen independiente la persistencia
del nombre de la carpeta.

## Límites pendientes

No hay fallos conocidos del cambio de identidad. Falta exclusivamente el renombrado
manual de la carpeta y, para uso operativo, crear el primer dueño. No se realizó
inspección visual interactiva en navegador ni validación RNF2 con personal del negocio.
No borrar volúmenes desde Docker Desktop, no usar `docker volume rm` y no ejecutar
`docker compose down -v` como tarea de mantenimiento.
