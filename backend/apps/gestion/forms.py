from django import forms
from django.forms import BaseFormSet, formset_factory
from django.utils import timezone

from .models import Compra, DetalleCompra, Producto, Proveedor, Venta


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['nombre', 'unidad', 'precio_venta', 'activo']
        labels = {'precio_venta': 'Precio de venta por kg / unidad'}

    def clean_unidad(self):
        unidad = self.cleaned_data['unidad']
        if self.instance.pk and self.instance.movimientos.exists():
            anterior = Producto.objects.get(pk=self.instance.pk)
            if unidad != anterior.unidad:
                raise forms.ValidationError('No cambie la unidad de un producto con historial.')
        return unidad


class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = ['nombre', 'rut', 'telefono', 'email', 'activo']


class CompraForm(forms.ModelForm):
    class Meta:
        model = Compra
        fields = ['proveedor', 'fecha', 'referencia']
        widgets = {'fecha': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['proveedor'].queryset = Proveedor.objects.filter(activo=True)


class VentaForm(forms.ModelForm):
    class Meta:
        model = Venta
        fields = ['fecha']
        widgets = {'fecha': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'})}


class LineaForm(forms.ModelForm):
    class Meta:
        model = DetalleCompra
        fields = ['producto', 'cantidad', 'precio_unitario']
        labels = {'precio_unitario': 'Precio por kg / unidad'}
        widgets = {
            'cantidad': forms.TextInput(attrs={'inputmode': 'decimal', 'placeholder': 'Ej.: 2,5'}),
            'precio_unitario': forms.TextInput(attrs={'inputmode': 'decimal'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['producto'].queryset = Producto.objects.filter(activo=True)
        self.fields['cantidad'].localize = True
        self.fields['precio_unitario'].localize = True


class LineasBase(BaseFormSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.productos = list(Producto.objects.filter(activo=True))
        opciones = [('', '---------')] + [(p.pk, f'{p.nombre} ({p.unidad}) — Stock: {p.stock}') for p in self.productos]
        for form in self.forms:
            form.fields['producto'].choices = opciones
        self.opciones_producto = opciones

    @property
    def empty_form(self):
        form = super().empty_form
        form.fields['producto'].choices = self.opciones_producto
        return form

    def clean(self):
        if any(self.errors):
            return
        ids = [f.cleaned_data['producto'].pk for f in self.forms if f.cleaned_data and not f.cleaned_data.get('DELETE')]
        if len(ids) != len(set(ids)):
            raise forms.ValidationError('No repita productos: use una sola línea por producto.')


LineasFormSet = formset_factory(LineaForm, formset=LineasBase, extra=1, min_num=1,
                               validate_min=True, max_num=100, validate_max=True,
                               absolute_max=100, can_delete=True)


class PeriodoForm(forms.Form):
    periodo = forms.ChoiceField(choices=[('semana', 'Semana (lunes a domingo)'), ('mes', 'Mes calendario')], initial='semana')
    fecha = forms.DateField(label='Fecha dentro del período', initial=timezone.localdate,
                           widget=forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}))
