from datetime import date
from decimal import Decimal

from django.test import TestCase

from usuarios.models import Usuario
from gestion.models import Producto, Proveedor
from gestion.services import registrar_compra, registrar_venta


class BaseNegocio(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.dueno = Usuario.objects.create_user('dueno', 'dueno@example.test', 'Clave-test-934!', rol='dueno')
        cls.empleado = Usuario.objects.create_user('empleado', 'empleado@example.test', 'Clave-test-934!')
        cls.producto = Producto.objects.create(nombre='Posta rosada', unidad='kg', precio_venta=8000)
        cls.proveedor = Proveedor.objects.create(nombre='Frigorífico de prueba')

    def compra(self, cantidad='12', precio='5000', **kwargs):
        return registrar_compra(usuario=self.dueno, proveedor=self.proveedor, fecha=date(2026, 11, 8),
                                lineas=[self.linea(cantidad, precio)], **kwargs)

    def linea(self, cantidad='12', precio='5000', producto=None):
        return {'producto': producto or self.producto, 'cantidad': Decimal(cantidad), 'precio_unitario': Decimal(precio)}


class BaseVentas(BaseNegocio):
    def setUp(self):
        self.compra()

    def venta(self, cantidad='2.5', **kwargs):
        return registrar_venta(usuario=self.empleado, fecha=date(2026, 11, 8),
                               lineas=[self.linea(cantidad, '8000')], **kwargs)
