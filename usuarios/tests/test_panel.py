from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from gestion.models import Producto, Proveedor
from gestion.services import registrar_compra, registrar_venta
from usuarios.models import Usuario


class PanelInicioTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.dueno = Usuario.objects.create_user('dueno', 'dueno@example.test', 'Clave-test-934!', rol='dueno')
        cls.empleado = Usuario.objects.create_user('cajero', 'cajero@example.test', 'Clave-test-934!', rol='empleado')
        cls.producto = Producto.objects.create(nombre='Posta rosada', precio_venta=Decimal('8000'))
        Producto.objects.create(nombre='Pernil', precio_venta=Decimal('6000'))
        Producto.objects.create(nombre='Fuera de venta', precio_venta=Decimal('5000'), activo=False)
        proveedor = Proveedor.objects.create(nombre='Proveedor de prueba')
        hoy = timezone.localdate()
        registrar_compra(usuario=cls.dueno, proveedor=proveedor, fecha=hoy, lineas=[
            {'producto': cls.producto, 'cantidad': Decimal('12'), 'precio_unitario': Decimal('5000')},
        ])
        registrar_venta(usuario=cls.dueno, fecha=hoy, lineas=[
            {'producto': cls.producto, 'cantidad': Decimal('1'), 'precio_unitario': Decimal('8000')},
        ])
        registrar_venta(usuario=cls.empleado, fecha=hoy, lineas=[
            {'producto': cls.producto, 'cantidad': Decimal('2'), 'precio_unitario': Decimal('8000')},
        ])

    def test_dueno_ve_indicadores_totales(self):
        self.client.force_login(self.dueno)
        respuesta = self.client.get(reverse('inicio'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context['productos_activos'], 2)
        self.assertEqual(respuesta.context['productos_agotados'], 1)
        self.assertEqual(respuesta.context['ventas_hoy'], 2)
        self.assertEqual(respuesta.context['monto_ventas_hoy'], Decimal('24000'))
        self.assertContains(respuesta, '$24.000')

    def test_empleado_solo_ve_sus_ventas(self):
        self.client.force_login(self.empleado)
        respuesta = self.client.get(reverse('inicio'))
        self.assertEqual(respuesta.context['ventas_hoy'], 1)
        self.assertEqual(respuesta.context['monto_ventas_hoy'], Decimal('16000'))
        self.assertContains(respuesta, '$16.000')
        self.assertNotContains(respuesta, '$24.000')
        self.assertNotContains(respuesta, 'Administrar cuentas y roles.')

    def test_sin_ventas_de_hoy_muestra_cero(self):
        self.client.force_login(self.dueno)
        from gestion.models import Venta
        Venta.objects.all().update(fecha=date(2025, 1, 1))
        respuesta = self.client.get(reverse('inicio'))
        self.assertEqual(respuesta.context['ventas_hoy'], 0)
        self.assertEqual(respuesta.context['monto_ventas_hoy'], Decimal('0'))
        self.assertContains(respuesta, '$0')
