from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

from django.db import close_old_connections, connections
from django.test import Client, TestCase, TransactionTestCase
from django.utils import timezone

from apps.usuarios.authentication import ERROR_ACCESO
from apps.usuarios.models import Usuario


CLAVE = 'Clave-admin-945!'


class AccesoAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cuentas = [
            Usuario.objects.create_user(f'cuenta{i}', f'cuenta{i}@example.test', CLAVE,
                                        rol=rol, is_staff=staff, is_active=activo)
            for i, (rol, staff, activo) in enumerate((
                ('empleado', False, True), ('empleado', True, True),
                ('dueno', False, True), ('dueno', True, True),
                ('empleado', False, False), ('dueno', True, False),
            ))
        ]

    def acceder(self, cuenta, password=CLAVE, path='/admin/login/'):
        cliente = Client()
        respuesta = cliente.post(path, {'username': cuenta.username, 'password': password})
        return cliente, respuesta

    def test_credenciales_correctas_autorizacion_y_contador_separados(self):
        for cuenta in self.cuentas:
            for path in ('/login/', '/admin/login/'):
                with self.subTest(cuenta=cuenta.username, path=path):
                    Usuario.objects.filter(pk=cuenta.pk).update(intentos_fallidos=2)
                    cliente, respuesta = self.acceder(cuenta, path=path)
                    permitido = cuenta.is_active and (path == '/login/' or (cuenta.is_staff and cuenta.es_dueno))
                    self.assertEqual(respuesta.status_code, 302 if permitido else 200)
                    self.assertEqual('_auth_user_id' in cliente.session, permitido)
                    cuenta.refresh_from_db()
                    self.assertEqual(cuenta.intentos_fallidos, 0 if cuenta.is_active else 2)
                    self.assertIsNone(cuenta.bloqueo_hasta)
                    if not permitido:
                        self.assertContains(respuesta, ERROR_ACCESO, count=1)
                        self.assertIsNone(respuesta.context['form'].get_user())

    def test_password_incorrecta_cuenta_en_ambos_logins_aunque_no_tenga_permisos(self):
        for cuenta in self.cuentas:
            with self.subTest(cuenta=cuenta.username):
                for numero, path in enumerate(('/admin/login/', '/login/', '/admin/login/'), start=1):
                    cliente, respuesta = self.acceder(cuenta, password='incorrecta', path=path)
                    self.assertContains(respuesta, ERROR_ACCESO, count=1)
                    self.assertNotIn('_auth_user_id', cliente.session)
                    cuenta.refresh_from_db()
                    self.assertEqual(cuenta.intentos_fallidos, numero if cuenta.is_active else 0)
                self.assertEqual(cuenta.cuenta_bloqueada, cuenta.is_active)

    def test_admin_correcto_no_desbloquea_ningun_tipo_de_cuenta(self):
        hasta = timezone.now() + timedelta(minutes=15)
        for cuenta in self.cuentas:
            Usuario.objects.filter(pk=cuenta.pk).update(intentos_fallidos=3, bloqueo_hasta=hasta)
            for path in ('/admin/login/', '/login/'):
                cliente, respuesta = self.acceder(cuenta, path=path)
                self.assertContains(respuesta, ERROR_ACCESO, count=1)
                self.assertNotIn('_auth_user_id', cliente.session)
            cuenta.refresh_from_db()
            self.assertEqual(cuenta.intentos_fallidos, 3)
            self.assertEqual(cuenta.bloqueo_hasta, hasta)

    def test_denegaciones_admin_repetidas_no_bloquean_al_empleado(self):
        empleado = self.cuentas[0]
        for _ in range(4):
            self.assertEqual(self.acceder(empleado)[1].status_code, 200)
        empleado.refresh_from_db()
        self.assertEqual(empleado.intentos_fallidos, 0)
        self.assertIsNone(empleado.bloqueo_hasta)
        self.assertEqual(self.acceder(empleado, path='/login/')[1].status_code, 302)

    def test_mensaje_renderizado_del_login_no_revela_el_motivo(self):
        empleado = self.cuentas[0]
        inactivo = self.cuentas[-1]
        respuestas = [self.acceder(empleado, password='incorrecta', path='/login/')[1],
                      self.acceder(inactivo, path='/login/')[1],
                      Client().post('/login/', {'username': 'inexistente', 'password': CLAVE})]
        Usuario.objects.filter(pk=empleado.pk).update(intentos_fallidos=3, bloqueo_hasta=timezone.now() + timedelta(minutes=15))
        respuestas.append(self.acceder(empleado, path='/login/')[1])
        for respuesta in respuestas:
            self.assertContains(respuesta, ERROR_ACCESO, count=1)
            self.assertContains(respuesta, 'role="alert"')
            self.assertContains(respuesta, 'csrfmiddlewaretoken')
            for texto in ('Usuario o contraseña incorrectos.', 'intentos fallidos', '15 minutos', 'cuenta bloqueada', 'cuenta desactivada'):
                self.assertNotContains(respuesta, texto)


class ConcurrenciaAdminTests(TransactionTestCase):
    def setUp(self):
        self.empleado = Usuario.objects.create_user('caja', 'caja@example.test', CLAVE)

    def acceder_simultaneamente(self, intentos):
        barrera = Barrier(len(intentos))

        def acceder(intento):
            close_old_connections()
            try:
                path, password = intento
                cliente = Client()
                barrera.wait(timeout=15)
                respuesta = cliente.post(path, {'username': 'caja', 'password': password})
                return respuesta.status_code, '_auth_user_id' in cliente.session
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=len(intentos)) as pool:
            return list(pool.map(acceder, intentos))

    def test_denegaciones_administrativas_simultaneas_no_son_fallos(self):
        self.empleado.intentos_fallidos = 2; self.empleado.save()
        resultados = self.acceder_simultaneamente([('/admin/login/', CLAVE)] * 3)
        self.assertEqual(resultados, [(200, False)] * 3)
        self.empleado.refresh_from_db()
        self.assertEqual(self.empleado.intentos_fallidos, 0)
        self.assertIsNone(self.empleado.bloqueo_hasta)

    def test_denegacion_correcta_y_tercer_fallo_se_serializan(self):
        self.empleado.intentos_fallidos = 2; self.empleado.save()
        resultados = self.acceder_simultaneamente([('/admin/login/', CLAVE), ('/login/', 'incorrecta')])
        self.assertEqual(resultados, [(200, False)] * 2)
        self.empleado.refresh_from_db()
        # Correcta primero: reset y un fallo; fallo primero: bloqueo que la correcta no quita.
        self.assertIn(self.empleado.intentos_fallidos, (1, 3))
        self.assertEqual(self.empleado.cuenta_bloqueada, self.empleado.intentos_fallidos == 3)

    def test_fallos_reales_simultaneos_comparten_el_contador(self):
        resultados = self.acceder_simultaneamente([
            ('/admin/login/', 'incorrecta'), ('/login/', 'incorrecta'), ('/admin/login/', 'incorrecta'),
        ])
        self.assertEqual(resultados, [(200, False)] * 3)
        self.empleado.refresh_from_db()
        self.assertEqual(self.empleado.intentos_fallidos, 3)
        self.assertTrue(self.empleado.cuenta_bloqueada)
