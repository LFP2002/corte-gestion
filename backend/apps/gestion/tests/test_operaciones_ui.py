"""Pruebas de la presentación progresiva de las operaciones comerciales."""
from datetime import date
from decimal import Decimal

from django.urls import reverse

from apps.gestion.models import DetalleCompra, DetalleVenta, Producto
from apps.gestion.services import registrar_compra
from .base import BaseVentas


class FormulariosOperacionesTests(BaseVentas):
    def test_compra_y_venta_muestran_una_linea_sin_checkbox_y_cancelar(self):
        self.client.force_login(self.dueno)
        for ruta, vuelta, etiqueta in (
            ('gestion:compra_crear', 'gestion:compras', 'compra'),
            ('gestion:venta_crear', 'gestion:ventas', 'venta'),
        ):
            with self.subTest(ruta=ruta):
                respuesta = self.client.get(reverse(ruta))
                self.assertEqual(respuesta.status_code, 200)
                html = respuesta.content.decode()
                # El formulario inicial contiene una línea; la plantilla de JS no
                # es una línea visible hasta que se pulsa Agregar otro producto.
                self.assertEqual(html.split('<template id="linea-vacia">')[0].count('data-linea'), 1)
                self.assertContains(respuesta, 'id="agregar"')
                self.assertContains(respuesta, 'Agregar otro producto')
                self.assertContains(respuesta, 'Quitar producto')
                self.assertContains(respuesta, 'name="lineas-0-DELETE"')
                self.assertNotContains(respuesta, 'type="checkbox" name="lineas-0-DELETE"')
                self.assertContains(respuesta, f'href="{reverse(vuelta)}">Cancelar</a>')
                self.assertNotContains(respuesta, 'Marque «Eliminar»')
                self.assertNotContains(respuesta, 'Una confirmación guarda la operación')

    def test_cancelar_catalogo_es_boton_secundario(self):
        self.client.force_login(self.dueno)
        for tipo in ('productos', 'proveedores'):
            respuesta = self.client.get(reverse('gestion:catalogo_crear', args=[tipo]))
            self.assertContains(
                respuesta,
                f'class="btn sec" href="{reverse("gestion:catalogo", args=[tipo])}">Cancelar</a>',
            )

    def test_compra_con_linea_eliminada_no_agrega_sus_productos(self):
        otro = Producto.objects.create(nombre='Lomo', precio_venta=9000)
        self.client.force_login(self.dueno)
        respuesta = self.client.post(reverse('gestion:compra_crear'), {
            'proveedor': self.proveedor.pk, 'fecha': '2026-11-08', 'referencia': '',
            'lineas-TOTAL_FORMS': '3', 'lineas-INITIAL_FORMS': '0',
            'lineas-0-producto': self.producto.pk, 'lineas-0-cantidad': '2',
            'lineas-0-precio_unitario': '5000',
            'lineas-1-producto': '', 'lineas-1-cantidad': '',
            'lineas-1-precio_unitario': '', 'lineas-1-DELETE': 'on',
            'lineas-2-producto': otro.pk, 'lineas-2-cantidad': '1',
            'lineas-2-precio_unitario': '3000',
        })
        self.assertEqual(respuesta.status_code, 302)
        compra = self.producto.detallecompra_set.order_by('-pk').first().compra
        self.assertEqual(compra.total, Decimal('13000'))
        self.assertEqual(compra.detalles.count(), 2)
        self.producto.refresh_from_db()
        otro.refresh_from_db()
        self.assertEqual(self.producto.stock, Decimal('14'))
        self.assertEqual(otro.stock, Decimal('1'))

    def test_venta_con_linea_eliminada_no_descuenta_stock(self):
        otro = Producto.objects.create(nombre='Lomo', precio_venta=9000)
        registrar_compra(
            usuario=self.dueno, proveedor=self.proveedor,
            fecha=date(2026, 11, 8),
            lineas=[self.linea('4', '5000', otro)],
        )
        self.client.force_login(self.empleado)
        respuesta = self.client.post(reverse('gestion:venta_crear'), {
            'fecha': '2026-11-08',
            'lineas-TOTAL_FORMS': '3', 'lineas-INITIAL_FORMS': '0',
            'lineas-0-producto': self.producto.pk, 'lineas-0-cantidad': '2',
            'lineas-0-precio_unitario': '8000',
            'lineas-1-producto': '', 'lineas-1-cantidad': '',
            'lineas-1-precio_unitario': '', 'lineas-1-DELETE': 'on',
            'lineas-2-producto': otro.pk, 'lineas-2-cantidad': '1',
            'lineas-2-precio_unitario': '9000',
        })
        self.assertEqual(respuesta.status_code, 302)
        detalle = DetalleVenta.objects.get(producto=otro)
        self.assertEqual(detalle.venta.total, Decimal('25000'))
        self.assertEqual(DetalleVenta.objects.filter(venta=detalle.venta).count(), 2)
        self.producto.refresh_from_db()
        otro.refresh_from_db()
        self.assertEqual(self.producto.stock, Decimal('10'))
        self.assertEqual(otro.stock, Decimal('3'))

    def test_todas_las_lineas_eliminadas_son_rechazadas(self):
        self.client.force_login(self.dueno)
        respuesta = self.client.post(reverse('gestion:compra_crear'), {
            'proveedor': self.proveedor.pk, 'fecha': '2026-11-08',
            'lineas-TOTAL_FORMS': '1', 'lineas-INITIAL_FORMS': '0',
            'lineas-0-DELETE': 'on',
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.context['lineas'].non_form_errors())
        self.assertEqual(DetalleCompra.objects.count(), 1)

    def test_errores_de_linea_mantienen_campos_y_boton_cancelar(self):
        self.client.force_login(self.empleado)
        respuesta = self.client.post(reverse('gestion:venta_crear'), {
            'fecha': '2026-11-08',
            'lineas-TOTAL_FORMS': '1', 'lineas-INITIAL_FORMS': '0',
            'lineas-0-producto': self.producto.pk, 'lineas-0-cantidad': '9999',
            'lineas-0-precio_unitario': '8000',
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, '9999')
        self.assertContains(respuesta, reverse('gestion:ventas'))
