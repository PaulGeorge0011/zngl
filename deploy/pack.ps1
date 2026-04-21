# ZS2 offline packaging script for CentOS 7
# Usage: .\deploy\pack.ps1

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$projectRoot = Split-Path -Parent $PSScriptRoot
$deployDir = Join-Path $projectRoot "deploy"
$packageFile = Join-Path $deployDir "zs2-deploy.tar.gz"
$wheelsDir = Join-Path $deployDir "wheels"
$tempDir = Join-Path $deployDir "temp"
$offlineAssetsDir = Join-Path $deployDir "offline-assets"
$localWheelCacheDir = Join-Path $projectRoot "backend\temp_wheels"
$pipIndexUrl = if ($env:ZS2_PIP_INDEX_URL) { $env:ZS2_PIP_INDEX_URL } else { "https://pypi.tuna.tsinghua.edu.cn/simple" }
$pipTrustedHost = if ($pipIndexUrl -match '^https?://([^/]+)') { $matches[1] } else { "" }
$pipProxy = if ($env:ZS2_PIP_PROXY) { $env:ZS2_PIP_PROXY } else { "" }
$pythonVersion = "310"
$pythonAbi = "cp310"

function Require-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command not found: $Name"
    }
}

function Require-Path {
    param(
        [string]$Path,
        [string]$Message
    )
    if (-not (Test-Path $Path)) {
        throw $Message
    }
}

function Require-NonEmptyDirectory {
    param(
        [string]$Path,
        [string]$Message
    )
    Require-Path $Path $Message
    $items = Get-ChildItem -Path $Path -Force -ErrorAction SilentlyContinue
    if (-not $items) {
        throw $Message
    }
}

function Invoke-Pip {
    param(
        [string[]]$PipArgs,
        [string]$FailureMessage
    )

    $managedEnvNames = @(
        "PIP_NO_INDEX",
        "PIP_NO_CACHE_DIR",
        "PIP_CACHE_DIR",
        "PIP_INDEX_URL",
        "PIP_EXTRA_INDEX_URL",
        "PIP_FIND_LINKS",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY"
    )
    $savedEnv = @{}

    foreach ($name in $managedEnvNames) {
        $savedEnv[$name] = [System.Environment]::GetEnvironmentVariable($name)
    }

    try {
        [System.Environment]::SetEnvironmentVariable("PIP_NO_INDEX", $null)
        [System.Environment]::SetEnvironmentVariable("PIP_NO_CACHE_DIR", "1")
        [System.Environment]::SetEnvironmentVariable("PIP_CACHE_DIR", $null)
        [System.Environment]::SetEnvironmentVariable("PIP_INDEX_URL", $null)
        [System.Environment]::SetEnvironmentVariable("PIP_EXTRA_INDEX_URL", $null)
        [System.Environment]::SetEnvironmentVariable("PIP_FIND_LINKS", $null)

        if ($pipProxy) {
            [System.Environment]::SetEnvironmentVariable("HTTP_PROXY", $pipProxy)
            [System.Environment]::SetEnvironmentVariable("HTTPS_PROXY", $pipProxy)
            [System.Environment]::SetEnvironmentVariable("ALL_PROXY", $pipProxy)
        } else {
            [System.Environment]::SetEnvironmentVariable("HTTP_PROXY", $null)
            [System.Environment]::SetEnvironmentVariable("HTTPS_PROXY", $null)
            [System.Environment]::SetEnvironmentVariable("ALL_PROXY", $null)
        }

        $effectiveArgs = @($PipArgs)
        if ($effectiveArgs -notcontains "--no-cache-dir") {
            $effectiveArgs += "--no-cache-dir"
        }

        & pip @effectiveArgs
        if ($LASTEXITCODE -ne 0) {
            throw $FailureMessage
        }
    } finally {
        foreach ($name in $managedEnvNames) {
            [System.Environment]::SetEnvironmentVariable($name, $savedEnv[$name])
        }
    }
}

function Test-WheelhouseCompleteness {
    param(
        [string]$ReqFile,
        [string]$WheelsDir
    )

    $checkDir = Join-Path $deployDir "_wheel-verify"
    if (Test-Path $checkDir) {
        Remove-Item -Recurse -Force $checkDir
    }
    New-Item -ItemType Directory -Path $checkDir | Out-Null

    try {
        $verifyRequirementsArgs = @(
            "download",
            "-r", $ReqFile,
            "-d", $checkDir,
            "--platform", "manylinux2014_x86_64",
            "--python-version", $pythonVersion,
            "--implementation", "cp",
            "--abi", $pythonAbi,
            "--only-binary", ":all:",
            "--no-index",
            "--find-links", $WheelsDir
        )
        Invoke-Pip -PipArgs $verifyRequirementsArgs -FailureMessage "Wheelhouse is incomplete for backend requirements"

        $verifyDaphneArgs = @(
            "download",
            "daphne",
            "-d", $checkDir,
            "--platform", "manylinux2014_x86_64",
            "--python-version", $pythonVersion,
            "--implementation", "cp",
            "--abi", $pythonAbi,
            "--only-binary", ":all:",
            "--no-index",
            "--find-links", $WheelsDir
        )
        Invoke-Pip -PipArgs $verifyDaphneArgs -FailureMessage "Wheelhouse is incomplete for daphne"
    } finally {
        Remove-Item -Recurse -Force $checkDir -ErrorAction SilentlyContinue
    }
}

