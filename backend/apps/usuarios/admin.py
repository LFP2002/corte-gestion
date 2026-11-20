from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.admin.utils import unquote
from django.db import transaction

from .models import Usuario
from .authentication import AccesoAdminForm


def acceso_admin(request):
    return request.user.is_active and request.user.is_staff and request.user.es_dueno


admin.site.has_permission = acceso_admin
admin.site.login_form = AccesoAdminForm


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'rol', 'is_staff', 'bloqueo_hasta')
    readonly_fields = ('intentos_fallidos', 'bloqueo_hasta')
    fieldsets = UserAdmin.fieldsets + (('Rol', {'fields': ('rol',)}),)
    add_fieldsets = ((None, {'classes': ('wide',), 'fields': (
        'username', 'email', 'first_name', 'rol', 'usable_password', 'password1', 'password2',
    )}),)

    def save_model(self, request, obj, form, change):
        with transaction.atomic():
            if change:
                actual = Usuario.objects.select_for_update().get(pk=obj.pk)
                obj.intentos_fallidos = actual.intentos_fallidos
                obj.bloqueo_hasta = actual.bloqueo_hasta
            super().save_model(request, obj, form, change)

    def user_change_password(self, request, id, form_url=''):
        # El formulario original de Django guarda la instancia completa. Tomar el
        # mismo bloqueo antes de que la vuelva a cargar evita perder intentos nuevos.
        with transaction.atomic():
            if request.method == 'POST':
                usuario = self.get_object(request, unquote(id))
                if usuario is not None:
                    Usuario.objects.select_for_update().get(pk=usuario.pk)
            return super().user_change_password(request, id, form_url)
