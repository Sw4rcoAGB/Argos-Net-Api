#Requires -Version 5.1
param(
    [switch]$SkipValidation
)

$ErrorActionPreference = "Stop"
$projectRoot  = $PSScriptRoot
$contractsDir = Join-Path $projectRoot "contracts"
$envFile      = Join-Path $projectRoot ".env"

Write-Host ""
Write-Host "============================================" -ForegroundColor Magenta
Write-Host "   AgroNest -- Deploy en Sepolia Testnet   " -ForegroundColor Magenta
Write-Host "============================================" -ForegroundColor Magenta
Write-Host ""

# --- Leer .env --------------------------------------------------------------
if (-not (Test-Path $envFile)) {
    Write-Host "[ERROR] .env no encontrado en $envFile" -ForegroundColor Red
    exit 1
}

$envVars = @{}
Get-Content $envFile | ForEach-Object {
    if ($_ -match "^\s*([^#\s][^=]*)=(.*)$") {
        $envVars[$matches[1].Trim()] = $matches[2].Trim()
    }
}

$rpcUrl     = $envVars["RPC_URL"]
$privateKey = $envVars["API_PRIVATE_KEY"]

# --- Validaciones ------------------------------------------------------------
Write-Host "[INFO] Validando configuracion..." -ForegroundColor Cyan

if ([string]::IsNullOrWhiteSpace($rpcUrl)) {
    Write-Host "[ERROR] RPC_URL no esta configurado en .env" -ForegroundColor Red
    Write-Host "  Agrega: RPC_URL=https://eth-sepolia.g.alchemy.com/v2/TU_API_KEY" -ForegroundColor Yellow
    exit 1
}

if ($rpcUrl -match "localhost|127\.0\.0\.1") {
    Write-Host "[ERROR] RPC_URL apunta a localhost. Para Sepolia necesitas Alchemy o Infura." -ForegroundColor Red
    Write-Host "  URL actual: $rpcUrl" -ForegroundColor DarkGray
    Write-Host "  Cambia a  : RPC_URL=https://eth-sepolia.g.alchemy.com/v2/TU_API_KEY" -ForegroundColor Yellow
    exit 1
}

if ([string]::IsNullOrWhiteSpace($privateKey)) {
    Write-Host "[ERROR] API_PRIVATE_KEY no esta configurada en .env" -ForegroundColor Red
    exit 1
}

$hardhatKey = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
if ($privateKey -eq $hardhatKey) {
    Write-Host "[ERROR] API_PRIVATE_KEY sigue siendo la clave de Hardhat (no tiene ETH en Sepolia)." -ForegroundColor Red
    Write-Host "  Exporta tu clave privada desde MetaMask y actualiza el .env" -ForegroundColor Yellow
    exit 1
}

Write-Host "[OK] RPC URL: $($rpcUrl.Substring(0, [Math]::Min(60, $rpcUrl.Length)))..." -ForegroundColor Green
Write-Host "[OK] Private key configurada" -ForegroundColor Green

# --- Exportar variables para hardhat.config.js ------------------------------
$env:RPC_URL         = $rpcUrl
$env:API_PRIVATE_KEY = $privateKey
$env:CHAIN_ID        = "11155111"

# --- Deploy ------------------------------------------------------------------
Write-Host ""
Write-Host "[INFO] Iniciando deploy en Sepolia (puede tardar 1-2 minutos)..." -ForegroundColor Cyan
Write-Host ""

Push-Location $contractsDir
try {
    npx hardhat run scripts/deploy.js --network sepolia
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] El deploy fallo. Revisa el error de arriba." -ForegroundColor Red
        exit 1
    }
} finally {
    Pop-Location
}

# --- Leer JSON con addresses -------------------------------------------------
$addressesFile = Join-Path $contractsDir "deployed_addresses.sepolia.json"
if (-not (Test-Path $addressesFile)) {
    Write-Host "[ERROR] No se encontro deployed_addresses.sepolia.json" -ForegroundColor Red
    exit 1
}

$deployed = Get-Content $addressesFile -Raw | ConvertFrom-Json

Write-Host ""
Write-Host "[OK] Contratos desplegados:" -ForegroundColor Green
Write-Host "  MockUSDC     : $($deployed.USDC_CONTRACT_ADDRESS)"   -ForegroundColor Cyan
Write-Host "  MockOracle   : $($deployed.ORACLE_CONTRACT_ADDRESS)" -ForegroundColor Cyan
Write-Host "  AgroNestCrop : $($deployed.CROP_CONTRACT_ADDRESS)"   -ForegroundColor Cyan

# --- Actualizar .env ---------------------------------------------------------
Write-Host ""
Write-Host "[INFO] Actualizando .env con las nuevas addresses..." -ForegroundColor Cyan

$envContent = Get-Content $envFile -Raw

function Update-EnvVar($content, $key, $value) {
    if ($content -match "(?m)^$key=") {
        return ($content -replace "(?m)^$key=.*", "$key=$value")
    } else {
        return ($content.TrimEnd() + "`r`n$key=$value`r`n")
    }
}

$envContent = Update-EnvVar $envContent "CHAIN_ID"                "11155111"
$envContent = Update-EnvVar $envContent "USDC_CONTRACT_ADDRESS"   $deployed.USDC_CONTRACT_ADDRESS
$envContent = Update-EnvVar $envContent "ORACLE_CONTRACT_ADDRESS" $deployed.ORACLE_CONTRACT_ADDRESS
$envContent = Update-EnvVar $envContent "CROP_CONTRACT_ADDRESS"   $deployed.CROP_CONTRACT_ADDRESS

[System.IO.File]::WriteAllText($envFile, $envContent, [System.Text.Encoding]::UTF8)

Write-Host "[OK] .env actualizado" -ForegroundColor Green

# --- Links Etherscan ---------------------------------------------------------
Write-Host ""
Write-Host "Verifica en Etherscan Sepolia:" -ForegroundColor White
Write-Host "  https://sepolia.etherscan.io/address/$($deployed.USDC_CONTRACT_ADDRESS)"   -ForegroundColor DarkCyan
Write-Host "  https://sepolia.etherscan.io/address/$($deployed.ORACLE_CONTRACT_ADDRESS)" -ForegroundColor DarkCyan
Write-Host "  https://sepolia.etherscan.io/address/$($deployed.CROP_CONTRACT_ADDRESS)"   -ForegroundColor DarkCyan

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  Deploy completado. Levanta la API con:" -ForegroundColor Green
Write-Host "    uvicorn main:app --reload" -ForegroundColor Green
Write-Host "  Las addresses estan en .env de forma permanente." -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
