from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.usuarios.models import Usuario


class Command(BaseCommand):
    help = 'Recuperación local de emergencia: elimina solo el bloqueo temporal de una cuenta.'

    def add_arguments(self, parser):
        parser.add_argument('username')

    def handle(self, *args, **options):
        with transaction.atomic():
            try:
                usuario = Usuario.objects.select_for_update().get(username=options['username'])
            except Usuario.DoesNotExist as exc:
                raise CommandError('Cuenta no encontrada.') from exc
            usuario.intentos_fallidos = 0
            usuario.bloqueo_hasta = None
            usuario.save(update_fields=['intentos_fallidos', 'bloqueo_hasta'])
        self.stdout.write(self.style.SUCCESS('Bloqueo temporal restablecido; rol y estado administrativo conservados.'))
