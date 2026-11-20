from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.contrib.staticfiles import finders
from django.db.migrations.loader import MigrationLoader
from django.template.loader import get_template
from django.test import SimpleTestCase
from django.urls import resolve


class EstructuraTests(SimpleTestCase):
    def test_identidad_apps_y_tablas(self):
        for label in ('usuarios', 'gestion'):
            config = apps.get_app_config(label)
            self.assertEqual(config.name, f'apps.{label}')
            self.assertEqual(config.label, label)
            for model in config.get_models():
                self.assertEqual(model._meta.db_table, f'{label}_{model._meta.model_name}')
        self.assertEqual(settings.AUTH_USER_MODEL, 'usuarios.Usuario')

    def test_templates_centralizados(self):
        root = settings.BASE_DIR / 'templates'
        for path in root.rglob('*.html'):
            name = path.relative_to(root).as_posix()
            with self.subTest(template=name):
                self.assertEqual(Path(get_template(name).origin.name), path)
        for label in ('usuarios', 'gestion'):
            self.assertFalse((Path(apps.get_app_config(label).path) / 'templates').exists())

    def test_estaticos_unicos(self):
        for name in ('css/style.css', 'js/operacion.js'):
            self.assertEqual(
                [Path(path) for path in finders.find(name, find_all=True)],
                [settings.BASE_DIR / 'static' / name],
            )
        for label in ('usuarios', 'gestion'):
            self.assertFalse((Path(apps.get_app_config(label).path) / 'static').exists())

    def test_historial_migraciones_descubierto(self):
        loader = MigrationLoader(None)
        migrations = {key for key in loader.disk_migrations if key[0] in ('usuarios', 'gestion')}
        self.assertEqual(migrations, {
            ('usuarios', '0001_initial'),
            ('usuarios', '0002_bloqueo_acceso'),
            ('gestion', '0001_initial'),
            ('gestion', '0002_detalleventa_venta_and_more'),
            ('gestion', '0003_rol_vendedor_al_registrar'),
        })

    def test_urls_apuntan_a_paquetes_nuevos(self):
        self.assertEqual(resolve('/').func.__module__, 'apps.usuarios.views')
        self.assertEqual(resolve('/productos/').func.__module__, 'apps.gestion.views')
