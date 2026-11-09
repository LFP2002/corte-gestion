from io import StringIO
from unittest.mock import patch

from django.core.management import call_command

from usuarios.models import Usuario
from .base import BaseUsuarios


class ComandosUsuariosTests(BaseUsuarios):
    def test_comando_idempotente(self):
        with patch('builtins.input', side_effect=AssertionError('No debe pedir datos')):
            call_command('crear_dueno', stdout=StringIO())
        self.assertEqual(Usuario.objects.count(), 2)

    def test_creacion_segura_primer_dueno(self):
        Usuario.objects.all().delete()
        with patch('builtins.input', side_effect=['propietario', 'propietario@example.test']), patch(
            'usuarios.management.commands.crear_dueno.getpass', return_value='Fuerte-942-Zebra!'
        ):
            call_command('crear_dueno', stdout=StringIO())
        usuario = Usuario.objects.get()
        self.assertTrue(usuario.es_dueno)
        self.assertTrue(usuario.check_password('Fuerte-942-Zebra!'))
        self.assertFalse(usuario.is_staff)
