# Seguridad, empleado del mes y filtros

## Alcance acordado antes de implementar

Base: `main` en `f2c9afb`; rama `feat/seguridad-usuarios-filtros-estadisticas`.
Auditoría inicial: estructura FYAG vigente, formularios UserCreationForm/ModelForm,
LoginView/LogoutView y ModelBackend de Django, comando crear_dueno con validate_password,
admin restringido a dueño/staff. Ventas con fecha comercial DateField y usuario protegido.
Baseline: **55 pruebas aprobadas en 7,776 s**, MariaDB real; Compose válido y check sin problemas.

Cambios previstos:
- Validador adicional, sin retirar los validadores existentes ni cambiar hashes/sesiones.
- Dos campos aditivos en Usuario para intentos y vencimiento; login público y admin
  mediante formularios Django con bloqueo transaccional de la fila del usuario.
- Desbloqueo POST exclusivo del dueño, con CSRF; no altera is_active ni rol.
- Empleado del mes mediante agregación ORM por fecha comercial, solo para dueño.
- Formularios GET validados y panel nativo reutilizable en seis listados, paginación
  que conserva todos los parámetros; sin frontend ni dependencias adicionales.
- Respaldo privado restaurado y validado antes de aplicar migraciones; ensayar primero
  contra copia aislada. Conservar volumen, cuentas e historial comercial.

## Implementación y controles

### Política de contraseña

`PoliticaPasswordValidator` exige longitud ≥8, mayúscula, minúscula, dígito decimal
y símbolo no alfanumérico/no espacio. Acepta letras Unicode. Devuelve todos los
requisitos faltantes en español con códigos separados. Se agrega a
`AUTH_PASSWORD_VALIDATORS` sin retirar similitud, longitud, contraseñas comunes o
numéricas. No se valida de nuevo una contraseña antigua al iniciar sesión.

Flujos de la aplicación: UserCreationForm, edición con validate_password,
`crear_dueno`/`crear_demo`; formularios originales de alta/cambio del admin y
`changepassword` de Django usan la misma configuración. No hay registro público.
El admin conserva UserAdmin; su alta ahora expone correo y rol de forma explícita.
No se guarda texto plano ni se altera el algoritmo de hash del framework.

Se extiende además el comando `createsuperuser` de Django: se heredan argumentos
estándar, se valida antes de llamar al manager original y se elimina la posibilidad
de omitir validadores tanto en modo interactivo como con DJANGO_SUPERUSER_PASSWORD.
Un superusuario nuevo recibe rol dueño para cumplir la restricción de acceso al admin;
no se promueven cuentas existentes. `--noinput` sin contraseña conserva la semántica
Django de contraseña inutilizable. No se incluye ningún secreto en mensajes.
`usuarios` se registra antes de `django.contrib.auth` para que Django descubra el
comando reforzado con prioridad; las etiquetas, backend y migraciones no cambian.

Las APIs de programación `create_user`, `set_password` y `authenticate` son APIs
confiables de Django, no endpoints públicos: no validan política ni contabilizan
intentos por sí mismas. Código futuro que acepte entradas debe usar los formularios
de la aplicación/validate_password, nunca una llamada directa como sustituto.
Los comandos de contraseña soportados validan la política; para el primer dueño
operativo se recomienda `crear_dueno`, sin privilegios staff/superusuario.

### Bloqueo persistente y recuperación

- `Usuario.intentos_fallidos`: entero positivo, inicialmente 0.
- `Usuario.bloqueo_hasta`: fecha/hora nullable, inicialmente NULL.
- Umbral: **3 fallos**, duración: **15 minutos**. La comparación usa tiempo consciente
  de zona horaria; el listado muestra hora de Santiago. En el límite exacto ya expiró.
- Login público y `/admin/login/` comparten contador y reglas. Se extienden
  AuthenticationForm/AdminAuthenticationForm; LoginView/LogoutView, ModelBackend,
  cookies, rutas y sesiones existentes se mantienen.
