from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone as dt_timezone
from io import StringIO
from itertools import product
from threading import Barrier
from unittest.mock import patch

from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management import call_command, CommandError
from django.db import close_old_connections, connections
from django.test import Client, SimpleTestCase, TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from apps.usuarios.authentication import ERROR_ACCESO
from apps.usuarios.forms import UsuarioCrearForm, UsuarioEditarForm
from apps.usuarios.models import Usuario
from apps.usuarios.validators import PoliticaPasswordValidator


CLAVE = 'Segura-Nueva-573!'


class PoliticaTests(SimpleTestCase):
    def test_todas_las_combinaciones_de_requisitos(self):
        validador = PoliticaPasswordValidator()
        for categorias in product((False, True), repeat=4):
            for largo in (7, 8):
                clave = ''.join(c for cumple, c in zip(categorias, 'Ab4!') if cumple).ljust(largo)
                with self.subTest(categorias=categorias, largo=largo):
                    if all(categorias) and largo >= 8:
                        validador.validate(clave)
                    else:
                        with self.assertRaises(ValidationError) as exc:
                            validador.validate(clave)
                        codigos = {e.code for e in exc.exception.error_list}
                        self.assertEqual('password_longitud' in codigos, largo < 8)
                        for presente, codigo in zip(categorias, ('mayuscula', 'minuscula', 'numero', 'simbolo')):
                            self.assertEqual(f'password_{codigo}' in codigos, not presente)

    def test_unicode_y_espacio_no_es_simbolo(self):
        PoliticaPasswordValidator().validate('Árbol-943!')
        with self.assertRaisesMessage(ValidationError, 'símbolo'):
            PoliticaPasswordValidator().validate('Arbol 943')

    def test_validadores_django_siguen_presentes(self):
        with self.assertRaises(ValidationError) as exc:
            validate_password('12345678')
        codigos = {e.code for e in exc.exception.error_list}
        self.assertIn('password_too_common', codigos)
        self.assertIn('password_entirely_numeric', codigos)


class CredencialesTests(TestCase):
    def datos(self, clave):
        return {'username': 'nuevo', 'email': 'nuevo@example.test', 'first_name': 'Nuevo',
                'rol': 'empleado', 'password1': clave, 'password2': clave}

    def test_creacion_empleado_rechaza_debil_y_guarda_hash_fuerte(self):
        form = UsuarioCrearForm(self.datos('sin-mayuscula-573!'))
        self.assertFalse(form.is_valid())
        self.assertIn('mayúscula', str(form.errors))
        form = UsuarioCrearForm(self.datos(CLAVE))
        self.assertTrue(form.is_valid(), form.errors)
        usuario = form.save()
        self.assertNotEqual(usuario.password, CLAVE)
        self.assertTrue(usuario.check_password(CLAVE))

    def test_edicion_rechaza_debil_conserva_hash_y_permite_vacio(self):
        usuario = Usuario.objects.create_user('antiguo', 'antiguo@example.test', 'clave-antigua')
        anterior = usuario.password
        datos = {'username': usuario.username, 'email': usuario.email, 'rol': usuario.rol, 'is_active': 'on'}
        form = UsuarioEditarForm({**datos, 'password': 'sin-mayuscula-573!'}, instance=usuario)
        self.assertFalse(form.is_valid())
        usuario.refresh_from_db()
        self.assertEqual(usuario.password, anterior)
        form = UsuarioEditarForm(datos, instance=usuario)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        usuario.refresh_from_db()
        self.assertEqual(usuario.password, anterior)
        form = UsuarioEditarForm({**datos, 'password': CLAVE}, instance=usuario)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertTrue(form.save().check_password(CLAVE))

    def test_formulario_django_set_password_y_admin(self):
        from django.contrib.auth.forms import AdminPasswordChangeForm
        usuario = Usuario.objects.create_user('caja', 'caja@example.test', CLAVE)
        for clase in (SetPasswordForm, AdminPasswordChangeForm):
            form = clase(usuario, {'new_password1': 'Sin-numero!', 'new_password2': 'Sin-numero!',
                                  'password1': 'Sin-numero!', 'password2': 'Sin-numero!'})
            self.assertFalse(form.is_valid(), clase)
            self.assertIn('número', str(form.errors))

    def test_primer_dueno_no_omite_politica(self):
        with patch('builtins.input', side_effect=['jefe', 'jefe@example.test']), patch(
            'apps.usuarios.management.commands.crear_dueno.getpass', return_value='sin-mayuscula-573!'
        ):
            with self.assertRaisesMessage(CommandError, 'mayúscula'):
                call_command('crear_dueno', stdout=StringIO())
        self.assertFalse(Usuario.objects.exists())

    def test_cuenta_antigua_autentica_sin_revalidar_password(self):
        usuario = Usuario.objects.create_user('antiguo', 'antiguo@example.test', 'simple')
        anterior = usuario.password
        respuesta = self.client.post('/login/', {'username': usuario.username, 'password': 'simple'})
        self.assertEqual(respuesta.status_code, 302)
        usuario.refresh_from_db()
        self.assertEqual(usuario.password, anterior)

    def test_admin_creacion_valida_politica_y_guarda_hash(self):
        jefe = Usuario.objects.create_superuser('jefe', 'jefe@example.test', CLAVE, rol='dueno')
        self.client.force_login(jefe)
        datos = {'username': 'nuevo', 'email': 'nuevo@example.test', 'rol': 'empleado',
                 'usable_password': 'true', 'password1': 'Sin-numero!', 'password2': 'Sin-numero!'}
        respuesta = self.client.post('/admin/usuarios/usuario/add/', datos)
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'número')
        self.assertFalse(Usuario.objects.filter(username='nuevo').exists())
        respuesta = self.client.post('/admin/usuarios/usuario/add/', {**datos, 'password1': CLAVE, 'password2': CLAVE})
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(Usuario.objects.get(username='nuevo').check_password(CLAVE))


