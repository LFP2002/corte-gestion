"""Arranque de desarrollo: conexión real, migraciones y servidor sin shell."""
import os
import subprocess
import sys
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.db import connection, OperationalError

for intento in range(60):
    try:
        connection.ensure_connection()
        break
    except OperationalError:
        connection.close()
        time.sleep(2)
else:
    sys.exit('MariaDB no disponible después de 120 segundos.')
subprocess.run([sys.executable, 'manage.py', 'migrate', '--noinput'], check=True)
os.execv(sys.executable, [sys.executable, 'manage.py', 'runserver', '0.0.0.0:8000', '--noreload'])
