from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .forms import CompraForm, LineasFormSet, PeriodoForm, ProductoForm, ProveedorForm, VentaForm
from .models import Compra, MovimientoStock, Producto, Proveedor, Venta
from .services import registrar_compra, registrar_venta, validar_usuario
from .reports import compras_por_proveedor, limites_periodo, productos_mas_vendidos
from django.utils import timezone
from datetime import timedelta


CATALOGOS = {
    'productos': (Producto, ProductoForm, 'Productos'),
    'proveedores': (Proveedor, ProveedorForm, 'Proveedores'),
}


@login_required
def catalogo(request, tipo):
    validar_usuario(request.user, solo_dueno=tipo == 'proveedores')
    modelo, _, titulo = CATALOGOS[tipo]
    objetos = modelo.objects.all()
    if request.GET.get('q'):
        objetos = objetos.filter(nombre__icontains=request.GET['q'])
    pagina = Paginator(objetos, 30).get_page(request.GET.get('page'))
    return render(request, 'gestion/catalogo.html', {'objetos': pagina, 'tipo': tipo, 'titulo': titulo})


@login_required
@require_http_methods(['GET', 'POST'])
def catalogo_form(request, tipo, pk=None):
    validar_usuario(request.user, solo_dueno=True)
    modelo, formulario, titulo = CATALOGOS[tipo]
    objeto = get_object_or_404(modelo, pk=pk) if pk else None
    form = formulario(request.POST or None, instance=objeto)
    if request.method == 'POST' and form.is_valid():
        # Mismo bloqueo de producto utilizado por compras/ventas.
        with transaction.atomic():
            if objeto:
                bloqueado = modelo.objects.select_for_update().get(pk=pk)
                if tipo == 'productos':
                    form.instance.stock = bloqueado.stock
                if tipo == 'productos' and bloqueado.movimientos.exists() and form.cleaned_data['unidad'] != bloqueado.unidad:
                    form.add_error('unidad', 'No cambie la unidad de un producto con historial.')
                    return render(request, 'gestion/form.html', {'form': form, 'titulo': titulo, 'tipo': tipo})
            form.save()
        messages.success(request, 'Registro guardado.')
        return redirect('gestion:catalogo', tipo=tipo)
    return render(request, 'gestion/form.html', {'form': form, 'titulo': titulo, 'tipo': tipo})


@login_required
@require_http_methods(['GET', 'POST'])
def catalogo_eliminar(request, tipo, pk):
    validar_usuario(request.user, solo_dueno=True)
    modelo, _, _ = CATALOGOS[tipo]
    objeto = get_object_or_404(modelo, pk=pk)
    if request.method == 'POST':
        try:
            with transaction.atomic():
                modelo.objects.select_for_update().get(pk=pk).delete()
            messages.success(request, 'Registro eliminado.')
        except ProtectedError:
            messages.error(request, 'Tiene historial: no se puede eliminar. Puede marcarlo como inactivo al editar.')
        return redirect('gestion:catalogo', tipo=tipo)
    return render(request, 'gestion/eliminar.html', {'object': objeto, 'tipo': tipo})


@login_required
def compras(request):
    validar_usuario(request.user, solo_dueno=True)
    pagina = Paginator(Compra.objects.select_related('proveedor', 'usuario'), 30).get_page(request.GET.get('page'))
    return render(request, 'gestion/operaciones.html', {'objetos': pagina, 'tipo': 'compra'})


@login_required
@require_http_methods(['GET', 'POST'])
def compra_crear(request):
    validar_usuario(request.user, solo_dueno=True)
    form = CompraForm(request.POST or None)
    lineas = LineasFormSet(request.POST or None, prefix='lineas')
    if request.method == 'POST' and form.is_valid() and lineas.is_valid():
        datos = [f.cleaned_data for f in lineas if f.cleaned_data and not f.cleaned_data.get('DELETE')]
        try:
            compra = registrar_compra(usuario=request.user, lineas=datos, **form.cleaned_data)
        except ValidationError as exc:
            form.add_error(None, ' '.join(exc.messages))
        else:
            messages.success(request, 'Compra confirmada. Stock actualizado.')
            return redirect('gestion:compra_detalle', pk=compra.pk)
    return render(request, 'gestion/operacion_form.html', {'form': form, 'lineas': lineas, 'tipo': 'compra'})


@login_required
def compra_detalle(request, pk):
    validar_usuario(request.user, solo_dueno=True)
    compra = get_object_or_404(Compra.objects.select_related('proveedor', 'usuario').prefetch_related('detalles__producto'), pk=pk)
    return render(request, 'gestion/operacion_detalle.html', {'object': compra, 'tipo': 'compra'})


@login_required
def stock(request):
    validar_usuario(request.user)
    productos = Producto.objects.all()
    if request.GET.get('q'):
        productos = productos.filter(nombre__icontains=request.GET['q'])
    movimientos = MovimientoStock.objects.select_related('producto', 'usuario')[:50] if request.user.es_dueno else []
    return render(request, 'gestion/stock.html', {
        'productos': Paginator(productos, 30).get_page(request.GET.get('page')), 'movimientos': movimientos,
    })


@login_required
def ventas(request):
    validar_usuario(request.user)
    # El historial es de consulta para cualquier usuario activo autorizado;
    # conservar el vendedor visible permite trazabilidad de cada operación.
    objetos = Venta.objects.select_related('usuario')
    pagina = Paginator(objetos, 30).get_page(request.GET.get('page'))
    return render(request, 'gestion/operaciones.html', {'objetos': pagina, 'tipo': 'venta'})


@login_required
@require_http_methods(['GET', 'POST'])
def venta_crear(request):
    validar_usuario(request.user)
    form = VentaForm(request.POST or None)
    lineas = LineasFormSet(request.POST or None, prefix='lineas')
    if request.method == 'POST' and form.is_valid() and lineas.is_valid():
        datos = [f.cleaned_data for f in lineas if f.cleaned_data and not f.cleaned_data.get('DELETE')]
        try:
            venta = registrar_venta(usuario=request.user, lineas=datos, **form.cleaned_data)
        except ValidationError as exc:
            form.add_error(None, ' '.join(exc.messages))
        else:
            messages.success(request, 'Venta confirmada. Stock actualizado.')
            return redirect('gestion:venta_detalle', pk=venta.pk)
    return render(request, 'gestion/operacion_form.html', {'form': form, 'lineas': lineas, 'tipo': 'venta'})


@login_required
def venta_detalle(request, pk):
    validar_usuario(request.user)
    # Los detalles también son visibles para empleados, independientemente
    # de quién registró la venta. La vista no permite modificar operaciones.
    objetos = Venta.objects.select_related('usuario').prefetch_related('detalles__producto')
    venta = get_object_or_404(objetos, pk=pk)
    return render(request, 'gestion/operacion_detalle.html', {'object': venta, 'tipo': 'venta'})


@login_required
def reportes(request):
    validar_usuario(request.user, solo_dueno=True)
    form = PeriodoForm(request.GET if request.GET else {'periodo': 'semana', 'fecha': timezone.localdate()})
    contexto = {'form': form}
    if form.is_valid():
        inicio, fin = limites_periodo(**form.cleaned_data)
        contexto.update(inicio=inicio, ultimo_dia=fin - timedelta(days=1),
                        proveedores=compras_por_proveedor(inicio, fin),
                        productos=productos_mas_vendidos(inicio, fin))
    return render(request, 'gestion/reportes.html', contexto)
