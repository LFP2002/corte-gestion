from datetime import date

from django.urls import reverse

from gestion.services import registrar_venta
from .base import BaseNegocio


class NavegacionActivaTests(BaseNegocio):
    """La selección identifica la sección, incluso en formularios y detalles."""

    def comprobar_seccion(self, url, seccion_url):
        respuesta = self.client.get(url)
        self.assertEqual(respuesta.status_code, 200, url)
        self.assertContains(respuesta, 'aria-current="page"', count=1)
        self.assertContains(
            respuesta,
            f'href="{seccion_url}" class="activo" aria-current="page"',
            count=1,
        )
        self.assertContains(respuesta, 'aria-label="Navegación principal"')

    def test_dueno_tiene_una_unica_seccion_activa(self):
        compra = self.compra()
        venta = registrar_venta(
            usuario=self.dueno,
            fecha=date(2026, 11, 8),
            lineas=[self.linea('1', '8000')],
        )
        rutas = [
            ('inicio', [], 'inicio', []),
            ('gestion:catalogo', ['productos'], 'gestion:catalogo', ['productos']),
            ('gestion:catalogo_crear', ['productos'], 'gestion:catalogo', ['productos']),
            ('gestion:catalogo_editar', ['productos', self.producto.pk], 'gestion:catalogo', ['productos']),
            ('gestion:catalogo_eliminar', ['productos', self.producto.pk], 'gestion:catalogo', ['productos']),
            ('gestion:catalogo', ['proveedores'], 'gestion:catalogo', ['proveedores']),
            ('gestion:catalogo_crear', ['proveedores'], 'gestion:catalogo', ['proveedores']),
            ('gestion:catalogo_editar', ['proveedores', self.proveedor.pk], 'gestion:catalogo', ['proveedores']),
            ('gestion:catalogo_eliminar', ['proveedores', self.proveedor.pk], 'gestion:catalogo', ['proveedores']),
            ('gestion:ventas', [], 'gestion:ventas', []),
            ('gestion:venta_crear', [], 'gestion:ventas', []),
            ('gestion:venta_detalle', [venta.pk], 'gestion:ventas', []),
            ('gestion:stock', [], 'gestion:stock', []),
            ('gestion:compras', [], 'gestion:compras', []),
            ('gestion:compra_crear', [], 'gestion:compras', []),
            ('gestion:compra_detalle', [compra.pk], 'gestion:compras', []),
            ('gestion:reportes', [], 'gestion:reportes', []),
            ('usuario_lista', [], 'usuario_lista', []),
            ('usuario_crear', [], 'usuario_lista', []),
            ('usuario_editar', [self.dueno.pk], 'usuario_lista', []),
            ('usuario_eliminar', [self.dueno.pk], 'usuario_lista', []),
        ]
        self.client.force_login(self.dueno)
        for vista, argumentos, seccion, argumentos_seccion in rutas:
            with self.subTest(vista=vista, argumentos=argumentos):
                self.comprobar_seccion(
                    reverse(vista, args=argumentos),
                    reverse(seccion, args=argumentos_seccion),
                )

    def test_empleado_conserva_menu_restringido_y_estado_activo(self):
        self.compra()
        venta = registrar_venta(
            usuario=self.empleado,
            fecha=date(2026, 11, 8),
            lineas=[self.linea('1', '8000')],
        )
        self.client.force_login(self.empleado)
        for vista, argumentos, seccion, argumentos_seccion in [
            ('inicio', [], 'inicio', []),
            ('gestion:catalogo', ['productos'], 'gestion:catalogo', ['productos']),
            ('gestion:ventas', [], 'gestion:ventas', []),
            ('gestion:venta_crear', [], 'gestion:ventas', []),
            ('gestion:venta_detalle', [venta.pk], 'gestion:ventas', []),
            ('gestion:stock', [], 'gestion:stock', []),
        ]:
            with self.subTest(vista=vista, argumentos=argumentos):
                self.comprobar_seccion(
                    reverse(vista, args=argumentos),
                    reverse(seccion, args=argumentos_seccion),
                )
        respuesta = self.client.get(reverse('inicio'))
        self.assertNotContains(respuesta, 'href="' + reverse('usuario_lista') + '"')
        self.assertNotContains(respuesta, 'href="' + reverse('gestion:compras') + '"')
        self.assertNotContains(respuesta, 'href="' + reverse('gestion:reportes') + '"')
