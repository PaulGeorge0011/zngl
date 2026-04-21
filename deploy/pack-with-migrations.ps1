# ZS2 offline packaging script with makemigrations
# Usage: .\deploy\pack-with-migrations.ps1

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$projectRoot = Split-Path -Parent $PSScriptRoot
$packScript = Join-Path $PSScriptRoot "pack.ps1"
$packageFile = Join-Path $PSScriptRoot "zs2-deploy.tar.gz"

Write-Host "=== ZS2 offline package build (with migrations) ===" -ForegroundColor Green

Push-Location (Join-Path $projectRoot "backend")
try {
    Write-Host "`n[0/2] Run makemigrations" -ForegroundColor Cyan
    python manage.py makemigrations
    if ($LASTEXITCODE -ne 0) {
        throw "makemigrations failed"
    }
} finally {
    Pop-Location
}

Write-Host "`n[1/2] Run offline packaging" -ForegroundColor Cyan
try {
    & $packScript
    if ($LASTEXITCODE -ne 0) {
        throw "pack.ps1 failed"
    }
} catch {
    if (Test-Path $packageFile) {
        $existingPackage = Get-Item $packageFile
        Write-Warning "Packaging failed. Existing package remains on disk and may be stale: $($existingPackage.FullName) ($($existingPackage.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss")), $([math]::Round($existingPackage.Length / 1MB, 2)) MB)"
    }
    throw
}
