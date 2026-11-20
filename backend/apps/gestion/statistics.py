"""Estadísticas de lectura sobre la fecha comercial de las ventas."""
from datetime import date
from zoneinfo import ZoneInfo

from django import forms
from django.db.models import Count, Sum
from django.utils import timezone

from .models import Venta


def mes_actual():
    return timezone.localdate(timezone.now(), ZoneInfo('America/Santiago')).replace(day=1)


class MesForm(forms.Form):
    mes = forms.DateField(label='Mes', input_formats=['%Y-%m'],
                         widget=forms.DateInput(format='%Y-%m', attrs={'type': 'month'}))

    def clean_mes(self):
        mes = self.cleaned_data['mes'].replace(day=1)
        if mes > mes_actual():
            raise forms.ValidationError('Selecciona el mes actual o uno anterior.')
        return mes


def ranking_empleados(mes):
    fin = date(mes.year + (mes.month == 12), mes.month % 12 + 1, 1)
    return (Venta.objects.filter(fecha__gte=mes, fecha__lt=fin, usuario__rol='empleado')
            .values('usuario_id', 'usuario__first_name', 'usuario__last_name',
                    'usuario__username', 'usuario__is_active')
            .annotate(total_vendido=Sum('total'), cantidad_ventas=Count('pk'))
            .order_by('-total_vendido', '-cantidad_ventas', 'usuario_id'))
