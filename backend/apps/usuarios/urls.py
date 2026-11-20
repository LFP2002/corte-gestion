from django.contrib.auth import views as auth
from django.urls import path

from . import views

urlpatterns = [
    path('', views.Inicio.as_view(), name='inicio'),
    path('login/', auth.LoginView.as_view(redirect_authenticated_user=True), name='login'),
    path('logout/', auth.LogoutView.as_view(), name='logout'),
    path('usuarios/', views.UsuarioLista.as_view(), name='usuario_lista'),
    path('usuarios/nuevo/', views.UsuarioCrear.as_view(), name='usuario_crear'),
    path('usuarios/<int:pk>/editar/', views.UsuarioEditar.as_view(), name='usuario_editar'),
    path('usuarios/<int:pk>/eliminar/', views.UsuarioEliminar.as_view(), name='usuario_eliminar'),
]
