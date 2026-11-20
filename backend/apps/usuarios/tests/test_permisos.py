from django.urls import reverse

from .base import BaseUsuarios


class PermisosUsuariosTests(BaseUsuarios):
    def test_permisos_usuarios(self):
        self.assertEqual(self.client.get(reverse('usuario_lista')).status_code, 302)
        self.client.force_login(self.empleado)
        self.assertEqual(self.client.get(reverse('usuario_lista')).status_code, 403)
        self.assertEqual(self.client.post(reverse('usuario_crear'), {}).status_code, 403)
        self.client.force_login(self.dueno)
        self.assertEqual(self.client.get(reverse('usuario_lista')).status_code, 200)

    def test_ultimo_dueno_no_se_degrada(self):
        self.client.force_login(self.dueno)
        self.client.post(reverse('usuario_editar', args=[self.dueno.pk]), {
            'username': 'jefe', 'email': self.dueno.email, 'rol': 'empleado', 'first_name': '', 'is_active': 'on',
        })
        self.dueno.refresh_from_db()
        self.assertEqual(self.dueno.rol, 'dueno')

    def test_ultimo_dueno_no_se_desactiva(self):
        self.client.force_login(self.dueno)
        self.client.post(reverse('usuario_editar', args=[self.dueno.pk]), {
            'username': self.dueno.username, 'email': self.dueno.email, 'rol': 'dueno', 'first_name': '',
        })
        self.dueno.refresh_from_db()
        self.assertTrue(self.dueno.is_active)
