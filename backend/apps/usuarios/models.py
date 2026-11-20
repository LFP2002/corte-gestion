from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class Usuario(AbstractUser):
    """Usuario del sistema (tabla usuarios_usuario en MySQL)."""
    ROLES = [('dueno', 'Dueño'), ('empleado', 'Empleado')]
    rol = models.CharField(max_length=10, choices=ROLES, default='empleado')
    email = models.EmailField('correo', unique=True)
    intentos_fallidos = models.PositiveSmallIntegerField(default=0, editable=False)
    bloqueo_hasta = models.DateTimeField(null=True, blank=True, editable=False)

    @property
    def cuenta_bloqueada(self):
        return self.bloqueo_hasta is not None and self.bloqueo_hasta > timezone.now()

    @property
    def es_dueno(self):
        return self.rol == 'dueno'

    def __str__(self):
        return self.get_full_name() or self.username
