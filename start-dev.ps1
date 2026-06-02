#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Levanta el entorno de desarrollo completo de AgroNest con un solo comando.

.DESCRIPTION
    1. Inicia el nodo Hardhat local (localhost:8545) en una nueva ventana
    2. Espera a que el nodo esté listo
    3. Despliega los contratos y genera contracts/deployed_addresses.json
    4. Levanta la API FastAPI (uvicorn)

    La API lee las addresses automáticamente desde deployed_addresses.json,
    por lo que NO necesitas actualizar .env manualmente.

.EXAMPLE
    .\start-dev.ps1
    .\start-dev.ps1 -SkipDeploy   # Si el nodo ya está corriendo y no quieres redesplegar
#>

param(
    [switch]$SkipDeploy
)

$ErrorActionPreference = "Stop"
$contractsDir = Join-Path $PSScriptRoot "contracts"
$apiDir       = $PSScriptRoot

# ─── Colores ────────────────────────────────────────────────────────────────
function Info  ($msg) { Write-Host "  $msg" -ForegroundColor Cyan   }
function OK    ($msg) { Write-Host "  ✔ $msg" -ForegroundColor Green  }
function Warn  ($msg) { Write-Host "  ⚠ $msg" -ForegroundColor Yellow }
function Err   ($msg) { Write-Host "  ✖ $msg" -ForegroundColor Red    }

Write-Host ""
Write-Host "╔══════════════════════════════════════╗" -ForegroundColor Magenta
Write-Host "║     AgroNest — Dev Environment       ║" -ForegroundColor Magenta
Write-Host "╚══════════════════════════════════════╝" -ForegroundColor Magenta
Write-Host ""

# ─── 1. Verificar dependencias ───────────────────────────────────────────────
Info "Verificando dependencias..."

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Err "Node.js no encontrado. Instálalo desde https://nodejs.org"
    exit 1
}
if (-not (Get-Command npx -ErrorAction SilentlyContinue)) {
    Err "npx no encontrado. Reinstala Node.js"
    exit 1
}
if (-not (Test-Path (Join-Path $contractsDir "node_modules"))) {
    Warn "node_modules no encontrado en contracts/. Instalando dependencias..."
    Push-Location $contractsDir
    npm install
    Pop-Location
}
OK "Dependencias OK"

# ─── 2. Iniciar nodo Hardhat ─────────────────────────────────────────────────
$port = 8545
$nodeRunning = $false

# Comprobar si ya hay algo escuchando en 8545
try {
    $conn = New-Object System.Net.Sockets.TcpClient
    $conn.Connect("localhost", $port)
    $conn.Close()
    $nodeRunning = $true
} catch {}

if ($nodeRunning) {
    OK "Nodo Hardhat ya está corriendo en localhost:$port"
} else {
    Info "Iniciando nodo Hardhat en localhost:$port..."

    # Abrir en nueva ventana de PowerShell para que quede visible
    Start-Process powershell -ArgumentList @(
        "-NoExit",
        "-Command",
        "cd '$contractsDir'; Write-Host 'Hardhat Node — AgroNest' -ForegroundColor Cyan; npx hardhat node"
    )

    # Esperar a que el puerto esté disponible (máx 30s)
    $timeout = 30
    $elapsed = 0
    $ready   = $false
    Info "Esperando que el nodo esté listo"
    while (-not $ready -and $elapsed -lt $timeout) {
        Start-Sleep -Seconds 1
        $elapsed++
        Write-Host "." -NoNewline -ForegroundColor DarkGray
        try {
            $conn = New-Object System.Net.Sockets.TcpClient
            $conn.Connect("localhost", $port)
            $conn.Close()
            $ready = $true
        } catch {}
    }
    Write-Host ""

    if (-not $ready) {
        Err "El nodo Hardhat no respondió en $timeout segundos."
        Err "Revisa la ventana de Hardhat para ver el error."
        exit 1
    }
    OK "Nodo Hardhat listo (arrancó en ${elapsed}s)"
}

# ─── 3. Desplegar contratos ───────────────────────────────────────────────────
if ($SkipDeploy) {
    Warn "Saltando despliegue (-SkipDeploy). Usando deployed_addresses.json existente."
} else {
    Info "Desplegando contratos en red local..."
    Push-Location $contractsDir
    try {
        npx hardhat run scripts/deploy.js --network localhost
        if ($LASTEXITCODE -ne 0) {
            Err "Error en el despliegue. Revisa la salida de Hardhat."
            Pop-Location
            exit 1
        }
        OK "Contratos desplegados. Addresses guardadas en contracts/deployed_addresses.json"
    } finally {
        Pop-Location
    }
}

# Mostrar las addresses desplegadas
$addressesFile = Join-Path $contractsDir "deployed_addresses.json"
if (Test-Path $addressesFile) {
    $addresses = Get-Content $addressesFile | ConvertFrom-Json
    Write-Host ""
    Write-Host "  Addresses activas:" -ForegroundColor White
    Write-Host "    USDC   : $($addresses.USDC_CONTRACT_ADDRESS)"   -ForegroundColor DarkCyan
    Write-Host "    Oracle : $($addresses.ORACLE_CONTRACT_ADDRESS)" -ForegroundColor DarkCyan
    Write-Host "    Crop   : $($addresses.CROP_CONTRACT_ADDRESS)"   -ForegroundColor DarkCyan
    Write-Host ""
}

# ─── 4. Iniciar API ───────────────────────────────────────────────────────────
Info "Iniciando API FastAPI (uvicorn)..."
Write-Host ""
Write-Host "  API disponible en: http://localhost:8000" -ForegroundColor Green
Write-Host "  Swagger UI       : http://localhost:8000/docs" -ForegroundColor Green
Write-Host ""
Write-Host "  Presiona Ctrl+C para detener la API" -ForegroundColor DarkGray
Write-Host ""

Push-Location $apiDir
try {
    uvicorn main:app --reload --host 0.0.0.0 --port 8001
} finally {
    Pop-Location
}
