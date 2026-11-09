# CorteGestión — Verificación ejecutada

Fecha: 8 de noviembre de 2026. Windows, Docker Desktop con motor Linux.
Imagen web Python 3.12, Django 5.2.19 y mysqlclient 2.2.8; servidor MariaDB 11.4.
No se usó SQLite ni un sustituto de MariaDB.

## Por fases

1. **Auditoría / infraestructura**: revisión de fuentes originales y migración de
   Usuario; `docker version`, `docker compose config --quiet`, construcción real
   de imagen (mysqlclient compilado correctamente), arranque de los tres servicios.
   No hay Git: no se creó rama. Se conserva el entorno `.venv` anterior sin modificarlo.
2. **Conexión / autenticación**: migraciones originales aplicadas a MariaDB; 6
   pruebas iniciales ejecutadas y aprobadas, incluidas alta segura y ruta pública cerrada.
3. **Productos / proveedores / compras**: 16 pruebas acumuladas aprobadas, incluidas
   compra de 12 kg, CRUD y rollback después de una escritura de stock.
4. **Ventas / stock**: 24 pruebas acumuladas aprobadas; venta de 2,5 kg deja 9,5 kg,
   totales, varias líneas, stock insuficiente y reversión de fallos.
5. **Reportes / interfaz / pruebas**: suite completa de **38 pruebas aprobadas**
   contra MariaDB. Incluye semana/mes, límites de calendario, permisos, CSRF,
   páginas del dueño, desactivación del último dueño y prueba concurrente con
   conexiones independientes (dos ventas de 8 kg sobre 12 kg: solo una confirma).

## Comandos y resultados

```powershell
docker compose run --rm --no-deps -v "${PWD}:/app" web python manage.py test --verbosity 2
# Ran 38 tests in 6.053s — OK
docker compose run --rm --no-deps -v "${PWD}:/app" web python manage.py makemigrations --check --dry-run
# No changes detected
docker compose exec web python manage.py check --database default
# System check identified no issues (0 silenced).
docker compose exec web python manage.py showmigrations
# Todas aplicadas, incluidas usuarios.0001 y gestion.0001 / 0002.
```

Se reconstruyó y levantó la imagen final, se ejecutaron también las pruebas desde
la imagen sin montar código local y se verificó el healthcheck HTTP de `web`.
El acceso HTTP desde Windows a `/login/`, `/static/style.css` y phpMyAdmin respondió 200.
El procedimiento documentado para conceder permisos de pruebas mediante
`docker compose cp` + `sh` también se ejecutó correctamente.

## Persistencia real del volumen

Se creó exclusivamente un proveedor marcador de prueba en la base de aplicación;
se ejecutó `docker compose down` **sin -v** y después `docker compose up -d --wait`.
El proveedor permaneció con el mismo ID al recrear contenedores. Se retiró únicamente
ese marcador creado para la prueba. Se verificó que no quedaron usuarios de prueba
en la base real. Los registros comerciales de las pruebas unitarias se crearon en
`test_carniceria`, destruida normalmente por el runner Django.

No se crearon cuentas operativas: el usuario debe ejecutar `crear_dueno` e ingresar
sus propias credenciales. El `.env` local se generó con secretos aleatorios y está
excluido de Git y del contexto de construcción. Los servicios quedaron levantados.

## Medición informativa de RNF2

Cliente de pruebas Django, MariaDB real por red Docker, POSTs completos sin seguir
la redirección de respuesta, cinco repeticiones por caso, sin simular tiempo humano:

| Operación | Líneas | Mediana | Máximo |
|---|---:|---:|---:|
| Compra | 1 | 9,2 ms | 19,9 ms |
| Venta | 1 | 7,9 ms | 8,2 ms |
| Compra | 5 | 22,7 ms | 22,9 ms |
| Venta | 5 | 21,8 ms | 21,9 ms |
| Compra | 20 | 72,9 ms | 79,6 ms |
| Venta | 20 | 71,1 ms | 76,2 ms |

Son resultados de una ejecución local, no un SLA ni evidencia suficiente para
declarar cumplido RNF2. No incluyen renderizado de navegador, digitación, interacción
con clientes del negocio, red externa ni carga de producción.

### Validación manual pendiente

- Recorrer el flujo del README en navegador, verificar apariencia en móvil y teclado,
  agregar/eliminar líneas con JavaScript y confirmar importes visibles.
- Iniciar sesión en phpMyAdmin con las credenciales locales y observar las tablas
  de la demostración. Se verificó su respuesta HTTP, no una sesión interactiva en su GUI.
- Medir con dueño/empleado tiempo desde apertura hasta confirmación de una compra
  y una venta, con 1, 5 y 20 líneas, al menos 10 repeticiones; registrar errores,
  mediana, percentil 95 e interrupciones al atender clientes.
- Usar el umbral que establezca el informe original; no fue proporcionado un umbral
  numérico. No se modificó el RNF2 ni se inventó una aceptación cuantitativa.

No hay fallos automatizados pendientes conocidos. No se auditó/importó la antigua
BD XAMPP ni se realizó despliegue de producción, prueba de carga sostenida o auditoría
de seguridad externa. Esas actividades no se declaran realizadas.
