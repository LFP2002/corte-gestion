from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.urls import reverse

from gestion.models import Compra, DetalleCompra, MovimientoStock
from .base import BaseNegocio


class ComprasTests(BaseNegocio):
    def test_redondeo_por_linea(self):
        compra = self.compra(cantidad='1.125', precio='2.50')
        self.assertEqual(compra.total, Decimal('2.81'))

    def test_cantidades_y_precios_invalidos(self):
        for cantidad, precio in [('0', '2'), ('-1', '2'), ('1', '0'), ('1.0001', '2'), ('1', '-2')]:
            with self.assertRaises(ValidationError):
                self.compra(cantidad, precio)
        self.assertFalse(Compra.objects.exists())

    def test_rollback_fallo_posterior_al_stock(self):
        with patch('gestion.services.MovimientoStock.objects.create', side_effect=RuntimeError('fallo simulado')):
            with self.assertRaises(RuntimeError):
                self.compra()
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 0)
        self.assertEqual(Compra.objects.count(), 0)
        self.assertEqual(DetalleCompra.objects.count(), 0)
        self.assertEqual(MovimientoStock.objects.count(), 0)

    def test_compra_http(self):
        self.client.force_login(self.dueno)
        respuesta = self.client.post(reverse('gestion:compra_crear'), {
            'proveedor': self.proveedor.pk, 'fecha': '2026-11-08', 'referencia': 'Guía',
            'lineas-TOTAL_FORMS': '1', 'lineas-INITIAL_FORMS': '0',
            'lineas-0-producto': self.producto.pk, 'lineas-0-cantidad': '12', 'lineas-0-precio_unitario': '5000',
        })
        self.assertEqual(respuesta.status_code, 302)
        self.assertContains(self.client.get(respuesta.url), '60000')

    def test_empleado_no_compra(self):
        self.client.force_login(self.empleado)
        for nombre in ['compras', 'compra_crear']:
            self.assertEqual(self.client.get(reverse('gestion:' + nombre)).status_code, 403)
        self.assertEqual(self.client.post(reverse('gestion:compra_crear'), {}).status_code, 403)
