from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Usuario


def acceso_admin(request):
    return request.user.is_active and request.user.is_staff and request.user.es_dueno


admin.site.has_permission = acceso_admin


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'rol', 'is_staff')
    fieldsets = UserAdmin.fieldsets + (('Rol', {'fields': ('rol',)}),)
