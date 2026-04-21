# pack night-shift SMS notify feature patch
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
$Out       = Join-Path $ScriptDir "patch-sms-notify"
if (-not (Test-Path $ScriptDir)) { New-Item -ItemType Directory -Path $ScriptDir -Force | Out-Null }

Write-Host "Root      = $Root"
Write-Host "ScriptDir = $ScriptDir"
Write-Host "Out       = $Out"

if (Test-Path $Out) { Remove-Item $Out -Recurse -Force }
New-Item -ItemType Directory -Path $Out -Force | Out-Null

# ---------- backend files ----------
$backendBase   = Join-Path $Out "backend\apps\safety"
$migrationsDir = Join-Path $backendBase "migrations"
$settingsDir   = Join-Path $Out "backend\config\settings"

New-Item -ItemType Directory -Path $backendBase   -Force | Out-Null
New-Item -ItemType Directory -Path $migrationsDir -Force | Out-Null
New-Item -ItemType Directory -Path $settingsDir   -Force | Out-Null

# new: sms module
Copy-Item (Join-Path $Root "backend\apps\safety\sms.py") $backendBase -Force

# modified: model (new field sms_sent_at)
Copy-Item (Join-Path $Root "backend\apps\safety\models.py") $backendBase -Force

# modified: serializer + views
Copy-Item (Join-Path $Root "backend\apps\safety\nightshift_serializers.py") $backendBase -Force
Copy-Item (Join-Path $Root "backend\apps\safety\nightshift_views.py")       $backendBase -Force

# new migration
Copy-Item (Join-Path $Root "backend\apps\safety\migrations\0007_nightshiftduty_sms_sent_at.py") $migrationsDir -Force

# modified: settings base (new SMS_* config)
Copy-Item (Join-Path $Root "backend\config\settings\base.py") $settingsDir -Force

# env.example (reference only, do NOT overwrite server .env)
$envDir = Join-Path $Out "backend"
New-Item -ItemType Directory -Path $envDir -Force | Out-Null
Copy-Item (Join-Path $Root "backend\.env.example") $envDir -Force

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
$zip = Join-Path $ScriptDir "patch-sms-notify.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path (Join-Path $Out "*") -DestinationPath $zip

Write-Host ""
Write-Host "========================================"
Write-Host "patch zip generated:"
Write-Host "  $zip"
Write-Host "========================================"