- `transaction.atomic` y `select_for_update` sobre la cuenta abarcan autenticación,
  incremento/reset y vencimiento. El error se lanza **fuera** de atomic para no
  revertir el contador. Los intentos durante el bloqueo no lo prolongan.
- Éxito antes del umbral reinicia contador; tras expirar, comienza un ciclo nuevo.
- Mensaje público idéntico para contraseña errónea, nombre inexistente, cuenta
  inactiva y bloqueada. No se crean registros para nombres inexistentes. También
  se realiza trabajo de hash para cuentas bloqueadas, sin almacenar la contraseña.
- Formularios incompletos se validan normalmente: no son comprobaciones de credenciales.
- No se modifica `is_active` ni rol. No se expulsan sesiones existentes: además de
  conservar compatibilidad, un dueño con sesión puede recuperar cuentas sin quedar
  excluido por un atacante que conozca su nombre.
- `/usuarios/<pk>/desbloquear/`: solo dueño, solo POST, CSRF obligatorio. Reinicia
  ambos campos; incluso una cuenta desactivada permanece desactivada. GET →405,
  empleado →403, anónimo →login. Cambiar datos o contraseña no quita el bloqueo.
- Recuperación local de emergencia: `python manage.py desbloquear_usuario USERNAME`
  dentro de web. Requiere acceso autorizado al host/contenedor; no es ruta pública.
- Edición de usuarios y admin conservan el estado de bloqueo bajo el mismo bloqueo
  de fila, para no sobrescribir intentos concurrentes con instancias antiguas.

La protección cubre los dos puntos de login HTTP existentes. Si se añade otro flujo
de login, debe reutilizar estos formularios. No hay proveedor de autenticación paralelo.

### Empleado del mes

Ruta exclusiva del dueño: `/estadisticas/empleado-del-mes/?mes=YYYY-MM`.
Acceso desde Inicio; el empleado recibe 403 por URL directa y no recibe contexto
ni enlace con el ranking. El resto de permisos comerciales se conserva.

Consulta ORM única, sin tabla de estadísticas: filtrar ventas por `fecha` en
`[primer día, primer día del mes siguiente)`, `usuario__rol='empleado'`, agrupar
por usuario y agregar Sum(total), Count(pk). Orden: monto DESC, cantidad DESC,
usuario_id ASC. Se muestran hasta tres puestos y el destacado, importes CLP.
Mes por defecto calculado explícitamente en America/Santiago; formato inválido o
mes futuro muestra error. No hay ventas de empleados → estado vacío, no un ganador
con cero ventas. Inactivos incluidos y etiquetados como históricos.

`fecha` es la fecha **comercial** DateField existente, no `creado_en` reinterpretado
en UTC. No se altera ninguna venta. La exclusión se basa en el rol actual del usuario:
el esquema no almacena un historial de cambios de rol. No se calcula utilidad.

### Filtros GET

| Listado | Parámetros admitidos |
|---|---|
| Productos | `q` nombre, `estado=activo/inactivo`, `disponibilidad=disponible/agotado`, `unidad=kg/unidad` |
| Proveedores | `q` nombre, `estado=activo/inactivo` |
| Ventas | `desde=YYYY-MM-DD`, `hasta=YYYY-MM-DD` inclusivos, `vendedor=<id>` |
| Compras | `desde`, `hasta` inclusivos, `proveedor=<id>` |
| Inventario | Los mismos que productos; filtran existencias, no los últimos 50 movimientos globales |
| Usuarios | `q` nombre/apellidos/usuario, `rol=dueno/empleado`, `estado=activo/inactivo`, `bloqueo=bloqueado/libre` |

Valor vacío significa todos. `page` controla la paginación (30 registros).
Vendedores disponibles: usuarios con ventas, incluidos dueños e inactivos; ambos
roles ya pueden consultar el historial completo. No se muestran correos ni estados
de cuentas en ese selector. Proveedores incluyen inactivos por su historial.

