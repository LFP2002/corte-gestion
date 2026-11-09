$ErrorActionPreference = 'Stop'
$raiz = Split-Path $PSScriptRoot -Parent
$destino = Join-Path $raiz '.env'
if (Test-Path $destino) {
    Write-Host '.env ya existe. No se modificaron sus valores.'
    exit 0
}
$rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
function New-Secret {
    $bytes = New-Object byte[] 48
    $rng.GetBytes($bytes)
    return [Convert]::ToBase64String($bytes)
}
@(
    "SECRET_KEY=$(New-Secret)"
    'DEBUG=True'
    'ALLOWED_HOSTS=localhost,127.0.0.1'
    'DB_NAME=carniceria'
    'DB_USER=carniceria_app'
    "DB_PASSWORD=$(New-Secret)"
    "DB_ROOT_PASSWORD=$(New-Secret)"
) | Set-Content -Encoding ascii $destino
$rng.Dispose()
Write-Host '.env creado con secretos aleatorios. No compartir ni subir este archivo.'
