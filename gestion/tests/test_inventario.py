from decimal import Decimal

from django.db.models.deletion import ProtectedError
from django.urls import reverse

from gestion.models import Compra, MovimientoStock, Producto, Venta
from .base import BaseNegocio, BaseVentas


class InventarioComprasTests(BaseNegocio):
    def test_compra_stock_total_y_persistencia(self):
        compra = self.compra(referencia='GUIA-001')
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, Decimal('12'))
        self.assertEqual(Compra.objects.get(pk=compra.pk).total, Decimal('60000'))
        self.assertEqual(compra.detalles.get().subtotal, Decimal('60000'))
        self.assertEqual(MovimientoStock.objects.get().saldo, Decimal('12'))

    def test_historial_protegido(self):
        compra = self.compra()
        for objeto in [self.producto, self.proveedor, self.dueno, compra, compra.detalles.get()]:
            with self.assertRaises(ProtectedError):
                objeto.delete()

    def test_no_cambia_unidad_con_historial(self):
        self.compra()
        self.client.force_login(self.dueno)
        respuesta = self.client.post(reverse('gestion:catalogo_editar', args=['productos', self.producto.pk]), {
            'nombre': self.producto.nombre, 'unidad': 'unidad', 'precio_venta': '8000', 'activo': 'on',
        })
        self.assertContains(respuesta, 'No cambie la unidad')
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.unidad, 'kg')
        self.assertEqual(self.producto.stock, 12)

    def test_eliminar_historial_muestra_error(self):
        self.compra()
        self.client.force_login(self.dueno)
        respuesta = self.client.post(reverse('gestion:catalogo_eliminar', args=['productos', self.producto.pk]), follow=True)
        self.assertContains(respuesta, 'Tiene historial')
        self.assertTrue(Producto.objects.filter(pk=self.producto.pk).exists())


class InventarioVentasTests(BaseVentas):
    def test_flujo_obligatorio_stock_9_5(self):
        venta = self.venta()
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, Decimal('9.5'))
        self.assertEqual(Venta.objects.get(pk=venta.pk).total, Decimal('20000'))
        movimiento = MovimientoStock.objects.get(detalle_venta__venta=venta)
        self.assertEqual(movimiento.cantidad, Decimal('-2.5'))
        self.assertEqual(movimiento.saldo, Decimal('9.5'))
