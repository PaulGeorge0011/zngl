# pack dustroom missing files patch
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
$Out       = Join-Path $ScriptDir "fix-dustroom-missing"
if (-not (Test-Path $ScriptDir)) { New-Item -ItemType Directory -Path $ScriptDir -Force | Out-Null }

Write-Host "Root      = $Root"
Write-Host "ScriptDir = $ScriptDir"
Write-Host "Out       = $Out"

if (Test-Path $Out) { Remove-Item $Out -Recurse -Force }
New-Item -ItemType Directory -Path $Out -Force | Out-Null

# ---------- backend ----------
$backendBase   = Join-Path $Out "backend\apps\safety"
$migrationsDir = Join-Path $backendBase "migrations"
$scriptsDir    = Join-Path $Out "backend\scripts"

New-Item -ItemType Directory -Path $backendBase   -Force | Out-Null
New-Item -ItemType Directory -Path $migrationsDir -Force | Out-Null
New-Item -ItemType Directory -Path $scriptsDir    -Force | Out-Null

Copy-Item (Join-Path $Root "backend\apps\safety\dustroom_views.py")       $backendBase -Force
Copy-Item (Join-Path $Root "backend\apps\safety\dustroom_serializers.py") $backendBase -Force
Copy-Item (Join-Path $Root "backend\apps\safety\migrations\0004_dustroom_inspectionitem_inspectiontemplate_and_more.py") $migrationsDir -Force

Copy-Item (Join-Path $Root "backend\apps\safety\models.py")      $backendBase -Force
Copy-Item (Join-Path $Root "backend\apps\safety\admin.py")       $backendBase -Force
Copy-Item (Join-Path $Root "backend\apps\safety\urls.py")        $backendBase -Force
Copy-Item (Join-Path $Root "backend\apps\safety\permissions.py") $backendBase -Force

Copy-Item (Join-Path $Root "backend\apps\safety\nightshift_views.py")       $backendBase -Force -ErrorAction SilentlyContinue
Copy-Item (Join-Path $Root "backend\apps\safety\nightshift_serializers.py") $backendBase -Force -ErrorAction SilentlyContinue
Copy-Item (Join-Path $Root "backend\apps\safety\migrations\0005_nightshiftcategory_nightshiftcheckitem_and_more.py") $migrationsDir -Force -ErrorAction SilentlyContinue
Copy-Item (Join-Path $Root "backend\apps\safety\migrations\0006_nightshiftduty_nightshiftrecord_duty.py")            $migrationsDir -Force -ErrorAction SilentlyContinue

Copy-Item (Join-Path $Root "backend\scripts\init_dustroom_data.py")  $scriptsDir -Force
Copy-Item (Join-Path $Root "backend\scripts\init_nightshift_data.py") $scriptsDir -Force -ErrorAction SilentlyContinue

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
$zip = Join-Path $ScriptDir "fix-dustroom-missing.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path (Join-Path $Out "*") -DestinationPath $zip

Write-Host ""
Write-Host "========================================"
Write-Host "patch zip generated:"
Write-Host "  $zip"
Write-Host "========================================"
