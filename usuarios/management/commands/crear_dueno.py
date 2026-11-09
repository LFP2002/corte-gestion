from getpass import getpass

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.db import connection, transaction

from usuarios.models import Usuario


class Command(BaseCommand):
    help = 'Crea el primer dueño de forma interactiva; no modifica cuentas existentes.'

    def handle(self, *args, **options):
        # GET_LOCK cubre incluso una BD vacía (no hay filas que bloquear).
        nombre_lock = f"{connection.settings_dict['NAME']}:primer_dueno"
        with connection.cursor() as cursor:
            cursor.execute('SELECT GET_LOCK(%s, 10)', [nombre_lock])
            if cursor.fetchone()[0] != 1:
                raise CommandError('Otro proceso está creando el primer dueño. Reintente luego.')
        try:
            self.crear()
        finally:
            with connection.cursor() as cursor:
                cursor.execute('SELECT RELEASE_LOCK(%s)', [nombre_lock])

    def crear(self):
        if Usuario.objects.filter(rol='dueno', is_active=True).exists():
            self.stdout.write('Ya existe un dueño activo. No se realizaron cambios.')
            return
        username = input('Usuario: ').strip()
        email = input('Correo: ').strip()
        password = getpass('Contraseña: ')
        if password != getpass('Repita la contraseña: '):
            raise CommandError('Las contraseñas no coinciden.')
        usuario = Usuario(username=username, email=email, rol='dueno')
        try:
            validate_email(email)
            usuario.full_clean(exclude=['password'])
            validate_password(password, usuario)
        except ValidationError as exc:
            raise CommandError('; '.join(exc.messages)) from exc
        with transaction.atomic():
            list(Usuario.objects.select_for_update().order_by('pk'))
            if Usuario.objects.filter(rol='dueno', is_active=True).exists():
                self.stdout.write('Ya existe un dueño activo. No se realizaron cambios.')
                return
            usuario.set_password(password)
            usuario.save()
        self.stdout.write(self.style.SUCCESS('Primer dueño creado.'))
