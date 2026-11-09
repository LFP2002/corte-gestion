from decimal import Decimal

from django.urls import reverse

from gestion.models import Producto
from .base import BaseNegocio


class InterfazGestionTests(BaseNegocio):
    def test_catalogo_muestra_precio_clp_y_nombre_especifico(self):
        self.client.force_login(self.dueno)
        respuesta = self.client.get(reverse('gestion:catalogo', args=['productos']))
        self.assertContains(respuesta, '$8.000')
        self.assertContains(respuesta, 'Nuevo producto')
        self.assertNotContains(respuesta, 'Página 1 de 1')

    def test_inventario_distingue_agotado_disponible_inactivo(self):
        self.compra()
        Producto.objects.create(nombre='Pernil', precio_venta=Decimal('7000'))
        Producto.objects.create(nombre='Fuera de venta', precio_venta=Decimal('7000'), activo=False)
        self.client.force_login(self.dueno)
        respuesta = self.client.get(reverse('gestion:stock'))
        self.assertContains(respuesta, 'Disponible')
        self.assertContains(respuesta, 'Agotado')
        self.assertContains(respuesta, 'Inactivo')
        self.assertNotContains(respuesta, 'Página 1 de 1')

    def test_historial_compra_muestra_encabezado_y_moneda(self):
        self.compra()
        self.client.force_login(self.dueno)
        respuesta = self.client.get(reverse('gestion:compras'))
        self.assertContains(respuesta, 'Proveedor')
        self.assertContains(respuesta, '$60.000')
        self.assertNotContains(respuesta, 'Proveedor / usuario')
