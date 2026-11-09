from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect
from django.core.exceptions import PermissionDenied
from decimal import Decimal

from django.db import transaction
from django.db.models import Count, Q, Sum
from django.utils import timezone

from gestion.models import Producto, Venta
from django.db.models.deletion import ProtectedError
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, TemplateView, UpdateView

from .forms import UsuarioCrearForm, UsuarioEditarForm
from .models import Usuario


class SoloDueno(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.es_dueno

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied('Esta sección es solo para el dueño.')
        return super().handle_no_permission()


class Inicio(LoginRequiredMixin, TemplateView):
    template_name = 'usuarios/inicio.html'

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        productos = Producto.objects.filter(activo=True).aggregate(
            cantidad=Count('pk'),
            agotados=Count('pk', filter=Q(stock=0)),
        )
        ventas = Venta.objects.filter(fecha=timezone.localdate())
        if not self.request.user.es_dueno:
            # Un empleado únicamente puede consultar los indicadores de sus ventas.
            ventas = ventas.filter(usuario_id=self.request.user.pk)
        resumen_ventas = ventas.aggregate(
            cantidad=Count('pk'),
            monto=Sum('total', default=Decimal('0')),
        )
        contexto.update(
            productos_activos=productos['cantidad'],
            productos_agotados=productos['agotados'],
            ventas_hoy=resumen_ventas['cantidad'],
            monto_ventas_hoy=resumen_ventas['monto'],
        )
        return contexto


class UsuarioLista(SoloDueno, ListView):
    model = Usuario
    template_name = 'usuarios/lista.html'
    context_object_name = 'usuarios'
    ordering = ['id']


class UsuarioCrear(SoloDueno, CreateView):
    form_class = UsuarioCrearForm
    template_name = 'usuarios/form.html'
    success_url = reverse_lazy('usuario_lista')
    extra_context = {'titulo': 'Nuevo usuario'}

    def form_valid(self, form):
        messages.success(self.request, 'Usuario creado.')
        return super().form_valid(form)


class UsuarioEditar(SoloDueno, UpdateView):
    model = Usuario
    form_class = UsuarioEditarForm
    template_name = 'usuarios/form.html'
    success_url = reverse_lazy('usuario_lista')
    extra_context = {'titulo': 'Editar usuario'}

    def form_valid(self, form):
        with transaction.atomic():
            usuarios = list(Usuario.objects.select_for_update().order_by('pk'))
            anterior = next(u for u in usuarios if u.pk == self.object.pk)
            if (anterior.es_dueno and anterior.is_active
                    and (form.cleaned_data['rol'] != 'dueno' or not form.cleaned_data['is_active'])
                    and sum(u.es_dueno and u.is_active for u in usuarios) <= 1):
                form.add_error('rol', 'Debe quedar al menos un dueño activo.')
                return self.form_invalid(form)
            messages.success(self.request, 'Usuario actualizado.')
            return super().form_valid(form)


class UsuarioEliminar(SoloDueno, DeleteView):
    model = Usuario
    template_name = 'usuarios/eliminar.html'
    success_url = reverse_lazy('usuario_lista')

    def post(self, request, *args, **kwargs):
        with transaction.atomic():
            usuarios = list(Usuario.objects.select_for_update().order_by('pk'))
            u = self.get_object()
            if u == request.user:
                messages.error(request, 'No puedes eliminar tu propio usuario.')
            elif u.es_dueno and u.is_active and sum(x.es_dueno and x.is_active for x in usuarios) <= 1:
                messages.error(request, 'Debe quedar al menos un dueño activo.')
            else:
                try:
                    u.delete()
                    messages.success(request, f'Usuario «{u}» eliminado.')
                except ProtectedError:
                    messages.error(request, 'Usuario con operaciones históricas: no se puede eliminar. Desactive su cuenta al editar.')
        return redirect(self.success_url)
