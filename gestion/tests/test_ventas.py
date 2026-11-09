from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.urls import reverse

from gestion.models import DetalleVenta, MovimientoStock, Producto, Venta
from gestion.services import registrar_compra, registrar_venta
from .base import BaseVentas


class VentasTests(BaseVentas):
    def test_no_sobreventa(self):
        with self.assertRaisesMessage(ValidationError, 'Stock insuficiente'):
            self.venta('12.001')
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, Decimal('12'))
        self.assertEqual(Venta.objects.count(), 0)

    def test_operacion_varios_productos_y_total(self):
        otro = Producto.objects.create(nombre='Lomo', precio_venta=9000)
        registrar_compra(usuario=self.dueno, proveedor=self.proveedor, fecha=date(2026, 11, 8),
                         lineas=[self.linea('5', '5000', otro)])
        venta = registrar_venta(usuario=self.dueno, fecha=date(2026, 11, 8),
                                lineas=[self.linea('2.5', '8000'), self.linea('1', '9000', otro)])
        self.assertEqual(venta.total, Decimal('29000'))
        self.assertEqual(venta.detalles.count(), 2)
        otro.refresh_from_db()
        self.assertEqual(otro.stock, 4)

    def test_rollback_segunda_linea_sin_stock(self):
        otro = Producto.objects.create(nombre='Sin stock', precio_venta=9000)
        with self.assertRaises(ValidationError):
            registrar_venta(usuario=self.dueno, fecha=date(2026, 11, 8),
                            lineas=[self.linea('1'), self.linea('1', producto=otro)])
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 12)
        self.assertFalse(Venta.objects.exists())
        self.assertFalse(DetalleVenta.objects.exists())

    def test_rollback_fallo_despues_de_descontar(self):
        with patch('gestion.services.MovimientoStock.objects.create', side_effect=RuntimeError('fallo simulado')):
            with self.assertRaises(RuntimeError):
                self.venta()
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 12)
        self.assertEqual(Venta.objects.count(), 0)
        self.assertEqual(DetalleVenta.objects.count(), 0)
        self.assertEqual(MovimientoStock.objects.count(), 1)

    def test_venta_http_coma_decimal_y_persistencia_get(self):
        self.client.force_login(self.empleado)
        respuesta = self.client.post(reverse('gestion:venta_crear'), {
            'fecha': '2026-11-08', 'lineas-TOTAL_FORMS': '1', 'lineas-INITIAL_FORMS': '0',
            'lineas-0-producto': self.producto.pk, 'lineas-0-cantidad': '2,5', 'lineas-0-precio_unitario': '8000',
        })
        self.assertEqual(respuesta.status_code, 302)
        for _ in range(2):
            self.assertContains(self.client.get(respuesta.url), '$20.000')
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, Decimal('9.5'))

    def test_empleado_consulta_historial_completo_y_detalle_ajeno(self):
        venta_dueno = registrar_venta(
            usuario=self.dueno, fecha=date(2026, 11, 8),
            lineas=[self.linea('1', '8000')],
        )
        venta_propia = self.venta('2')
        self.client.force_login(self.empleado)

        respuesta = self.client.get(reverse('gestion:ventas'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            {venta.pk for venta in respuesta.context['objetos']},
            {venta_dueno.pk, venta_propia.pk},
        )
        self.assertContains(respuesta, reverse('gestion:venta_detalle', args=[venta_dueno.pk]))
        self.assertContains(respuesta, reverse('gestion:venta_detalle', args=[venta_propia.pk]))
        self.assertContains(respuesta, 'dueno')
        self.assertContains(respuesta, 'empleado')

        detalle = self.client.get(reverse('gestion:venta_detalle', args=[venta_dueno.pk]))
        self.assertEqual(detalle.status_code, 200)
        self.assertContains(detalle, '$8.000')
        self.assertContains(detalle, 'dueno')
        self.assertContains(self.client.get(reverse('gestion:venta_detalle', args=[venta_propia.pk])), '$16.000')
        self.assertEqual(Venta.objects.count(), 2)

    def test_acceso_de_empleado_sigue_restringido_a_consulta_comercial(self):
        venta = registrar_venta(
            usuario=self.dueno, fecha=date(2026, 11, 8),
            lineas=[self.linea('1', '8000')],
        )
        self.client.force_login(self.empleado)
        self.assertEqual(self.client.get(reverse('gestion:venta_detalle', args=[venta.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse('gestion:compras')).status_code, 403)
        self.assertEqual(self.client.get(reverse('gestion:reportes')).status_code, 403)
        self.assertEqual(self.client.get(reverse('gestion:compra_crear')).status_code, 403)
        self.assertEqual(Venta.objects.count(), 1)

    def test_producto_inactivo_y_duplicado(self):
        with self.assertRaises(ValidationError):
            registrar_venta(usuario=self.dueno, fecha=date(2026, 11, 8), lineas=[self.linea('1'), self.linea('2')])
        self.producto.activo = False
        self.producto.save()
        with self.assertRaises(ValidationError):
            self.venta()