class BloqueoTests(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user('caja', 'caja@example.test', CLAVE)
        self.dueno = Usuario.objects.create_user('jefe', 'jefe@example.test', CLAVE, rol='dueno')

    def intento(self, password='incorrecta', username='caja', cliente=None):
        return (cliente or self.client).post('/login/', {'username': username, 'password': password})

    def bloquear(self):
        for _ in range(3):
            self.intento()
        self.usuario.refresh_from_db()

    def test_primer_segundo_y_tercer_fallo(self):
        for numero in range(1, 4):
            self.assertEqual(self.intento().status_code, 200)
            self.usuario.refresh_from_db()
            self.assertEqual(self.usuario.intentos_fallidos, numero)
            self.assertEqual(self.usuario.cuenta_bloqueada, numero == 3)
            self.assertTrue(self.usuario.is_active)
            self.assertEqual(self.usuario.rol, 'empleado')

    def test_correcta_durante_bloqueo_no_accede_ni_extiende(self):
        self.bloquear()
        hasta = self.usuario.bloqueo_hasta
        respuesta = self.intento(CLAVE)
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.bloqueo_hasta, hasta)
        self.assertEqual(self.usuario.intentos_fallidos, 3)

    def test_exito_antes_bloqueo_restablece(self):
        self.intento(); self.intento()
        self.assertEqual(self.intento(CLAVE).status_code, 302)
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.intentos_fallidos, 0)
        self.assertIsNone(self.usuario.bloqueo_hasta)

    def test_expira_exactamente_a_los_quince_minutos(self):
        ahora = datetime(2026, 11, 20, 12, tzinfo=dt_timezone.utc)
        with patch('apps.usuarios.authentication.timezone.now', return_value=ahora):
            self.bloquear()
        self.assertEqual(self.usuario.bloqueo_hasta, ahora + timedelta(minutes=15))
        with patch('apps.usuarios.authentication.timezone.now', return_value=ahora + timedelta(minutes=15) - timedelta(microseconds=1)):
            self.assertEqual(self.intento(CLAVE).status_code, 200)
        with patch('apps.usuarios.authentication.timezone.now', return_value=ahora + timedelta(minutes=15)):
            self.assertEqual(self.intento(CLAVE).status_code, 302)

    def test_primer_fallo_tras_expiracion_inicia_ciclo_nuevo(self):
        self.bloquear()
        with patch('apps.usuarios.authentication.timezone.now', return_value=self.usuario.bloqueo_hasta):
            self.intento()
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.intentos_fallidos, 1)
        self.assertIsNone(self.usuario.bloqueo_hasta)

    def test_mensaje_identico_inexistente_inactivo_bloqueado_y_password_erroneo(self):
        respuestas = [self.intento(username='no-existe'), self.intento()]
        self.usuario.is_active = False; self.usuario.save()
        respuestas.append(self.intento(CLAVE))
        self.usuario.is_active = True; self.usuario.save()
        self.bloquear(); respuestas.append(self.intento(CLAVE))
        for respuesta in respuestas:
            self.assertEqual(list(respuesta.context['form'].non_field_errors()), [ERROR_ACCESO])
        self.assertEqual(Usuario.objects.count(), 2)

    def test_desbloqueo_dueno_post_y_csrf(self):
        self.bloquear()
        url = reverse('usuario_desbloquear', args=[self.usuario.pk])
        self.client.force_login(self.dueno)
        self.assertEqual(self.client.get(url).status_code, 405)
        estricto = Client(enforce_csrf_checks=True); estricto.force_login(self.dueno)
        self.assertEqual(estricto.post(url).status_code, 403)
        self.assertEqual(self.client.post(url).status_code, 302)
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.intentos_fallidos, 0)
        self.assertIsNone(self.usuario.bloqueo_hasta)
        self.assertEqual(self.intento(CLAVE, cliente=Client()).status_code, 302)

    def test_empleado_y_anonimo_no_desbloquean(self):
        self.bloquear()
        url = reverse('usuario_desbloquear', args=[self.dueno.pk])
        self.assertEqual(self.client.post(url).status_code, 302)
        self.client.force_login(self.usuario)
        self.assertEqual(self.client.post(url).status_code, 403)

    def test_desbloqueo_no_reactiva_cuenta_y_comando_local(self):
        self.bloquear()
        self.usuario.is_active = False; self.usuario.save()
        call_command('desbloquear_usuario', self.usuario.username, stdout=StringIO())
        self.usuario.refresh_from_db()
        self.assertFalse(self.usuario.is_active)
        self.assertIsNone(self.usuario.bloqueo_hasta)
        self.assertEqual(self.intento(CLAVE).status_code, 200)

    def test_admin_comparte_contador_y_bloqueo(self):
        self.dueno.is_staff = True; self.dueno.save()
        for _ in range(3):
            self.client.post('/admin/login/', {'username': 'jefe', 'password': 'incorrecta'})
        self.dueno.refresh_from_db()
        self.assertTrue(self.dueno.cuenta_bloqueada)
        self.assertEqual(self.intento(CLAVE, username='jefe').status_code, 200)
        self.assertEqual(self.client.post('/admin/login/', {'username': 'jefe', 'password': CLAVE}).status_code, 200)

    def test_editar_no_desbloquea_y_listado_distingue_estados(self):
        self.bloquear(); self.client.force_login(self.dueno)
        self.client.post(reverse('usuario_editar', args=[self.usuario.pk]), {
            'username': 'caja', 'email': self.usuario.email, 'rol': 'empleado', 'is_active': 'on',
        })
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.cuenta_bloqueada)
        self.assertContains(self.client.get('/usuarios/'), 'Desbloquear cuenta')

    def test_sesion_existente_django_no_se_reemplaza_ni_revoca_por_bloqueo(self):
        sesion = Client(); sesion.force_login(self.usuario, backend='django.contrib.auth.backends.ModelBackend')
        self.bloquear()
        self.assertEqual(sesion.get('/').status_code, 200)
        self.assertEqual(sesion.session['_auth_user_backend'], 'django.contrib.auth.backends.ModelBackend')

    def test_admin_cambia_password_sin_borrar_bloqueo(self):
        self.bloquear()
        self.dueno.is_staff = True; self.dueno.is_superuser = True; self.dueno.save()
        self.client.force_login(self.dueno)
        respuesta = self.client.post(f'/admin/usuarios/usuario/{self.usuario.pk}/password/', {
            'usable_password': 'true', 'password1': CLAVE, 'password2': CLAVE,
        })
        self.assertEqual(respuesta.status_code, 302)
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.cuenta_bloqueada)
        self.assertTrue(self.usuario.check_password(CLAVE))


