from datetime import date

from django.core.exceptions import PermissionDenied
from django.urls import reverse

from gestion.models import Compra
from gestion.services import registrar_compra, registrar_venta
from .base import BaseNegocio


class SeguridadYVistasTests(BaseNegocio):
    def test_todas_las_pantallas_dueno(self):
        self.client.force_login(self.dueno)
        for nombre in ['inicio', 'gestion:compras', 'gestion:compra_crear', 'gestion:ventas', 'gestion:venta_crear',
                       'gestion:stock', 'gestion:reportes', 'usuario_crear']:
            with self.subTest(nombre=nombre):
                self.assertEqual(self.client.get(reverse(nombre)).status_code, 200)

    def test_csrf_en_operaciones(self):
        from django.test import Client
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.dueno)
        for nombre in ['gestion:compra_crear', 'gestion:venta_crear', 'usuario_crear']:
            self.assertEqual(cliente.post(reverse(nombre), {}).status_code, 403)

    def test_servicios_validan_roles(self):
        with self.assertRaises(PermissionDenied):
            registrar_compra(usuario=self.empleado, proveedor=self.proveedor, fecha=date.today(), lineas=[self.linea()])
        self.empleado.is_active = False
        with self.assertRaises(PermissionDenied):
            registrar_venta(usuario=self.empleado, fecha=date.today(), lineas=[self.linea()])

    def test_campos_invalidos_en_formulario(self):
        self.client.force_login(self.dueno)
        respuesta = self.client.post(reverse('gestion:compra_crear'), {
            'proveedor': self.proveedor.pk, 'fecha': '2026-11-08',
            'lineas-TOTAL_FORMS': '1', 'lineas-INITIAL_FORMS': '0',
            'lineas-0-producto': self.producto.pk, 'lineas-0-cantidad': '-1', 'lineas-0-precio_unitario': '0',
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.context['lineas'].errors)
        self.assertFalse(Compra.objects.exists())
