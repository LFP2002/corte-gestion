from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from threading import Barrier

from django.core.exceptions import ValidationError
from django.db import close_old_connections, connection
from django.test import TransactionTestCase, skipUnlessDBFeature

from usuarios.models import Usuario
from gestion.models import MovimientoStock, Producto, Proveedor, Venta
from gestion.services import registrar_compra, registrar_venta


class ConcurrenciaMariaDBTests(TransactionTestCase):
    @skipUnlessDBFeature('has_select_for_update')
    def test_dos_ventas_no_consumen_el_mismo_stock(self):
        usuario = Usuario.objects.create_user('jefe', 'jefe@example.test', rol='dueno')
        producto = Producto.objects.create(nombre='Posta rosada', precio_venta=8000)
        proveedor = Proveedor.objects.create(nombre='Proveedor')
        registrar_compra(usuario=usuario, proveedor=proveedor, fecha=date.today(), lineas=[
            {'producto': producto, 'cantidad': Decimal('12'), 'precio_unitario': Decimal('5000')},
        ])
        barrera = Barrier(2)

        def vender():
            close_old_connections()
            try:
                barrera.wait(timeout=10)
                registrar_venta(usuario=usuario, fecha=date.today(), lineas=[
                    {'producto': producto, 'cantidad': Decimal('8'), 'precio_unitario': Decimal('8000')},
                ])
                return 'confirmada'
            except ValidationError:
                return 'rechazada'
            finally:
                connection.close()

        with ThreadPoolExecutor(max_workers=2) as pool:
            resultados = list(pool.map(lambda _: vender(), range(2)))
        self.assertCountEqual(resultados, ['confirmada', 'rechazada'])
        producto.refresh_from_db()
        self.assertEqual(producto.stock, Decimal('4'))
        self.assertEqual(Venta.objects.count(), 1)
        self.assertEqual(MovimientoStock.objects.count(), 2)
