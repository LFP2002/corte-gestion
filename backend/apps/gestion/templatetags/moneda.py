"""Formateo exclusivamente visual de importes en pesos chilenos.

No cambia importes en base de datos ni redondea operaciones comerciales.
Conserva centavos cuando el valor almacenado los contiene.
"""
from decimal import Decimal, InvalidOperation

from django import template


register = template.Library()


@register.filter
def clp(valor):
    """8000.00 -> $8.000; 1234.50 -> $1.234,50."""
    if valor is None or valor == '':
        return '—'
    try:
        numero = Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError):
        return '—'
    if not numero.is_finite():
        return '—'
    signo = '-' if numero < 0 else ''
    numero = abs(numero)
    entero = int(numero)
    miles = f'{entero:,}'.replace(',', '.')
    centavos = int((numero - entero) * 100)
    # Los importes monetarios se guardan como Decimal(..., 2).
    if centavos:
        return f'{signo}${miles},{centavos:02d}'
    return f'{signo}${miles}'
