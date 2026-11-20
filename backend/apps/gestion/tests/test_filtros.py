from datetime import date, timedelta
from urllib.parse import parse_qs, urlsplit
from html.parser import HTMLParser

from django.test import TestCase
from django.utils import timezone

from apps.gestion.models import Compra, Producto, Proveedor, Venta
from apps.usuarios.models import Usuario


class Enlaces(HTMLParser):
    def __init__(self, html):
        super().__init__(); self.enlaces = []; self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.enlaces.extend(value for key, value in attrs if key == 'href')


class FiltrosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.dueno = Usuario.objects.create_user('jefe', 'jefe@example.test', rol='dueno')
        cls.empleado = Usuario.objects.create_user('caja', 'caja@example.test', first_name='Luis')
        cls.inactivo = Usuario.objects.create_user('antiguo', 'antiguo@example.test', is_active=False)
        cls.producto = Producto.objects.create(nombre='Posta', precio_venta=8000, stock=5, unidad='kg')
        cls.agotado = Producto.objects.create(nombre='Pollo', precio_venta=3000, unidad='unidad')
        cls.oculto = Producto.objects.create(nombre='Posta antigua', precio_venta=8000, activo=False)
        cls.proveedor = Proveedor.objects.create(nombre='Frigorífico Uno')
        cls.proveedor_inactivo = Proveedor.objects.create(nombre='Frigorífico Antiguo', activo=False)
        cls.venta = Venta.objects.create(usuario=cls.empleado, fecha=date(2026, 10, 10), total=100)
        cls.otra_venta = Venta.objects.create(usuario=cls.dueno, fecha=date(2026, 11, 10), total=200)
        cls.compra = Compra.objects.create(usuario=cls.dueno, proveedor=cls.proveedor, fecha=date(2026, 10, 10), total=100)
        cls.otra_compra = Compra.objects.create(usuario=cls.dueno, proveedor=cls.proveedor_inactivo, fecha=date(2026, 11, 10), total=200)

    def setUp(self):
        self.client.force_login(self.dueno)

    def ids(self, path, params, variable='objetos'):
        respuesta = self.client.get(path, params)
        self.assertEqual(respuesta.status_code, 200)
        return [o.pk for o in respuesta.context[variable]]

    def test_productos_nombre_estado_stock_y_unidad_combinados(self):
        self.assertEqual(self.ids('/productos/', {'q': 'Posta', 'estado': 'activo',
                         'disponibilidad': 'disponible', 'unidad': 'kg'}), [self.producto.pk])
        self.assertEqual(self.ids('/productos/', {'disponibilidad': 'agotado', 'unidad': 'unidad'}), [self.agotado.pk])
        self.assertEqual(self.ids('/productos/', {'estado': 'inactivo'}), [self.oculto.pk])

    def test_proveedores_nombre_y_estado(self):
        self.assertEqual(self.ids('/proveedores/', {'q': 'Antiguo', 'estado': 'inactivo'}), [self.proveedor_inactivo.pk])

    def test_stock_nombre_disponibilidad_y_estado(self):
        self.assertEqual(self.ids('/stock/', {'q': 'Posta', 'estado': 'activo',
                         'disponibilidad': 'disponible'}, 'productos'), [self.producto.pk])
        self.assertEqual(self.ids('/stock/', {'estado': 'inactivo'}, 'productos'), [self.oculto.pk])

    def test_ventas_rango_inclusivo_y_vendedor_ambos_roles(self):
        for usuario in (self.dueno, self.empleado):
            self.client.force_login(usuario)
            self.assertEqual(self.ids('/ventas/', {'desde': '2026-10-10', 'hasta': '2026-10-10',
                                                  'vendedor': self.empleado.pk}), [self.venta.pk])
            self.assertEqual(self.ids('/ventas/', {'vendedor': self.dueno.pk}), [self.otra_venta.pk])
            self.assertEqual(len(self.ids('/ventas/', {})), 2)

    def test_compras_fecha_y_proveedor_historico_inactivo(self):
        self.assertEqual(self.ids('/compras/', {'desde': '2026-11-01', 'hasta': '2026-11-30',
                         'proveedor': self.proveedor_inactivo.pk}), [self.otra_compra.pk])

    def test_usuarios_nombre_rol_estado_y_bloqueo(self):
        self.empleado.bloqueo_hasta = timezone.now() + timedelta(minutes=15); self.empleado.save()
        self.assertEqual(self.ids('/usuarios/', {'q': 'Luis', 'rol': 'empleado', 'estado': 'activo',
                         'bloqueo': 'bloqueado'}, 'usuarios'), [self.empleado.pk])
        self.assertEqual(self.ids('/usuarios/', {'estado': 'inactivo', 'bloqueo': 'libre'}, 'usuarios'), [self.inactivo.pk])
        self.empleado.bloqueo_hasta = timezone.now() - timedelta(seconds=1); self.empleado.save()
        self.assertEqual(self.ids('/usuarios/', {'bloqueo': 'bloqueado'}, 'usuarios'), [])

    def test_parametros_invalidos_muestran_error_y_no_amplian_resultados(self):
        for path, datos, variable in (
            ('/productos/', {'estado': 'borrar'}, 'objetos'),
            ('/productos/', {'unidad': 'invalida'}, 'objetos'),
            ('/productos/', {'disponibilidad': 'negativo'}, 'objetos'),
            ('/ventas/', {'desde': '2026-99-99'}, 'objetos'),
            ('/ventas/', {'desde': '2026-11-01', 'hasta': '2026-10-01'}, 'objetos'),
            ('/ventas/', {'vendedor': '999999'}, 'objetos'),
            ('/compras/', {'proveedor': "1 OR 1=1"}, 'objetos'),
            ('/usuarios/', {'rol': 'admin'}, 'usuarios'),
            ('/usuarios/', {'bloqueo': 'invalido'}, 'usuarios'),
        ):
            with self.subTest(path=path, datos=datos):
                respuesta = self.client.get(path, datos)
                self.assertTrue(respuesta.context['filtro_form'].errors)
                self.assertEqual(list(respuesta.context[variable]), [])
                self.assertContains(respuesta, 'Revisa los filtros indicados.')

    def test_entrada_sql_y_html_es_dato_no_codigo(self):
        self.assertEqual(self.ids('/productos/', {'q': "' OR 1=1 --"}), [])
        respuesta = self.client.get('/productos/', {'q': '<script>alert(1)</script>'})
        self.assertNotContains(respuesta, '<script>alert(1)</script>')
        self.assertContains(respuesta, '&lt;script&gt;')

    def test_panel_cerrado_por_defecto_y_estado_visible_con_filtros(self):
        for path in ('/productos/', '/proveedores/', '/ventas/', '/compras/', '/stock/', '/usuarios/'):
            respuesta = self.client.get(path)
            self.assertContains(respuesta, '<details class="filtros">')
            self.assertNotContains(respuesta, '<details class="filtros" open>')
            self.assertContains(respuesta, 'Aplicar filtros')
        respuesta = self.client.get('/productos/', {'q': 'Posta', 'estado': 'activo'})
        self.assertContains(respuesta, 'Filtros activos: 2')
        self.assertContains(respuesta, '<details class="filtros" open>')
        self.assertContains(respuesta, 'value="Posta"')
        self.assertContains(respuesta, 'value="activo" selected')

    def test_paginacion_conserva_todos_los_filtros_y_valores_codificados(self):
        Producto.objects.bulk_create([Producto(nombre=f'Carne & especial {i}', precio_venta=100, stock=2) for i in range(35)])
        datos = {'q': 'Carne & especial', 'estado': 'activo', 'disponibilidad': 'disponible', 'unidad': 'kg'}
        respuesta = self.client.get('/productos/', datos)
        enlaces = Enlaces(respuesta.content.decode()).enlaces
        siguiente = next(url for url in enlaces if parse_qs(urlsplit(url).query).get('page') == ['2'])
        params = parse_qs(urlsplit(siguiente).query)
        for key, value in datos.items():
            self.assertEqual(params[key], [value])
        self.assertEqual(len(self.client.get('/productos/' + siguiente).context['objetos']), 5)

    def test_paginacion_usuarios_y_listados_sin_permisos_no_se_abren(self):
        Usuario.objects.bulk_create([Usuario(username=f'empleado{i}', email=f'empleado{i}@example.test') for i in range(32)])
        respuesta = self.client.get('/usuarios/', {'rol': 'empleado', 'page': 2})
        self.assertEqual(respuesta.context['page_obj'].number, 2)
        self.assertContains(respuesta, 'rol=empleado')
        self.client.force_login(self.empleado)
        for path in ('/usuarios/', '/compras/', '/proveedores/'):
            self.assertEqual(self.client.get(path, {'q': 'cualquiera'}).status_code, 403)