Write-Host "=== ZS2 offline package build ===" -ForegroundColor Green
Write-Host "Target package: $packageFile" -ForegroundColor DarkGray
if (Test-Path $packageFile) {
    $existingPackage = Get-Item $packageFile
    Write-Host "Existing package will be replaced on successful build only: $($existingPackage.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss")) / $([math]::Round($existingPackage.Length / 1MB, 2)) MB" -ForegroundColor DarkGray
}

Require-Command "npm"
Require-Command "pip"
Require-Command "tar"

$pythonBundle = Join-Path $offlineAssetsDir "python\Python-3.10.14.tgz"
$baseRpmDir = Join-Path $offlineAssetsDir "rpms\base"
$nginxRpmDir = Join-Path $offlineAssetsDir "rpms\nginx"
$postgresRpmDir = Join-Path $offlineAssetsDir "rpms\postgresql13"

Require-Path $pythonBundle "Missing offline Python bundle: deploy\offline-assets\python\Python-3.10.14.tgz"
Require-NonEmptyDirectory $baseRpmDir "Missing base RPMs in deploy\offline-assets\rpms\base"
Require-NonEmptyDirectory $nginxRpmDir "Missing nginx RPMs in deploy\offline-assets\rpms\nginx"
Require-NonEmptyDirectory $postgresRpmDir "Missing PostgreSQL 13 RPMs in deploy\offline-assets\rpms\postgresql13"

Write-Host "`n[1/5] Build frontend" -ForegroundColor Cyan
Push-Location (Join-Path $projectRoot "frontend")
try {
    $viteAppBase = if ($env:ZS2_VITE_APP_BASE) { $env:ZS2_VITE_APP_BASE } else { "" }
    $viteApiBase = if ($env:ZS2_VITE_API_BASE) { $env:ZS2_VITE_API_BASE } else { "" }
    $viteWsBase = if ($env:ZS2_VITE_WS_BASE) { $env:ZS2_VITE_WS_BASE } else { "" }
    $envContent = @(
        "VITE_APP_BASE=$viteAppBase",
        "VITE_API_BASE=$viteApiBase",
        "VITE_WS_BASE=$viteWsBase"
    ) -join [System.Environment]::NewLine
    Set-Content -Path ".env.production" -Value $envContent -Encoding UTF8

    Write-Host "  npm install" -ForegroundColor Gray
    npm install
    if ($LASTEXITCODE -ne 0) { throw "npm install failed" }

    Write-Host "  npm run build" -ForegroundColor Gray
    npm run build
    if ($LASTEXITCODE -ne 0) { throw "frontend build failed" }
} finally {
    Pop-Location
}
Write-Host "  frontend build complete" -ForegroundColor Green

Write-Host "`n[2/5] Download Linux wheels for Python 3.10" -ForegroundColor Cyan
if (Test-Path $wheelsDir) {
    Remove-Item -Recurse -Force $wheelsDir
}
New-Item -ItemType Directory -Path $wheelsDir | Out-Null

$reqFile = Join-Path $projectRoot "backend\requirements.txt"
$bootstrapPurePythonPackages = @(
    "exceptiongroup",
    "sniffio",
    "tomli",
    "typing_extensions"
)

if (Test-Path $localWheelCacheDir) {
    Write-Host "  prime wheelhouse from backend/temp_wheels" -ForegroundColor Gray
    Get-ChildItem -Path $localWheelCacheDir -Filter "*.whl" |
        Where-Object {
            $_.Name -match "py3-none-any|py2.py3-none-any|manylinux|musllinux" -and
            $_.Name -notmatch "win32|win_amd64|macosx"
        } |
        Copy-Item -Destination $wheelsDir -Force
}

foreach ($pkg in $bootstrapPurePythonPackages) {
    $bootstrapArgs = @(
        "download",
        $pkg,
        "-d", $wheelsDir,
        "--only-binary", ":all:",
        "--platform", "any",
        "--index-url", $pipIndexUrl,
        "--retries", "2",
        "--timeout", "30"
    )
    if ($pipTrustedHost) {
        $bootstrapArgs += @("--trusted-host", $pipTrustedHost)
    }

    Invoke-Pip -PipArgs $bootstrapArgs -FailureMessage "Failed to download bootstrap package '$pkg' from $pipIndexUrl"
}

