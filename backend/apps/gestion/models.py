from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Producto(models.Model):
    nombre = models.CharField(max_length=120, unique=True)
    unidad = models.CharField(max_length=10, choices=[('kg', 'Kilogramos'), ('unidad', 'Unidad')], default='kg')
    precio_venta = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    stock = models.DecimalField(max_digits=12, decimal_places=3, default=0, editable=False)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['nombre']
        constraints = [
            models.CheckConstraint(condition=models.Q(stock__gte=0), name='producto_stock_no_negativo'),
            models.CheckConstraint(condition=models.Q(precio_venta__gt=0), name='producto_precio_positivo'),
        ]

    def __str__(self):
        return f'{self.nombre} ({self.unidad})'


class Proveedor(models.Model):
    nombre = models.CharField(max_length=150, unique=True)
    rut = models.CharField('RUT / identificación', max_length=30, blank=True)
    telefono = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Operacion(models.Model):
    fecha = models.DateField(default=timezone.localdate, db_index=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    total = models.DecimalField(max_digits=16, decimal_places=2, editable=False)

    class Meta:
        abstract = True
        ordering = ['-fecha', '-pk']


class Compra(Operacion):
    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT, related_name='compras')
    referencia = models.CharField('Documento de compra (opcional)', max_length=100, blank=True)

    class Meta(Operacion.Meta):
        abstract = False
        constraints = [models.CheckConstraint(condition=models.Q(total__gt=0), name='compra_total_positivo')]


class DetalleBase(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.DecimalField(max_digits=12, decimal_places=3, validators=[MinValueValidator(Decimal('0.001'))])
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    subtotal = models.DecimalField(max_digits=16, decimal_places=2, editable=False)

    class Meta:
        abstract = True


class DetalleCompra(DetalleBase):
    compra = models.ForeignKey(Compra, on_delete=models.PROTECT, related_name='detalles')

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(cantidad__gt=0), name='detalle_compra_cantidad_positiva'),
            models.CheckConstraint(condition=models.Q(precio_unitario__gt=0), name='detalle_compra_precio_positivo'),
            models.CheckConstraint(condition=models.Q(subtotal__gt=0), name='detalle_compra_subtotal_positivo'),
            models.UniqueConstraint(fields=['compra', 'producto'], name='compra_producto_unico'),
        ]


class Venta(Operacion):
    class Meta(Operacion.Meta):
        abstract = False
        constraints = [models.CheckConstraint(condition=models.Q(total__gt=0), name='venta_total_positivo')]


class DetalleVenta(DetalleBase):
    venta = models.ForeignKey(Venta, on_delete=models.PROTECT, related_name='detalles')

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(cantidad__gt=0), name='detalle_venta_cantidad_positiva'),
            models.CheckConstraint(condition=models.Q(precio_unitario__gt=0), name='detalle_venta_precio_positivo'),
            models.CheckConstraint(condition=models.Q(subtotal__gt=0), name='detalle_venta_subtotal_positivo'),
            models.UniqueConstraint(fields=['venta', 'producto'], name='venta_producto_unico'),
        ]


class MovimientoStock(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name='movimientos')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    creado_en = models.DateTimeField(auto_now_add=True)
    cantidad = models.DecimalField(max_digits=12, decimal_places=3)
    saldo = models.DecimalField(max_digits=12, decimal_places=3)
    detalle_compra = models.OneToOneField(DetalleCompra, on_delete=models.PROTECT, null=True, blank=True)
    detalle_venta = models.OneToOneField(DetalleVenta, on_delete=models.PROTECT, null=True, blank=True)

    class Meta:
        ordering = ['-pk']
        constraints = [
            models.CheckConstraint(condition=models.Q(saldo__gte=0), name='movimiento_saldo_no_negativo'),
            models.CheckConstraint(condition=(
                models.Q(detalle_compra__isnull=False, detalle_venta__isnull=True, cantidad__gt=0)
                | models.Q(detalle_compra__isnull=True, detalle_venta__isnull=False, cantidad__lt=0)
            ), name='movimiento_origen_y_signo'),
        ]
