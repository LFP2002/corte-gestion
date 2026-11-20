from django.core.management.base import BaseCommand

from django.core.management import call_command


class Command(BaseCommand):
    help = 'Alias seguro de crear_dueno; ya no genera cuentas con claves predeterminadas.'

    def handle(self, *args, **opts):
        call_command('crear_dueno')
