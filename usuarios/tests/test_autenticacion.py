from django.urls import reverse

from usuarios.models import Usuario
from .base import BaseUsuarios


class AutenticacionTests(BaseUsuarios):
    def test_login_y_logout(self):
        respuesta = self.client.post(reverse('login'), {'username': 'jefe', 'password': 'Clave-test-934!'})
        self.assertRedirects(respuesta, reverse('inicio'))
        self.assertEqual(self.client.get(reverse('logout')).status_code, 405)
        self.assertRedirects(self.client.post(reverse('logout')), reverse('login'))

    def test_registro_cerrado(self):
        for metodo in (self.client.get, self.client.post):
            self.assertEqual(metodo('/registro/').status_code, 404)
        self.assertEqual(Usuario.objects.count(), 2)