Get-ChildItem -Path $wheelsDir -Filter "*.whl" |
    Where-Object {
        $_.Name -match "win32|win_amd64|macosx" -and
        $_.Name -match "exceptiongroup|sniffio|tomli|typing_extensions"
    } |
    Remove-Item -Force -ErrorAction SilentlyContinue

$requirementsArgs = @(
    "download",
    "-r", $reqFile,
    "-d", $wheelsDir,
    "--platform", "manylinux2014_x86_64",
    "--python-version", $pythonVersion,
    "--implementation", "cp",
    "--abi", $pythonAbi,
    "--only-binary", ":all:",
    "--index-url", $pipIndexUrl,
    "--retries", "2",
    "--timeout", "30"
)
if ($pipTrustedHost) {
    $requirementsArgs += @("--trusted-host", $pipTrustedHost)
}
Invoke-Pip -PipArgs $requirementsArgs -FailureMessage "Failed to download Linux wheels for backend requirements from $pipIndexUrl"

$daphneArgs = @(
    "download",
    "daphne",
    "-d", $wheelsDir,
    "--platform", "manylinux2014_x86_64",
    "--python-version", $pythonVersion,
    "--implementation", "cp",
    "--abi", $pythonAbi,
    "--only-binary", ":all:",
    "--index-url", $pipIndexUrl,
    "--retries", "2",
    "--timeout", "30"
)
if ($pipTrustedHost) {
    $daphneArgs += @("--trusted-host", $pipTrustedHost)
}
Invoke-Pip -PipArgs $daphneArgs -FailureMessage "Failed to download Linux wheels for daphne from $pipIndexUrl"

$invalidWheels = Get-ChildItem -Path $wheelsDir -Filter "*.whl" |
    Where-Object { $_.Name -match "win32|win_amd64|macosx" }
if ($invalidWheels) {
    $names = $invalidWheels.Name -join ", "
    throw "Found non-Linux wheels in wheelhouse: $names"
}

Test-WheelhouseCompleteness -ReqFile $reqFile -WheelsDir $wheelsDir

Write-Host "  wheelhouse ready" -ForegroundColor Green

Write-Host "`n[3/5] Prepare temp directory" -ForegroundColor Cyan
if (Test-Path $tempDir) {
    Remove-Item -Recurse -Force $tempDir
}
New-Item -ItemType Directory -Path $tempDir | Out-Null

Write-Host "`n[4/5] Collect package content" -ForegroundColor Cyan
Copy-Item -Recurse (Join-Path $projectRoot "backend") (Join-Path $tempDir "backend")
@("venv", "staticfiles", ".env", "db.sqlite3", "temp_wheels") | ForEach-Object {
    Remove-Item -Recurse -Force (Join-Path $tempDir "backend\$_") -ErrorAction SilentlyContinue
}
Get-ChildItem -Path (Join-Path $tempDir "backend") -Recurse -Directory -Filter "__pycache__" |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

New-Item -ItemType Directory -Path (Join-Path $tempDir "frontend") | Out-Null
Copy-Item -Recurse (Join-Path $projectRoot "frontend\dist") (Join-Path $tempDir "frontend\dist")
Copy-Item -Recurse $wheelsDir (Join-Path $tempDir "wheels")
Copy-Item -Recurse $offlineAssetsDir (Join-Path $tempDir "offline-assets")
Copy-Item (Join-Path $deployDir "install.sh") $tempDir
Copy-Item (Join-Path $deployDir "README.md") $tempDir
Copy-Item (Join-Path $deployDir "QUICKSTART.md") $tempDir -ErrorAction SilentlyContinue

Write-Host "`n[5/5] Create tarball" -ForegroundColor Cyan
if (Test-Path $packageFile) {
    Remove-Item -Force $packageFile
}
Push-Location $deployDir
try {
    tar -czf zs2-deploy.tar.gz -C temp .
    if ($LASTEXITCODE -ne 0) { throw "tar failed" }
} finally {
    Pop-Location
    Remove-Item -Recurse -Force $tempDir -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force $wheelsDir -ErrorAction SilentlyContinue
}

$sizeMB = [math]::Round((Get-Item $packageFile).Length / 1MB, 2)

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Offline deployment package created" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "File: $packageFile" -ForegroundColor Yellow
Write-Host "Size: $sizeMB MB" -ForegroundColor Yellow
Write-Host ""
Write-Host "Included: frontend dist, Linux wheels, Python source tarball, nginx/postgresql/base RPMs" -ForegroundColor Cyan
