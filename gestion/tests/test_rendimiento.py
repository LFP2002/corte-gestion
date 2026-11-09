"""Medición informativa de POSTs; no valida por sí sola el RNF2 humano."""
from datetime import date
from decimal import Decimal
from statistics import median
from time import perf_counter

from django.test import TestCase
from django.urls import reverse

from usuarios.models import Usuario
from gestion.models import Producto, Proveedor


class MedicionOperacionesTests(TestCase):
    def test_medicion_post_compra_y_venta(self):
        usuario = Usuario.objects.create_user('medicion', 'medicion@example.test', rol='dueno')
        proveedor = Proveedor.objects.create(nombre='Medición')
        productos = [Producto.objects.create(nombre=f'Producto {i}', precio_venta=Decimal('8000')) for i in range(20)]
        self.client.force_login(usuario)
        for cantidad in [1, 5, 20]:
            datos = {'fecha': date.today().isoformat(), 'proveedor': proveedor.pk,
                     'lineas-TOTAL_FORMS': str(cantidad), 'lineas-INITIAL_FORMS': '0'}
            for i, producto in enumerate(productos[:cantidad]):
                datos.update({f'lineas-{i}-producto': producto.pk,
                              f'lineas-{i}-cantidad': '1', f'lineas-{i}-precio_unitario': '8000'})
            tiempos = {'compra': [], 'venta': []}
            for _ in range(5):
                for tipo in ['compra', 'venta']:
                    inicio = perf_counter()
                    respuesta = self.client.post(reverse(f'gestion:{tipo}_crear'), datos)
                    tiempos[tipo].append((perf_counter() - inicio) * 1000)
                    self.assertEqual(respuesta.status_code, 302)
            for tipo, valores in tiempos.items():
                print(f'POST {tipo}, {cantidad} líneas, n=5: mediana={median(valores):.1f} ms, máximo={max(valores):.1f} ms')
