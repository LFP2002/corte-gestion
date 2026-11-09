# Solo para instalar CorteGestion por primera vez en un equipo SIN datos previos.
# No sustituye el procedimiento de restauracion de un volumen/backup existente.
$ErrorActionPreference = 'Stop'
$raiz = Split-Path $PSScriptRoot -Parent
$volumen = 'carniceria_django_mariadb_data'
Push-Location $raiz
try {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw 'Docker no esta instalado o no esta disponible en PATH.'
    }
    docker info --format '{{.ServerVersion}}' 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw 'Inicie Docker Desktop (motor Linux) antes de continuar.'
    }
    docker volume inspect $volumen 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        throw "El volumen $volumen ya existe. No se modificara. Para una instalacion existente utilice 'docker compose up -d --build --wait'."
    }

    Write-Host 'Solo continuar si es un equipo SIN base de datos previa que recuperar.'
    $respuesta = Read-Host 'Escriba NUEVA para crear una base de datos vacia'
    if ($respuesta -cne 'NUEVA') {
        throw 'Instalacion cancelada: no se creo ningun volumen.'
    }

    & (Join-Path $PSScriptRoot 'preparar_entorno.ps1')
    if (-not (Test-Path '.env')) {
        throw 'No se pudo preparar .env.'
    }
    docker compose config --quiet
    if ($LASTEXITCODE -ne 0) {
        throw 'Configuracion de Docker Compose invalida. No se creo el volumen.'
    }
    docker volume create $volumen | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw 'No se pudo crear el volumen para MariaDB.'
    }
    docker compose up -d --build --wait
    if ($LASTEXITCODE -ne 0) {
        throw "El arranque fallo. No se elimino el volumen $volumen; revise los logs."
    }
    Write-Host 'Instalacion nueva iniciada. Aplicacion: http://localhost:8000'
    Write-Host 'phpMyAdmin: http://localhost:8081'
    Write-Host 'Cree el primer dueno con: docker compose exec web python manage.py crear_dueno'
}
finally {
    Pop-Location
}