Formularios ChoiceField/DateField/ModelChoiceField validan entradas; lookups ORM
estáticos, nunca SQL concatenado. Fechas invertidas, IDs ajenos al selector y valores
no admitidos muestran errores y lista vacía, no ignoran filtros inválidos.

Una plantilla común `gestion/filtros.html` usa details/summary accesible por teclado.
Inicialmente cerrado; filtros activos/errores lo abren. Indicador externo persiste al
cerrarlo. Abrir/cerrar no hace HTTP, aplicar usa un GET; no requiere JavaScript ni
recargas al alternar el panel. La etiqueta nativa `querystring` de Django conserva
todos los parámetros codificados al paginar. Responsive: grid compacto, una columna
y acciones amplias en móvil; tablas mantienen su scroll interno.

## Migración y protección de datos

Única migración nueva: `usuarios/0002_bloqueo_acceso.py`, dos operaciones AddField.
Sin tablas nuevas, renombres, cambios de roles ni migraciones de datos. Todas las
migraciones previas permanecen byte a byte intactas. La prueba estructural original
solo añade esta migración al conjunto esperado; no se eliminó ningún escenario previo.

Antes de aplicarla se exportó `backups/seguridad-filtros/antes.sql`, 25.182 bytes,
SHA256 `746ddcbe99a496fc2b363c05b60ad9883d43000bc7b0cc5bc2e549b1e5b710f5`.
Respaldo consistente con rutinas, eventos, triggers y datos binarios; restaurado
en **cortegestion_seguridad_verificacion** y comprobados recuentos de las 17 tablas.
Luego se aplicó primero allí la migración y se compararon todas las columnas originales.

Después del arranque real se repitió la comparación mediante huellas de cada tabla
proyectada sobre **todas sus columnas originales**, no solo recuentos: datos idénticos,
incluidos hashes de contraseña, estado administrativo, roles y fechas de usuarios.
`django_migrations` es la única excepción intencionada: una fila nueva (21 →22).
Los nuevos campos de las dos cuentas existentes quedaron en 0/NULL.

| Dato | Antes | Después |
|---|---:|---:|
| Tablas | 17 | 17 |
| Usuarios | 2 | 2 |
| Productos | 2 | 2 |
| Proveedores | 1 | 1 |
| Compras / detalles | 2 / 2 | 2 / 2 |
| Ventas / detalles | 2 / 3 | 2 / 3 |
| Movimientos | 5 | 5 |
| Content types / permisos | 13 / 52 | 13 / 52 |
| Grupos y vinculaciones | 0 | 0 |

Volumen **carniceria_django_mariadb_data** conservado. No se eliminaron volúmenes,
bases ni registros operativos, no se reinicializó MariaDB. SQL, snapshots y secretos
siguen ignorados por Git. El esquema aislado se conserva deliberadamente.

## Operación y actualización

Desde raíz, con Docker Linux iniciado y `.env` existente recuperado privadamente:

1. Guardar y comprobar respaldo **antes del build/up**, porque el arranque aplica migrate.
2. Ensayar el cambio sobre una copia aislada del respaldo, no sobre el esquema operativo.
3. Actualizar la rama feature y ejecutar:

```powershell
git switch feat/seguridad-usuarios-filtros-estadisticas
git pull --ff-only
docker volume inspect carniceria_django_mariadb_data
docker compose config --quiet
docker compose up -d --build --wait
docker compose exec -T web python manage.py check --database default
docker compose exec -T web python manage.py makemigrations --check --dry-run
docker compose exec -T web python manage.py migrate --check
docker compose exec -T web python manage.py showmigrations usuarios
docker compose cp scripts/pruebas_mariadb.sh db:/tmp/pruebas_mariadb.sh
docker compose exec -T db sh /tmp/pruebas_mariadb.sh
docker compose exec -T web python manage.py test --verbosity 2
```