class ConcurrenciaAccesoTests(TransactionTestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user('caja', 'caja@example.test', CLAVE)

    def ejecutar(self, claves):
        barrera = Barrier(len(claves))

        def autenticar(clave):
            close_old_connections()
            try:
                barrera.wait(timeout=15)
                return Client().post('/login/', {'username': 'caja', 'password': clave}).status_code
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=len(claves)) as pool:
            return list(pool.map(autenticar, claves))

    def test_tres_fallos_simultaneos_no_pierden_incrementos(self):
        self.assertEqual(self.ejecutar(['error'] * 3), [200] * 3)
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.intentos_fallidos, 3)
        self.assertTrue(self.usuario.cuenta_bloqueada)

    def test_correcta_y_tercer_fallo_son_serializados(self):
        self.usuario.intentos_fallidos = 2; self.usuario.save()
        resultados = self.ejecutar(['error', CLAVE])
        self.usuario.refresh_from_db()
        self.assertIn((resultados.count(302), self.usuario.intentos_fallidos), [(1, 1), (0, 3)])

    def test_persistencia_en_conexiones_y_clientes_nuevos(self):
        Client().post('/login/', {'username': 'caja', 'password': 'error'})
        connections.close_all()
        Client().post('/login/', {'username': 'caja', 'password': 'error'})
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.intentos_fallidos, 2)
