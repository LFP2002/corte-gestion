from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    """Usuario del sistema (tabla usuarios_usuario en MySQL)."""
    ROLES = [('dueno', 'Dueño'), ('empleado', 'Empleado')]
    rol = models.CharField(max_length=10, choices=ROLES, default='empleado')
    email = models.EmailField('correo', unique=True)

    @property
    def es_dueno(self):
        return self.rol == 'dueno'

    def __str__(self):
        return self.get_full_name() or self.username
