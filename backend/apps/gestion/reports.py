"""Consultas agregadas por períodos calendario, sin cargar detalles en Python."""
from datetime import timedelta

from django.db.models import Count, DecimalField, Max, OuterRef, Q, Subquery, Sum, Value
from django.db.models.functions import Coalesce

from .models import DetalleCompra, DetalleVenta, Proveedor


def limites_periodo(fecha, periodo):
    if periodo == 'semana':
        inicio = fecha - timedelta(days=fecha.weekday())
        return inicio, inicio + timedelta(days=7)
    inicio = fecha.replace(day=1)
    fin = (inicio + timedelta(days=32)).replace(day=1)
    return inicio, fin


def compras_por_proveedor(inicio, fin):
    periodo = Q(compras__fecha__gte=inicio, compras__fecha__lt=fin)
    # Comparar importes permite ordenar productos de distintas unidades (kg/unidad)
    # sin mezclar cantidades incompatibles. Desempate estable por nombre y PK.
    principal = (DetalleCompra.objects.filter(
        compra__proveedor_id=OuterRef('pk'),
        compra__fecha__gte=inicio, compra__fecha__lt=fin,
    ).order_by().values('producto_id', 'producto__nombre')
        .annotate(importe=Sum('subtotal'))
        .order_by('-importe', 'producto__nombre', 'producto_id')
        .values('producto__nombre')[:1])
    return Proveedor.objects.annotate(
        total_comprado=Coalesce(
            Sum('compras__total', filter=periodo),
            Value(0), output_field=DecimalField(max_digits=16, decimal_places=2),
        ),
        cantidad_compras=Count('compras', filter=periodo),
        ultima_compra=Max('compras__fecha', filter=periodo),
        producto_destacado=Subquery(principal),
    ).order_by('-total_comprado', 'nombre')


def productos_mas_vendidos(inicio, fin):
    return (DetalleVenta.objects.filter(venta__fecha__gte=inicio, venta__fecha__lt=fin)
            .values('producto_id', 'producto__nombre', 'producto__unidad')
            .annotate(cantidad_vendida=Sum('cantidad'), total_vendido=Sum('subtotal'))
            .order_by('-cantidad_vendida', 'producto__nombre'))
