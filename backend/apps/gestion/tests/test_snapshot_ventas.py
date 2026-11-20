from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from threading import Barrier
from unittest.mock import patch

from django.core.exceptions import PermissionDenied
from django.db import close_old_connections, connections
from django.test import TransactionTestCase
from django.urls import reverse

from apps.gestion.models import DetalleVenta, MovimientoStock, Producto, Proveedor, Venta
from apps.gestion.services import registrar_compra, registrar_venta
from apps.gestion.statistics import ranking_empleados
from apps.usuarios.models import Usuario
from .base import BaseVentas


class SnapshotVentaTests(BaseVentas):
    def test_servicio_registra_rol_real_y_no_lo_cambia_con_el_usuario(self):
        venta = self.venta('1')
        self.assertEqual(venta.rol_vendedor_al_registrar, 'empleado')
        Usuario.objects.filter(pk=self.empleado.pk).update(rol='dueno')
        # La instancia de sesión está obsoleta; debe leerse el usuario de MariaDB.
        otra = self.venta('1')
        self.assertEqual(otra.rol_vendedor_al_registrar, 'dueno')
        venta.refresh_from_db()
        self.assertEqual(venta.rol_vendedor_al_registrar, 'empleado')
        ranking = list(ranking_empleados(date(2026, 11, 1)))
        self.assertEqual(ranking[0]['cantidad_ventas'], 1)
        self.assertEqual(ranking[0]['total_vendido'], Decimal('8000'))

    def test_dueno_que_pasa_a_empleado_no_reclasifica_ventas_previas(self):
        venta = registrar_venta(usuario=self.dueno, fecha=date(2026, 11, 8), lineas=[self.linea('1', '8000')])
        Usuario.objects.create_user('otro_dueno', 'otro@example.test', rol='dueno')
        Usuario.objects.filter(pk=self.dueno.pk).update(rol='empleado')
        otra = registrar_venta(usuario=self.dueno, fecha=date(2026, 12, 1), lineas=[self.linea('1', '8000')])
        self.assertEqual(venta.rol_vendedor_al_registrar, 'dueno')
        self.assertEqual(otra.rol_vendedor_al_registrar, 'empleado')
        self.assertEqual(list(ranking_empleados(date(2026, 11, 1))), [])
        self.assertEqual(list(ranking_empleados(date(2026, 12, 1)))[0]['usuario_id'], self.dueno.pk)

    def test_snapshot_no_se_acepta_del_formulario_http(self):
        self.client.force_login(self.empleado)
        respuesta = self.client.post(reverse('gestion:venta_crear'), {
            'fecha': '2026-11-08', 'rol_vendedor_al_registrar': 'dueno',
            'lineas-TOTAL_FORMS': '1', 'lineas-INITIAL_FORMS': '0',
            'lineas-0-producto': self.producto.pk, 'lineas-0-cantidad': '1',
            'lineas-0-precio_unitario': '8000',
        })
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(Venta.objects.get().rol_vendedor_al_registrar, 'empleado')

    def test_snapshot_y_venta_se_revierten_con_fallo_de_stock(self):
        with patch('apps.gestion.services.MovimientoStock.objects.create', side_effect=RuntimeError('fallo simulado')):
            with self.assertRaises(RuntimeError):
                self.venta('1')
        self.assertFalse(Venta.objects.exists())
        self.assertFalse(DetalleVenta.objects.exists())
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 12)
        self.assertEqual(MovimientoStock.objects.count(), 1)

    def test_usuario_desactivado_con_instancia_obsoleta_no_registra_venta(self):
        Usuario.objects.filter(pk=self.empleado.pk).update(is_active=False)
        with self.assertRaises(PermissionDenied):
            self.venta('1')
        self.assertFalse(Venta.objects.exists())


class SnapshotConcurrenteTests(TransactionTestCase):
    def setUp(self):
        self.dueno = Usuario.objects.create_user('jefe', 'jefe@example.test', rol='dueno')
        self.empleado = Usuario.objects.create_user('caja', 'caja@example.test')
        self.producto = Producto.objects.create(nombre='Carne', precio_venta=100)
        proveedor = Proveedor.objects.create(nombre='Proveedor')
        registrar_compra(usuario=self.dueno, proveedor=proveedor, fecha=date(2026, 11, 8), lineas=[
            {'producto': self.producto, 'cantidad': Decimal('12'), 'precio_unitario': Decimal('100')},
        ])

    def test_dos_vendedores_simultaneos_conservan_rol_y_stock(self):
        barrera = Barrier(2)

        def vender(usuario):
            close_old_connections()
            try:
                barrera.wait(timeout=15)
                venta = registrar_venta(usuario=usuario, fecha=date(2026, 11, 8), lineas=[
                    {'producto': self.producto, 'cantidad': Decimal('1'), 'precio_unitario': Decimal('100')},
                ])
                return venta.usuario_id, venta.rol_vendedor_al_registrar
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            resultados = list(pool.map(vender, [self.dueno, self.empleado]))
        self.assertCountEqual(resultados, [(self.dueno.pk, 'dueno'), (self.empleado.pk, 'empleado')])
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 10)
        self.assertEqual(Venta.objects.count(), 2)
        self.assertEqual(DetalleVenta.objects.count(), 2)
        self.assertEqual(MovimientoStock.objects.count(), 3)
        ranking = list(ranking_empleados(date(2026, 11, 1)))
        self.assertEqual(len(ranking), 1)
        self.assertEqual(ranking[0]['usuario_id'], self.empleado.pk)
        self.assertEqual(ranking[0]['total_vendido'], 100)
