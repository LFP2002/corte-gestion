from datetime import date
from decimal import Decimal

from django.urls import reverse

from apps.gestion.models import Producto, Proveedor
from apps.gestion.reports import compras_por_proveedor, limites_periodo, productos_mas_vendidos
from apps.gestion.services import registrar_compra, registrar_venta
from .base import BaseNegocio


class ReportesTests(BaseNegocio):
    def setUp(self):
        self.compra()
        registrar_venta(usuario=self.empleado, fecha=date(2026, 11, 8), lineas=[self.linea('2.5', '8000')])
        registrar_venta(usuario=self.dueno, fecha=date(2026, 11, 9), lineas=[self.linea('1', '8000')])
        registrar_compra(usuario=self.dueno, proveedor=self.proveedor, fecha=date(2026, 12, 1), lineas=[self.linea('1')])

    def test_limites_semana_mes_y_cambio_de_ano(self):
        self.assertEqual(limites_periodo(date(2026, 11, 8), 'semana'), (date(2026, 11, 2), date(2026, 11, 9)))
        self.assertEqual(limites_periodo(date(2026, 12, 31), 'mes'), (date(2026, 12, 1), date(2027, 1, 1)))
        self.assertEqual(limites_periodo(date(2024, 2, 29), 'mes'), (date(2024, 2, 1), date(2024, 3, 1)))

    def test_compras_por_proveedor_mes_incluye_sin_compras(self):
        Proveedor.objects.create(nombre='Sin compras')
        datos = list(compras_por_proveedor(date(2026, 11, 1), date(2026, 12, 1)))
        self.assertEqual(datos[0].total_comprado, Decimal('60000'))
        self.assertEqual(datos[1].total_comprado, 0)

    def test_proveedor_muestra_compras_ultima_fecha_y_producto_por_importe(self):
        pernil = Producto.objects.create(nombre='Pernil', unidad='unidad', precio_venta=10000)
        registrar_compra(
            usuario=self.dueno, proveedor=self.proveedor, fecha=date(2026, 11, 10),
            lineas=[self.linea('2', '45000', pernil)],
        )
        registrar_compra(
            usuario=self.dueno, proveedor=self.proveedor, fecha=date(2026, 11, 12),
            lineas=[self.linea('1', '10000', pernil)],
        )
        Proveedor.objects.create(nombre='Sin compras')
        with self.assertNumQueries(1):
            datos = list(compras_por_proveedor(date(2026, 11, 1), date(2026, 12, 1)))
        self.assertEqual(datos[0].nombre, self.proveedor.nombre)
        self.assertEqual(datos[0].total_comprado, Decimal('160000'))
        self.assertEqual(datos[0].cantidad_compras, 3)
        self.assertEqual(datos[0].ultima_compra, date(2026, 11, 12))
        self.assertEqual(datos[0].producto_destacado, 'Pernil')
        self.assertEqual(datos[1].cantidad_compras, 0)
        self.assertIsNone(datos[1].ultima_compra)
        self.assertIsNone(datos[1].producto_destacado)
        diciembre = list(compras_por_proveedor(date(2026, 12, 1), date(2027, 1, 1)))
        self.assertEqual(diciembre[0].total_comprado, Decimal('5000'))
        self.assertEqual(diciembre[0].cantidad_compras, 1)
        self.assertEqual(diciembre[0].producto_destacado, 'Posta rosada')

    def test_reportes_html_incluye_nuevas_columnas_y_campos_alineados(self):
        self.client.force_login(self.dueno)
        respuesta = self.client.get(reverse('gestion:reportes'), {'periodo': 'mes', 'fecha': '2026-11-12'})
        self.assertContains(respuesta, 'class="card reporte-form"')
        self.assertContains(respuesta, 'Producto más comprado')
        self.assertContains(respuesta, 'Última compra')
        self.assertContains(respuesta, 'Compras')
        self.assertContains(respuesta, '08-11-2026')
        self.assertContains(respuesta, 'Posta rosada')
        self.assertContains(respuesta, 'importe acumulado')
        self.assertContains(respuesta, '$60.000')

    def test_ventas_por_semana_y_mes(self):
        semana = list(productos_mas_vendidos(date(2026, 11, 2), date(2026, 11, 9)))
        mes = list(productos_mas_vendidos(date(2026, 11, 1), date(2026, 12, 1)))
        self.assertEqual(semana[0]['cantidad_vendida'], Decimal('2.5'))
        self.assertEqual(mes[0]['cantidad_vendida'], Decimal('3.5'))
        self.assertEqual(mes[0]['total_vendido'], Decimal('28000'))

    def test_ranking_ordenado_por_cantidad(self):
        otro = Producto.objects.create(nombre='Lomo', precio_venta=9000)
        registrar_compra(usuario=self.dueno, proveedor=self.proveedor, fecha=date(2026, 11, 8), lineas=[self.linea('10', producto=otro)])
        registrar_venta(usuario=self.dueno, fecha=date(2026, 11, 8), lineas=[self.linea('5', producto=otro)])
        ranking = list(productos_mas_vendidos(date(2026, 11, 1), date(2026, 12, 1)))
        self.assertEqual([p['producto__nombre'] for p in ranking], ['Lomo', 'Posta rosada'])

    def test_http_reportes_y_fecha_invalida(self):
        self.client.force_login(self.dueno)
        respuesta = self.client.get(reverse('gestion:reportes'), {'periodo': 'semana', 'fecha': '2026-11-08'})
        self.assertContains(respuesta, '$60.000')
        self.assertContains(respuesta, 'Posta rosada')
        self.assertEqual(list(respuesta.context['productos'])[0]['cantidad_vendida'], Decimal('2.5'))
        invalida = self.client.get(reverse('gestion:reportes'), {'periodo': 'mes', 'fecha': 'incorrecta'})
        self.assertTrue(invalida.context['form'].errors)
        self.client.force_login(self.empleado)
        self.assertEqual(self.client.get(reverse('gestion:reportes')).status_code, 403)
