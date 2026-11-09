from django.test import TestCase

from usuarios.models import Usuario


class BaseUsuarios(TestCase):
    def setUp(self):
        self.dueno = Usuario.objects.create_user('jefe', 'jefe@example.test', 'Clave-test-934!', rol='dueno')
        self.empleado = Usuario.objects.create_user('caja', 'caja@example.test', 'Clave-test-934!')
