# Pruebas de seguridad del instalador. Simula Docker: NO crea volumenes reales.
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$global:SimulatedVolumeExists = $false
$global:InputAnswer = ''
$global:DockerCalls = [System.Collections.Generic.List[string]]::new()

function global:docker {
    $commandText = ($args | ForEach-Object { [string]$_ }) -join ' '
    $global:DockerCalls.Add($commandText)
    $global:LASTEXITCODE = 0
    if ($commandText -like 'info *') { return '25.0.0' }
    if ($commandText -like 'volume inspect *') {
        if ($global:SimulatedVolumeExists) { return 'existing-volume' }
        $global:LASTEXITCODE = 1
        return
    }
    if ($commandText -like 'volume create *') { return 'carniceria_django_mariadb_data' }
}

function global:Read-Host {
    param([string]$Prompt)
    return $global:InputAnswer
}

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw "FALLO: $Message" }
}

function New-TestRoot {
    $root = Join-Path ([System.IO.Path]::GetTempPath()) ("cortegestion-installer-" + [guid]::NewGuid().ToString('N'))
    $scripts = Join-Path $root 'scripts'
    New-Item -ItemType Directory -Path $scripts -Force | Out-Null
    Copy-Item (Join-Path $repo 'scripts/instalacion_nueva.ps1') $scripts
    Copy-Item (Join-Path $repo 'scripts/preparar_entorno.ps1') $scripts
    return $root
}

function Invoke-Case {
    param([string]$Name, [bool]$VolumeExists, [string]$Answer, [bool]$ShouldFail)
    $root = New-TestRoot
    $global:SimulatedVolumeExists = $VolumeExists
    $global:InputAnswer = $Answer
    $global:DockerCalls.Clear()
    $failed = $false
    try {
        & (Join-Path $root 'scripts/instalacion_nueva.ps1')
    }
    catch {
        $failed = $true
        if (-not $ShouldFail) { throw }
    }
    finally {
        try {
            Assert-True ($failed -eq $ShouldFail) "Resultado inesperado: $Name"
            $calls = $global:DockerCalls -join ' | '
            Assert-True (-not ($calls -match 'volume (rm|prune)|compose down')) "Accion destructiva: $Name"
            if ($VolumeExists) {
                Assert-True ($calls -notmatch 'volume create|compose up') "No debe reinstalarse con volumen existente"
                Assert-True (-not (Test-Path (Join-Path $root '.env'))) "No debe generar .env con volumen existente"
            }
            elseif ($Answer -cne 'NUEVA') {
                Assert-True ($calls -notmatch 'volume create|compose up') "No debe iniciar instalacion rechazada"
                Assert-True (-not (Test-Path (Join-Path $root '.env'))) "Cancelacion no debe generar .env"
            }
            else {
                Assert-True ($calls -match 'volume create carniceria_django_mariadb_data') "No creo el volumen esperado"
                Assert-True ($calls -match 'compose up -d --build --wait') "No intento levantar Compose"
                $envPath = Join-Path $root '.env'
                Assert-True (Test-Path $envPath) "No genero .env"
                $envText = Get-Content $envPath -Raw
                Assert-True ($envText -match '(?m)^SECRET_KEY=.{20,}$') "SECRET_KEY no generado"
                Assert-True ($envText -match '(?m)^DB_PASSWORD=.{20,}$') "DB_PASSWORD no generado"
            }
        }
        finally {
            Remove-Item -Recurse -Force $root -ErrorAction SilentlyContinue
        }
    }
    Write-Host "APROBADO: $Name"
}

try {
    Invoke-Case -Name 'Volumen preexistente queda intacto' -VolumeExists $true -Answer 'NUEVA' -ShouldFail $false
    Invoke-Case -Name 'Cancelacion no altera entorno' -VolumeExists $false -Answer 'NO' -ShouldFail $true
    Invoke-Case -Name 'Instalacion limpia prepara entorno' -VolumeExists $false -Answer 'NUEVA' -ShouldFail $false
    Write-Host '3 escenarios del instalador completados.'
}
finally {
    Remove-Item Function:\docker -ErrorAction SilentlyContinue
    Remove-Item Function:\Read-Host -ErrorAction SilentlyContinue
}
