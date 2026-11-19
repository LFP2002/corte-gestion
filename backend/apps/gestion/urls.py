from django.urls import path, register_converter

from . import views


class CatalogoConverter:
    regex = 'productos|proveedores'

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value


register_converter(CatalogoConverter, 'catalogo')
app_name = 'gestion'
urlpatterns = [
    path('<catalogo:tipo>/', views.catalogo, name='catalogo'),
    path('<catalogo:tipo>/nuevo/', views.catalogo_form, name='catalogo_crear'),
    path('<catalogo:tipo>/<int:pk>/editar/', views.catalogo_form, name='catalogo_editar'),
    path('<catalogo:tipo>/<int:pk>/eliminar/', views.catalogo_eliminar, name='catalogo_eliminar'),
    path('compras/', views.compras, name='compras'),
    path('compras/nueva/', views.compra_crear, name='compra_crear'),
    path('compras/<int:pk>/', views.compra_detalle, name='compra_detalle'),
    path('stock/', views.stock, name='stock'),
    path('ventas/', views.ventas, name='ventas'),
    path('ventas/nueva/', views.venta_crear, name='venta_crear'),
    path('ventas/<int:pk>/', views.venta_detalle, name='venta_detalle'),
    path('reportes/', views.reportes, name='reportes'),
]
