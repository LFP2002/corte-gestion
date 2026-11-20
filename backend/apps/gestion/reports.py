"""Consultas agregadas por períodos calendario, sin cargar detalles en Python."""
from datetime import timedelta

from django.db.models import DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce

from .models import DetalleVenta, Proveedor


def limites_periodo(fecha, periodo):
    if periodo == 'semana':
        inicio = fecha - timedelta(days=fecha.weekday())
        return inicio, inicio + timedelta(days=7)
    inicio = fecha.replace(day=1)
    fin = (inicio + timedelta(days=32)).replace(day=1)
    return inicio, fin


def compras_por_proveedor(inicio, fin):
    return Proveedor.objects.annotate(total_comprado=Coalesce(
        Sum('compras__total', filter=Q(compras__fecha__gte=inicio, compras__fecha__lt=fin)),
        Value(0), output_field=DecimalField(max_digits=16, decimal_places=2),
    )).order_by('-total_comprado', 'nombre')


def productos_mas_vendidos(inicio, fin):
    return (DetalleVenta.objects.filter(venta__fecha__gte=inicio, venta__fecha__lt=fin)
            .values('producto_id', 'producto__nombre', 'producto__unidad')
            .annotate(cantidad_vendida=Sum('cantidad'), total_vendido=Sum('subtotal'))
            .order_by('-cantidad_vendida', 'producto__nombre'))
