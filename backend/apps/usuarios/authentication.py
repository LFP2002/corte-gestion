"""Extiende los formularios Django, sin cambiar backends, hashes ni sesiones."""
from datetime import timedelta

from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.views.decorators.debug import sensitive_variables

from .models import Usuario


ERROR_ACCESO = 'No fue posible iniciar sesión. Verifica tus credenciales o solicita ayuda al dueño para recuperar el acceso.'
MAX_INTENTOS = 3
TIEMPO_BLOQUEO = timedelta(minutes=15)


class ControlIntentosMixin:
    error_messages = {'invalid_login': ERROR_ACCESO, 'inactive': ERROR_ACCESO}

    @sensitive_variables('password')
    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        self.user_cache = None
        if not username or not password:
            return self.cleaned_data
        error = None
        # El bloqueo abarca la comprobación de contraseña: dos solicitudes no pueden
        # perder incrementos ni autenticar después de que otra haya bloqueado la cuenta.
        with transaction.atomic():
            usuario = Usuario.objects.select_for_update().filter(username=username).first()
            ahora = timezone.now()
            if usuario and usuario.bloqueo_hasta and usuario.bloqueo_hasta > ahora:
                # Trabajo criptográfico también para cuentas bloqueadas; no revelar
                # existencia/estado por un atajo sin hash. Nunca guardar la entrada.
                make_password(password)
                self.user_cache = None
                error = self.get_invalid_login_error()
            else:
                if usuario and usuario.bloqueo_hasta:
                    usuario.intentos_fallidos = 0
                    usuario.bloqueo_hasta = None
                # AuthenticationForm.clean mezcla authenticate() y autorización.
                # Separar sus dos fases permite persistir solo fallos de credenciales,
                # conservando el backend, la caché de usuario y los hooks de Django.
                self.user_cache = authenticate(self.request, username=username, password=password)
                if self.user_cache is None:
                    error = self.get_invalid_login_error()
                    if usuario and usuario.is_active:
                        usuario.intentos_fallidos = min(usuario.intentos_fallidos + 1, MAX_INTENTOS)
                        if usuario.intentos_fallidos == MAX_INTENTOS:
                            usuario.bloqueo_hasta = ahora + TIEMPO_BLOQUEO
                else:
                    if usuario:
                        usuario.intentos_fallidos = 0
                        usuario.bloqueo_hasta = None
                    try:
                        self.confirm_login_allowed(self.user_cache)
                    except ValidationError:
                        # Contraseña correcta pero acceso al área denegado: no es
                        # fallo de autenticación ni debe producir una sesión.
                        self.user_cache = None
                        error = self.get_invalid_login_error()
                if usuario:
                    usuario.save(update_fields=['intentos_fallidos', 'bloqueo_hasta'])
        # Lanzar después del commit; hacerlo dentro revertiría el contador de fallos.
        if error:
            raise error
        return self.cleaned_data


class AccesoForm(ControlIntentosMixin, AuthenticationForm):
    pass


class AccesoAdminForm(ControlIntentosMixin, AdminAuthenticationForm):
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.es_dueno:
            raise self.get_invalid_login_error()
