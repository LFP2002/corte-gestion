"""Filtros GET validados: ninguna entrada del usuario se usa como nombre de lookup."""
from django import forms

from apps.usuarios.models import Usuario
from .models import Proveedor


ESTADOS = [('', 'Todos'), ('activo', 'Activo'), ('inactivo', 'Inactivo')]
DISPONIBILIDAD = [('', 'Todas'), ('disponible', 'Con existencias'), ('agotado', 'Agotado')]


class FiltroForm(forms.Form):
    @property
    def cantidad_activos(self):
        if self.is_valid():
            return sum(bool(self.cleaned_data.get(name)) for name in self.fields)
        return sum(bool(self.data.get(name)) for name in self.fields)

    def filtrar(self, queryset):
        # No convertir filtros inválidos en un listado global silenciosamente.
        return self._filtrar(queryset) if self.is_valid() else queryset.none()

    def _filtrar(self, queryset):
        return queryset


class NombreEstadoFiltro(FiltroForm):
    q = forms.CharField(label='Buscar por nombre', required=False, max_length=150,
                        widget=forms.TextInput(attrs={'type': 'search'}))
    estado = forms.ChoiceField(label='Estado', choices=ESTADOS, required=False)

    def _filtrar(self, queryset):
        datos = self.cleaned_data
        if datos['q']:
            queryset = queryset.filter(nombre__icontains=datos['q'])
        if datos['estado']:
            queryset = queryset.filter(activo=datos['estado'] == 'activo')
        return queryset


class ProductoFiltro(NombreEstadoFiltro):
    disponibilidad = forms.ChoiceField(label='Stock', choices=DISPONIBILIDAD, required=False)
    unidad = forms.ChoiceField(label='Unidad', choices=[('', 'Todas'), ('kg', 'Kilogramos'),
                                                     ('unidad', 'Unidad')], required=False)

    def _filtrar(self, queryset):
        queryset = super()._filtrar(queryset)
        if self.cleaned_data['disponibilidad'] == 'agotado':
            queryset = queryset.filter(stock=0)
        elif self.cleaned_data['disponibilidad'] == 'disponible':
            queryset = queryset.filter(stock__gt=0)
        if self.cleaned_data['unidad']:
            queryset = queryset.filter(unidad=self.cleaned_data['unidad'])
        return queryset


class FechasFiltro(FiltroForm):
    desde = forms.DateField(label='Desde', required=False, input_formats=['%Y-%m-%d'],
                           widget=forms.DateInput(attrs={'type': 'date'}))
    hasta = forms.DateField(label='Hasta', required=False, input_formats=['%Y-%m-%d'],
                           widget=forms.DateInput(attrs={'type': 'date'}))

    def clean(self):
        datos = super().clean()
        if datos.get('desde') and datos.get('hasta') and datos['desde'] > datos['hasta']:
            raise forms.ValidationError('La fecha inicial no puede ser posterior a la final.')
        return datos

    def _filtrar(self, queryset):
        if self.cleaned_data['desde']:
            queryset = queryset.filter(fecha__gte=self.cleaned_data['desde'])
        if self.cleaned_data['hasta']:
            queryset = queryset.filter(fecha__lte=self.cleaned_data['hasta'])
        return queryset


class VentaFiltro(FechasFiltro):
    vendedor = forms.ModelChoiceField(label='Vendedor', required=False, empty_label='Todos',
                                      queryset=Usuario.objects.none())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # El historial global ya es consultable por ambos roles; incluir vendedores
        # históricos, inactivos y dueños sin revelar sus correos ni otros atributos.
        self.fields['vendedor'].queryset = Usuario.objects.filter(venta__isnull=False).distinct().order_by('username')

    def _filtrar(self, queryset):
        queryset = super()._filtrar(queryset)
        if self.cleaned_data['vendedor']:
            queryset = queryset.filter(usuario=self.cleaned_data['vendedor'])
        return queryset


class CompraFiltro(FechasFiltro):
    proveedor = forms.ModelChoiceField(label='Proveedor', required=False, empty_label='Todos',
                                       queryset=Proveedor.objects.all())

    def _filtrar(self, queryset):
        queryset = super()._filtrar(queryset)
        if self.cleaned_data['proveedor']:
            queryset = queryset.filter(proveedor=self.cleaned_data['proveedor'])
        return queryset
