"""Único punto de escritura de operaciones confirmadas e inventario.

No se usan señales: cabecera, detalles, stock y movimientos se confirman juntos.
Los precios/total enviados por el navegador nunca sustituyen el cálculo del servidor.
"""
from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from .models import Compra, DetalleCompra, DetalleVenta, MovimientoStock, Producto, Proveedor, Venta

CENTAVO = Decimal('0.01')


def validar_usuario(usuario, solo_dueno=False):
    if not usuario.is_authenticated or not usuario.is_active or usuario.rol not in ('dueno', 'empleado'):
        raise PermissionDenied
    if solo_dueno and not usuario.es_dueno:
        raise PermissionDenied


def preparar_lineas(lineas):
    if not lineas or len(lineas) > 100:
        raise ValidationError('Debe indicar entre 1 y 100 productos.')
    preparadas = []
    ids = set()
    for linea in lineas:
        detalle = DetalleCompra(
            producto=linea['producto'], cantidad=linea['cantidad'],
            precio_unitario=linea['precio_unitario'],
        )
        # Validación de precisión, límites y positividad también para invocaciones
        # desde comandos o código Python (no solo desde ModelForms).
        for campo in ('cantidad', 'precio_unitario'):
            setattr(detalle, campo, detalle._meta.get_field(campo).clean(getattr(detalle, campo), detalle))
        if detalle.producto_id in ids:
            raise ValidationError('No repita productos: reúna la cantidad en una línea.')
        ids.add(detalle.producto_id)
        subtotal = (detalle.cantidad * detalle.precio_unitario).quantize(CENTAVO, rounding=ROUND_HALF_UP)
        if subtotal <= 0:
            raise ValidationError('El subtotal debe ser al menos 0,01.')
        detalle._meta.get_field('subtotal').clean(subtotal, detalle)
        preparadas.append((detalle.producto_id, detalle.cantidad, detalle.precio_unitario, subtotal))
    return preparadas


def bloquear_productos(lineas):
    ids = [linea[0] for linea in lineas]
    productos = {p.pk: p for p in Producto.objects.select_for_update().filter(pk__in=ids).order_by('pk')}
    if len(productos) != len(ids) or any(not p.activo for p in productos.values()):
        raise ValidationError('Uno de los productos ya no está disponible.')
    return productos


@transaction.atomic
def registrar_compra(*, usuario, proveedor, fecha, lineas, referencia=''):
    validar_usuario(usuario, solo_dueno=True)
    proveedor = Proveedor.objects.select_for_update().get(pk=proveedor.pk)
    if not proveedor.activo:
        raise ValidationError('El proveedor está inactivo.')
    lineas = preparar_lineas(lineas)
    productos = bloquear_productos(lineas)
    compra = Compra(usuario=usuario, proveedor=proveedor, fecha=fecha, referencia=referencia,
                    total=sum(linea[3] for linea in lineas))
    compra.full_clean()
    compra.save()
    for pk, cantidad, precio, subtotal in lineas:
        producto = productos[pk]
        detalle = DetalleCompra.objects.create(compra=compra, producto=producto, cantidad=cantidad,
                                               precio_unitario=precio, subtotal=subtotal)
        producto.stock += cantidad
        Producto._meta.get_field('stock').clean(producto.stock, producto)
        producto.save(update_fields=['stock'])
        MovimientoStock.objects.create(producto=producto, usuario=usuario, cantidad=cantidad,
                                      saldo=producto.stock, detalle_compra=detalle)
    return compra


@transaction.atomic
def registrar_venta(*, usuario, fecha, lineas):
    validar_usuario(usuario)
    lineas = preparar_lineas(lineas)
    productos = bloquear_productos(lineas)
    for pk, cantidad, _, _ in lineas:
        if productos[pk].stock < cantidad:
            raise ValidationError(f'Stock insuficiente para {productos[pk].nombre}: disponible {productos[pk].stock}.')
    venta = Venta(usuario=usuario, fecha=fecha, total=sum(linea[3] for linea in lineas))
    venta.full_clean()
    venta.save()
    for pk, cantidad, precio, subtotal in lineas:
        producto = productos[pk]
        detalle = DetalleVenta.objects.create(venta=venta, producto=producto, cantidad=cantidad,
                                              precio_unitario=precio, subtotal=subtotal)
        producto.stock -= cantidad
        producto.save(update_fields=['stock'])
        MovimientoStock.objects.create(producto=producto, usuario=usuario, cantidad=-cantidad,
                                      saldo=producto.stock, detalle_venta=detalle)
    return venta
