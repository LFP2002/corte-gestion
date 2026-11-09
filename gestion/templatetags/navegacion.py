"""Identifica la sección activa usando las rutas nombradas de Django.

No depende de los textos o prefijos de URL y permanece activo en formularios,
edición y vistas de detalle.
"""
from django import template


register = template.Library()


@register.simple_tag(takes_context=True)
def seccion_actual(context):
    request = context.get('request')
    resolver = getattr(request, 'resolver_match', None)
    if resolver is None:
        return ''

    vista = resolver.view_name
    if vista == 'inicio':
        return 'inicio'
    if vista in {
        'gestion:catalogo',
        'gestion:catalogo_crear',
        'gestion:catalogo_editar',
        'gestion:catalogo_eliminar',
    }:
        tipo = resolver.kwargs.get('tipo')
        return tipo if tipo in ('productos', 'proveedores') else ''
    if vista in {'gestion:ventas', 'gestion:venta_crear', 'gestion:venta_detalle'}:
        return 'ventas'
    if vista == 'gestion:stock':
        return 'stock'
    if vista in {'gestion:compras', 'gestion:compra_crear', 'gestion:compra_detalle'}:
        return 'compras'
    if vista == 'gestion:reportes':
        return 'reportes'
    if vista in {'usuario_lista', 'usuario_crear', 'usuario_editar', 'usuario_eliminar'}:
        return 'usuarios'
    return ''