No se ejecuta makemigrations para instalar: la migración está versionada. No cambiar
contraseñas de `.env` al reutilizar una BD ya inicializada. Un clon nuevo usa la misma
secuencia tras `git clone --branch feat/seguridad-usuarios-filtros-estadisticas
https://github.com/LFP2002/corte-gestion.git`. Si el equipo es realmente nuevo y no
tiene datos que recuperar, usar `scripts/instalacion_nueva.ps1` y `crear_dueno`, como
indica README. Si el volumen debía existir y no existe, detenerse y recuperar el respaldo.

Recuperación de una cuenta: Usuarios → Desbloquear cuenta, o comando local de
emergencia del README. La expiración no necesita cron: se evalúa en cada nuevo login.

## Verificación ejecutada

- Baseline 55/55; intermedio 77/77 con seguridad; ranking/filtros específicos 19/19.
- Suite ampliada **96/96, 22,825 s**, imagen reconstruida contra MariaDB real.
- Tras reforzar rutas del admin: **25/25 pruebas específicas de seguridad, 15,393 s**.
- Suite antes de la revisión adicional del CLI, imagen reconstruida sin montaje: **99/99, 25,525 s**:
  55 escenarios anteriores + 44 nuevos, sin omisiones.
- Revisión adicional del CLI: se detectó el bypass estándar de createsuperuser.
  La primera prueba reveló que auth tenía prioridad de descubrimiento del comando;
  se corrigió el orden de registro y las **10 pruebas de credenciales** pasaron.
  Cuatro casos nuevos cubren bypass interactivo, entorno débil/fuerte y contraseña
  inutilizable. Los resultados finales de la suite ampliada se registran en la PR.
- **Suite final: 103/103 pruebas en 25,791 s**, imagen reconstruida sin montaje:
  55 anteriores + 48 nuevas. Check, migraciones sin cambios/pendientes y comparación
  de todos los datos originales repetidos con éxito. Se comprobó explícitamente
  que el registro de comandos descubre `apps.usuarios.management.commands.createsuperuser`.
- Compose config/build/up correctos; check sin problemas, makemigrations sin cambios,
  migrate --check sin pendientes. Instalador Windows: 3 escenarios aprobados;
  prueba estructural PowerShell aprobada.
- Comparación de datos y migraciones descrita arriba, efectivamente ejecutada.
- Microsoft Edge headless/Playwright a **390, 768 y 1280 px**: seis listados y ranking,
  sin desbordamiento de página; paneles por teclado/clic sin recarga; indicador visible
  al cerrar; selecciones y paginación preservadas; empleado no accede al ranking.
- Persistencia real: dos fallos HTTP sobre cuenta sintética **en la copia aislada**,
  reiniciar su contenedor web y ejecutar el tercer fallo; cuenta bloqueada y contraseña
  correcta rechazada. Dueño la desbloquea mediante POST y se recupera el acceso.
  Contenedor temporal retirado, credenciales temporales eliminadas; ninguna cuenta
  de prueba se creó en la base operativa. Capturas permanecen fuera del repositorio.

Publicación de implementación: commit `d712d28`, rama
`feat/seguridad-usuarios-filtros-estadisticas`, creada desde `main`.
PR **borrador**: https://github.com/LFP2002/corte-gestion/pull/4, base `main`, sin merge.

GitHub Actions **aprobado** desde checkout limpio, con construcción de la imagen,
MariaDB real, 99 pruebas, migraciones y Windows:
- Push: https://github.com/LFP2002/corte-gestion/actions/runs/44648373468
  (Linux 1 min 43 s, Windows 11 s).
- PR: https://github.com/LFP2002/corte-gestion/actions/runs/44648428877
  (Linux 1 min 56 s, Windows 10 s).

Los checks de la PR reflejan la ejecución más reciente del último commit publicado.
No hay fallos automatizados conocidos. Continúan pendientes la aprobación humana
y las limitaciones de despliegue público/usabilidad descritas a continuación.

## Actualización y operación desde la raíz

