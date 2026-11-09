# CorteGestión — Auditoría inicial

Se revisaron todos los archivos fuente, templates, CSS, configuración, dependencias,
comandos y migraciones existentes. `.venv` contiene dependencias y no es código del
proyecto. No existe repositorio Git ni archivos de datos locales. No se consultó ni
alteró la antigua base externa de XAMPP: su existencia y contenido no están verificados.

## Conservar
- `usuarios.Usuario(AbstractUser)`, emails únicos, roles `dueno`/`empleado`.
- `usuarios/migrations/0001_initial.py` íntegra; no hay necesidad de reiniciar historial.
- Autenticación Django, CSRF, logout por POST, CRUD de usuarios y CSS burdeos/crema.
- Configuración WSGI/ASGI y estructura de templates Django.

## Corregir
- Registro abierto que otorga el primer rol dueño: cerrar ruta y retirar formulario público.
- Contraseña de BD y SECRET_KEY incrustadas: retirar y exigir entorno; considerar
  comprometidos los valores antiguos y rotarlos también en cualquier instalación previa.
- `crear_demo` con clave fija: reemplazar por alta interactiva segura.
- Edición de contraseña sin validadores completos; protección del último dueño basada
  en una instancia ya modificada por ModelForm; eliminación sin protección histórica.
- Permisos solo para usuarios: extender controles de servidor a cada módulo.
- PyMySQL y cryptography innecesarios en Linux: usar mysqlclient compilado en imagen.
- No había compras, ventas, inventario, reportes ni pruebas implementadas.

## Límites
Docker Compose es para desarrollo local, no despliegue público. No se cambian datos
de XAMPP ni se eliminan migraciones. Una importación de la BD anterior requiere copia
de seguridad y un procedimiento específico. RNF2 necesita medición con usuarios reales.
