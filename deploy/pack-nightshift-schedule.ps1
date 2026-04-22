# pack night-shift schedule calendar patch
# 说明：本补丁仅新增"排班日历 + 监护次数统计"功能，无数据库迁移，无新增依赖
$ErrorActionPreference = "Stop"

function Find-ProjectRoot {
    $candidates = @(
        $PSScriptRoot,
        (Split-Path -Parent $MyInvocation.MyCommand.Definition),
        (Get-Location).Path
    ) | Where-Object { $_ }

    foreach ($c in $candidates) {
        $p = $c
        for ($i = 0; $i -lt 5; $i++) {
            if ($p -and (Test-Path (Join-Path $p "backend\apps\safety\models.py"))) {
                return (Resolve-Path $p).Path
            }
            $p = Split-Path -Parent $p
        }
    }
    throw "project root not found (need backend\apps\safety\models.py)"
}

$Root      = Find-ProjectRoot
$ScriptDir = Join-Path $Root "deploy"
$Out       = Join-Path $ScriptDir "patch-nightshift-schedule"
if (-not (Test-Path $ScriptDir)) { New-Item -ItemType Directory -Path $ScriptDir -Force | Out-Null }

Write-Host "Root      = $Root"
Write-Host "ScriptDir = $ScriptDir"
Write-Host "Out       = $Out"

if (Test-Path $Out) { Remove-Item $Out -Recurse -Force }
New-Item -ItemType Directory -Path $Out -Force | Out-Null

# ---------- backend files ----------
$backendBase = Join-Path $Out "backend\apps\safety"
New-Item -ItemType Directory -Path $backendBase -Force | Out-Null

# modified: new inspector_stats view + Count/Q import
Copy-Item (Join-Path $Root "backend\apps\safety\nightshift_views.py") $backendBase -Force

# modified: new URL route for /nightshift/inspector-stats/
Copy-Item (Join-Path $Root "backend\apps\safety\urls.py") $backendBase -Force

# ---------- frontend ----------
$frontSrc = Join-Path $Root "frontend"
Push-Location $frontSrc
Write-Host ">>> building frontend dist ..."
npm run build
if ($LASTEXITCODE -ne 0) { Pop-Location; throw "frontend build failed" }
Pop-Location

$frontDir = Join-Path $Out "frontend"
New-Item -ItemType Directory -Path $frontDir -Force | Out-Null
Copy-Item (Join-Path $frontSrc "dist") $frontDir -Recurse -Force

# ---------- zip ----------
$zip = Join-Path $ScriptDir "patch-nightshift-schedule.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path (Join-Path $Out "*") -DestinationPath $zip

Write-Host ""
Write-Host "========================================"
Write-Host "patch zip generated:"
Write-Host "  $zip"
Write-Host ""
Write-Host "Contains:"
Write-Host "  backend\apps\safety\nightshift_views.py (modified)"
Write-Host "  backend\apps\safety\urls.py             (modified)"
Write-Host "  frontend\dist\                          (rebuilt)"
Write-Host ""
Write-Host "NOTE: No migrations, no new dependencies."
Write-Host "========================================"
