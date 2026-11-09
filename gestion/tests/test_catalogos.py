from django.urls import reverse

from gestion.models import Producto, Proveedor
from .base import BaseNegocio


class CatalogosTests(BaseNegocio):
    def test_crud_producto(self):
        self.client.force_login(self.dueno)
        url = reverse('gestion:catalogo_crear', args=['productos'])
        self.assertEqual(self.client.post(url, {'nombre': 'Lomo', 'unidad': 'kg', 'precio_venta': '9000', 'activo': 'on'}).status_code, 302)
        producto = Producto.objects.get(nombre='Lomo')
        self.assertContains(self.client.get(reverse('gestion:catalogo', args=['productos'])), 'Lomo')
        self.client.post(reverse('gestion:catalogo_editar', args=['productos', producto.pk]), {
            'nombre': 'Lomo vetado', 'unidad': 'kg', 'precio_venta': '9500', 'activo': 'on', 'stock': '999',
        })
        producto.refresh_from_db()
        self.assertEqual(producto.nombre, 'Lomo vetado')
        self.assertEqual(producto.stock, 0)
        self.client.post(reverse('gestion:catalogo_eliminar', args=['productos', producto.pk]))
        self.assertFalse(Producto.objects.filter(pk=producto.pk).exists())

    def test_crud_proveedor(self):
        self.client.force_login(self.dueno)
        self.client.post(reverse('gestion:catalogo_crear', args=['proveedores']), {'nombre': 'Proveedor nuevo', 'activo': 'on'})
        proveedor = Proveedor.objects.get(nombre='Proveedor nuevo')
        self.assertContains(self.client.get(reverse('gestion:catalogo', args=['proveedores'])), 'Proveedor nuevo')
        self.client.post(reverse('gestion:catalogo_editar', args=['proveedores', proveedor.pk]), {'nombre': 'Proveedor editado', 'activo': 'on'})
        proveedor.refresh_from_db()
        self.assertEqual(proveedor.nombre, 'Proveedor editado')
        self.client.post(reverse('gestion:catalogo_eliminar', args=['proveedores', proveedor.pk]))
        self.assertFalse(Proveedor.objects.filter(pk=proveedor.pk).exists())

    def test_empleado_solo_consulta_productos(self):
        self.client.force_login(self.empleado)
        self.assertEqual(self.client.get(reverse('gestion:catalogo', args=['productos'])).status_code, 200)
        self.assertEqual(self.client.get(reverse('gestion:stock')).status_code, 200)
        for tipo in ['productos', 'proveedores']:
            self.assertEqual(self.client.post(reverse('gestion:catalogo_crear', args=[tipo]), {}).status_code, 403)
            self.assertEqual(self.client.post(reverse('gestion:catalogo_editar', args=[tipo, 1]), {}).status_code, 403)
            self.assertEqual(self.client.post(reverse('gestion:catalogo_eliminar', args=[tipo, 1]), {}).status_code, 403)
        self.assertEqual(self.client.get(reverse('gestion:catalogo', args=['proveedores'])).status_code, 403)
