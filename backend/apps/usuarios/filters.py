from django import forms
from django.db.models import Q
from django.utils import timezone

from apps.gestion.filters import ESTADOS, FiltroForm
from .models import Usuario


class UsuarioFiltro(FiltroForm):
    q = forms.CharField(label='Nombre o usuario', required=False, max_length=150,
                        widget=forms.TextInput(attrs={'type': 'search'}))
    rol = forms.ChoiceField(label='Rol', required=False, choices=[('', 'Todos')] + Usuario.ROLES)
    estado = forms.ChoiceField(label='Estado administrativo', required=False, choices=ESTADOS)
    bloqueo = forms.ChoiceField(label='Bloqueo temporal', required=False,
                               choices=[('', 'Todos'), ('bloqueado', 'Bloqueados'), ('libre', 'Sin bloqueo vigente')])

    def _filtrar(self, queryset):
        datos = self.cleaned_data
        if datos['q']:
            queryset = queryset.filter(Q(username__icontains=datos['q']) |
                                       Q(first_name__icontains=datos['q']) | Q(last_name__icontains=datos['q']))
        if datos['rol']:
            queryset = queryset.filter(rol=datos['rol'])
        if datos['estado']:
            queryset = queryset.filter(is_active=datos['estado'] == 'activo')
        if datos['bloqueo'] == 'bloqueado':
            queryset = queryset.filter(bloqueo_hasta__gt=timezone.now())
        elif datos['bloqueo'] == 'libre':
            queryset = queryset.exclude(bloqueo_hasta__gt=timezone.now())
        return queryset
