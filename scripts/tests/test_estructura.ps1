# No requiere Docker ni acceso a secretos o datos.
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
foreach ($path in @(
    'backend/manage.py', 'backend/requirements.txt', 'backend/Dockerfile',
    'backend/config/settings.py', 'backend/apps/__init__.py',
    'backend/apps/gestion/apps.py', 'backend/apps/usuarios/apps.py',
    'backend/scripts/docker_start.py', 'backend/templates/base.html',
    'backend/templates/403.html', 'backend/templates/registration/login.html',
    'backend/templates/gestion/operacion_form.html', 'backend/templates/usuarios/inicio.html',
    'backend/static/css/style.css', 'backend/static/js/operacion.js',
    'backend/docs/PLAN_REESTRUCTURACION_FYAG.md', 'compose.yaml'
)) {
    if (-not (Test-Path (Join-Path $repo $path) -PathType Leaf)) {
        throw "Archivo requerido ausente: $path"
    }
}
foreach ($path in @(
    'config', 'gestion', 'usuarios', 'templates', 'static', 'docs',
    'manage.py', 'Dockerfile', 'requirements.txt', 'docker_start.py',
    'backend/apps/gestion/templates', 'backend/apps/usuarios/templates',
    'backend/apps/gestion/static', 'backend/apps/usuarios/static'
)) {
    if (Test-Path (Join-Path $repo $path)) { throw "Ruta obsoleta: $path" }
}
$compose = Get-Content (Join-Path $repo 'compose.yaml') -Raw
if ($compose -notmatch 'dockerfile: backend/Dockerfile') { throw 'Dockerfile no configurado' }
if ($compose -notmatch 'external: true\s+name: carniceria_django_mariadb_data') {
    throw 'Identidad del volumen externo alterada'
}
$dockerfile = Get-Content (Join-Path $repo 'backend/Dockerfile') -Raw
if ($dockerfile -notmatch 'COPY --chown=app:app backend/ \.') { throw 'COPY backend incorrecto' }
if ($dockerfile -notmatch 'scripts/docker_start.py') { throw 'Arranque incorrecto' }
Write-Host 'APROBADO: estructura backend, recursos unicos, Docker y volumen conservado.'
