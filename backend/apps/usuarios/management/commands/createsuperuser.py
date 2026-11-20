"""Conserva el comando Django, sin su opción de omitir la política de contraseñas."""
import os
from getpass import getpass

from django.contrib.auth.management.commands.createsuperuser import Command as DjangoCommand
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import CommandError
from django.views.decorators.debug import sensitive_variables


class Command(DjangoCommand):
    help = 'Crea un superusuario dueño validando siempre las nuevas credenciales.'

    @sensitive_variables('password', 'confirmacion')
    def handle(self, *args, **options):
        # Se heredan los argumentos estándar (--username, --email, --database,
        # --noinput). El manager Django conserva la creación y el hashing originales.
        database = options['database']
        datos = {}
        campos = [self.UserModel.USERNAME_FIELD, *self.UserModel.REQUIRED_FIELDS]
        for nombre in campos:
            valor = options.get(nombre)
            if valor is None:
                valor = os.environ.get(f'DJANGO_SUPERUSER_{nombre.upper()}')
            campo = self.UserModel._meta.get_field(nombre)
            if options['interactive'] and not valor:
                valor = self.get_input_data(campo, f'{campo.verbose_name}: ')
            if not valor:
                raise CommandError(f'Debe indicar {nombre}.')
            try:
                datos[nombre] = campo.clean(valor, None)
            except ValidationError as exc:
                raise CommandError('; '.join(exc.messages)) from exc

        # Un superusuario administrativo debe cumplir además el rol del proyecto.
        usuario = self.UserModel(**datos, rol='dueno', is_staff=True, is_superuser=True)
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')
        if options['interactive']:
            password = getpass('Contraseña: ')
            confirmacion = getpass('Repita la contraseña: ')
            if not password or password != confirmacion:
                raise CommandError('Las contraseñas deben ser no vacías y coincidir.')
        try:
            usuario.full_clean(exclude=['password'])
            if password is not None:
                validate_password(password, usuario)
        except ValidationError as exc:
            raise CommandError('; '.join(exc.messages)) from exc
        self.UserModel._default_manager.db_manager(database).create_superuser(
            **datos, password=password, rol='dueno',
        )
        if options['verbosity']:
            self.stdout.write(self.style.SUCCESS('Superusuario dueño creado; política de contraseña verificada.'))