Conservar el `.env` original de forma privada y verificar el volumen externo
`carniceria_django_mariadb_data`. Antes de actualizar una instalación con datos,
obtener y **restaurar para verificar** un respaldo consistente en un esquema aislado,
como se hizo en esta entrega. No generar secretos nuevos para una BD existente.

```powershell
git switch feat/seguridad-usuarios-filtros-estadisticas
git pull --ff-only
docker volume inspect carniceria_django_mariadb_data
docker compose config --quiet
# El arranque aplica la migración aditiva automáticamente: respaldar ANTES.
docker compose up -d --build --wait
docker compose exec -T web python manage.py check --database default
docker compose exec -T web python manage.py makemigrations --check --dry-run
docker compose exec -T web python manage.py migrate --check
docker compose cp scripts/pruebas_mariadb.sh db:/tmp/pruebas_mariadb.sh
docker compose exec -T db sh /tmp/pruebas_mariadb.sh
docker compose exec -T web python manage.py test --verbosity 2
```

Desde un clon limpio:
`git clone --branch feat/seguridad-usuarios-filtros-estadisticas https://github.com/LFP2002/corte-gestion.git`.
Luego entrar a `corte-gestion` y seguir el procedimiento anterior con `.env` y
volumen recuperados de forma privada. En un equipo realmente nuevo, sin datos
previos que recuperar, el instalador de README crea explícitamente el entorno.
No usar una inicialización nueva para restaurar una instalación existente.

La política no cambia contraseñas al desplegar; los dos campos nuevos reciben
valores neutros. No revertir ni borrar columnas para cambiar de rama sin un plan
de despliegue y respaldo: una reversión de esquema perdería el estado de bloqueos.
Detener con `docker compose stop`, nunca eliminar el volumen.

## Riesgos y límites

- Un atacante puede provocar bloqueo conociendo un usuario; no prolongar el bloqueo,
  conservar sesiones y ofrecer recuperación local/administrativa reduce el impacto,
  pero no elimina el riesgo. Para Internet se requiere rate limiting por origen y
  controles perimetrales; no se confía ciegamente en X-Forwarded-For.
- Mensajes genéricos no son una garantía matemática de tiempos idénticos: distintos
  hashes históricos, carga y contención de filas pueden afectar latencia. No se expone
  contador ni vencimiento en el formulario público.
- Los fallos cuentan por cuenta, no por IP; no hay CAPTCHA, MFA, email de recuperación
  ni tareas programadas. No se han añadido dependencias para esas funciones no pedidas.
- Mantener el reloj del servidor sincronizado. No publicar DEBUG/runserver/phpMyAdmin.
- El ranking refleja autoría de ventas y rol actual, no utilidad ni calidad de atención.
- Verificación de navegador automatizada, no estudio de usabilidad con personal/RNF2.

## Árbol de archivos nuevos y modificados

`+` nuevo, `~` modificado; no se eliminan archivos de aplicación.

```text
~ .github/workflows/ci.yml
~ README.md
backend/
  apps/
    gestion/
      + filters.py
      + statistics.py
      ~ views.py
      templatetags/~ navegacion.py
      tests/
        + test_estadisticas.py
        + test_filtros.py
        ~ test_estructura.py
    usuarios/
      ~ admin.py
      + authentication.py
      + filters.py
      ~ forms.py
      ~ models.py
      ~ urls.py
      + validators.py
      ~ views.py
      management/commands/+ desbloquear_usuario.py
      management/commands/+ createsuperuser.py
      migrations/+ 0002_bloqueo_acceso.py
      tests/+ test_seguridad_cuentas.py
  config/~ settings.py
  docs/+ SEGURIDAD_ESTADISTICAS_FILTROS.md
  static/css/~ style.css
  templates/
    gestion/
      ~ catalogo.html
      + filtros.html
      ~ operaciones.html
      ~ paginacion.html
      ~ stock.html
    usuarios/
      + empleado_mes.html
      ~ inicio.html
      ~ lista.html
```
