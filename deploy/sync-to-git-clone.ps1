# Copy modified / new files from current working copy to a fresh git clone.
# Usage:
#   .\deploy\sync-to-git-clone.ps1 -Target d:\zngl-git
param(
    [Parameter(Mandatory=$true)]
    [string]$Target
)

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
    throw "project root not found"
}

$Src = Find-ProjectRoot
$Dst = (Resolve-Path $Target).Path

if (-not (Test-Path (Join-Path $Dst ".git"))) {
    throw "Target is not a git repo: $Dst"
}

Write-Host "Source: $Src"
Write-Host "Target: $Dst"

# Explicit file list - modify here if you add new files later
$files = @(
    # ---- backend: safety module ----
    "backend\apps\safety\models.py",
    "backend\apps\safety\admin.py",
    "backend\apps\safety\urls.py",
    "backend\apps\safety\permissions.py",
    "backend\apps\safety\dustroom_views.py",
    "backend\apps\safety\dustroom_serializers.py",
    "backend\apps\safety\nightshift_views.py",
    "backend\apps\safety\nightshift_serializers.py",
    "backend\apps\safety\sms.py",

    # ---- backend: migrations ----
    "backend\apps\safety\migrations\0004_dustroom_inspectionitem_inspectiontemplate_and_more.py",
    "backend\apps\safety\migrations\0005_nightshiftcategory_nightshiftcheckitem_and_more.py",
    "backend\apps\safety\migrations\0006_nightshiftduty_nightshiftrecord_duty.py",
    "backend\apps\safety\migrations\0007_nightshiftduty_sms_sent_at.py",

    # ---- backend: scripts + config ----
    "backend\scripts\init_dustroom_data.py",
    "backend\scripts\init_nightshift_data.py",
    "backend\config\settings\base.py",
    "backend\.env.example",

    # ---- frontend: api + router + layout ----
    "frontend\src\api\dustroom.ts",
    "frontend\src\api\nightshift.ts",
    "frontend\src\router-app.ts",
    "frontend\src\components\layout\SidebarNav.vue",

    # ---- frontend: views ----
    "frontend\src\views\safety\SafetyView.vue",
    "frontend\src\views\safety\DustRoomView.vue",
    "frontend\src\views\safety\DustRoomInspectView.vue",
    "frontend\src\views\safety\DustRoomRecordsView.vue",
    "frontend\src\views\safety\DustRoomRecordDetailView.vue",
    "frontend\src\views\safety\DustRoomAdminView.vue",
    "frontend\src\views\safety\NightShiftView.vue",
    "frontend\src\views\safety\NightShiftInspectView.vue",
    "frontend\src\views\safety\NightShiftRecordsView.vue",
    "frontend\src\views\safety\NightShiftRecordDetailView.vue",
    "frontend\src\views\safety\NightShiftAdminView.vue"
)

$missing = @()
$copied  = 0

foreach ($rel in $files) {
    $srcFile = Join-Path $Src $rel
    $dstFile = Join-Path $Dst $rel
    if (-not (Test-Path $srcFile)) {
        $missing += $rel
        continue
    }
    $dstDir = Split-Path -Parent $dstFile
    if (-not (Test-Path $dstDir)) {
        New-Item -ItemType Directory -Path $dstDir -Force | Out-Null
    }
    Copy-Item $srcFile $dstFile -Force
    $copied++
    Write-Host "  [ok] $rel"
}

Write-Host ""
Write-Host "========================================"
Write-Host "Copied: $copied file(s)"
if ($missing.Count -gt 0) {
    Write-Host "Missing in source (skipped):"
    foreach ($m in $missing) { Write-Host "  - $m" }
}
Write-Host "========================================"
Write-Host "Next steps:"
Write-Host "  cd $Dst"
Write-Host "  git status"
Write-Host "  git diff"
