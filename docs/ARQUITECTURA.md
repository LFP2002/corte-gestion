# CorteGestión — Modelo de datos y decisiones

**Sistema de Gestión para Carnicerías**. La identidad Compose es `corte-gestion`;
se conserva el volumen externo `carniceria_django_mariadb_data`, sin renombrar la
base ni las apps internas. Procedimiento y respaldo: `CAMBIO_IDENTIDAD.md`.

```text
Usuario 1 ── N Compra N ── 1 Proveedor
Compra 1 ── N DetalleCompra N ── 1 Producto
Usuario 1 ── N Venta
Venta 1 ── N DetalleVenta N ── 1 Producto
DetalleCompra 1 ── 1 MovimientoStock (entrada positiva)
DetalleVenta  1 ── 1 MovimientoStock (salida negativa)
Producto 1 ── N MovimientoStock N ── 1 Usuario
```

## Datos

- **Usuario**: `AbstractUser` existente, email único, rol dueño/empleado. Se conserva
  su tabla y migración inicial; ninguna conversión de modelo de autenticación.
- **Producto**: nombre único, unidad (`kg` / `unidad`), precio de venta positivo,
  stock decimal no editable en formularios y bandera activo. La unidad queda fija
  después del primer movimiento para no reinterpretar cantidades históricas.
- **Proveedor**: nombre único, identificación/RUT libre, contacto y activo. No se
  implementa validación tributaria ni factura electrónica.
- **Compra/Venta**: fecha comercial indexada, instante de creación, usuario protegido,
  total calculado por servidor; compra agrega proveedor y referencia documental.
- **Detalles**: cantidad `Decimal(12,3)`, precio `Decimal(12,2)`, subtotal `Decimal(16,2)`.
  Una línea por producto y operación, FK protegidas. Precio histórico no depende del
  precio actual del catálogo. Nombre del producto/proveedor se consulta desde su catálogo.
- **MovimientoStock**: fecha de registro, usuario, producto, cantidad con signo y
  saldo posterior; exactamente un origen compra/venta, único por detalle. Restricción
  SQL asegura que origen y signo coincidan y saldo no sea negativo.

El stock parte en cero. No se modifica desde CRUD, no hay ajuste manual ni importación
de stock inicial oculta. Una existencia inicial se registra mediante una compra.
Unidad es una etiqueta de medida; la precisión de cantidades es la misma para todos
los productos. No hay conversiones entre unidades ni sumas globales de kg y unidades.
Los reportes muestran la unidad; una comparación entre unidades distintas no tiene
significado físico aunque el ranking numérico se presente ordenado como pide RF4.

## Transacciones

`registrar_compra` y `registrar_venta` son los puntos de escritura comerciales.
Comprueban rol/actividad, precisión, productos duplicados e importes positivos.
Bloquean productos con `SELECT ... FOR UPDATE` en orden estable de PK; la compra
también bloquea su proveedor. Una venta verifica stock **después de obtener el bloqueo**.
Se ejecutan cabecera, detalles, actualización y movimientos dentro de `transaction.atomic`.
Cualquier error revierte todo. El CRUD de productos utiliza el mismo bloqueo al editar
y conserva el stock leído bajo bloqueo, sin sobrescribirlo con una instancia vieja.

MariaDB utiliza InnoDB, `utf8mb4`, modo estricto y aislamiento READ COMMITTED.
Los bloqueos se mantienen hasta commit. No se usan señales ni actualizaciones desde JS.
La suite prueba dos ventas de 8 kg concurrentes sobre 12 kg: solo una se confirma.

Cada subtotal se redondea a dos decimales con `ROUND_HALF_UP`; total es la suma de
subtotales redondeados. Se rechazan líneas que redondean a cero y valores fuera de
precisión. Las restricciones SQL refuerzan las validaciones de formularios/servicios.
No se ofrece edición ni borrado de operaciones confirmadas. `PROTECT` evita borrar
accidentalmente productos, proveedores, usuarios, cabeceras o detalles referenciados.
Un administrador de BD puede eludir reglas de aplicación: phpMyAdmin es de consulta
para la demostración, no un editor de stock.

## Períodos

Reportes basados en la **fecha comercial**, no la fecha técnica de inserción.
Semana lunes–domingo y mes calendario de la fecha elegida, intervalo SQL `[inicio, fin)`.
RF2 agrega compras por proveedor, incluyendo proveedores sin compras con total cero.
RF4 agrega cantidades vendidas por producto, orden descendente y nombre como desempate.
No hay borradores que excluir: todas las operaciones persistidas están confirmadas.

## Seguridad y despliegue

Credenciales solo por entorno; `.env` excluido de imagen y control de versiones.
Puertos web/phpMyAdmin ligados a loopback; BD solo en red interna. Root se reserva
para mantenimiento; Django usa su cuenta de base limitada al esquema de aplicación
y, después de habilitar pruebas, al esquema de test. No se conceden privilegios globales.

El comando de primer dueño usa GET_LOCK de MariaDB para serializar incluso una BD
vacía, validación Django e ingreso oculto de contraseña. No hay ruta de autoalta.
CRUD de usuarios serializa las comprobaciones del último dueño activo mediante
bloqueo de filas. Cambios de contraseña pasan validadores y `set_password`.

Compose y el servidor Django son intencionalmente de desarrollo. No hay Celery,
API REST ni frontend adicional: no son necesarios para el alcance académico.
