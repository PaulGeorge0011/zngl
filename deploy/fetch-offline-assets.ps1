$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$projectRoot = Split-Path -Parent $PSScriptRoot
$offlineAssetsDir = Join-Path $PSScriptRoot "offline-assets"
$pythonDir = Join-Path $offlineAssetsDir "python"
$baseRpmDir = Join-Path $offlineAssetsDir "rpms\base"
$nginxRpmDir = Join-Path $offlineAssetsDir "rpms\nginx"
$postgresRpmDir = Join-Path $offlineAssetsDir "rpms\postgresql13"

$pythonVersion = "3.10.14"
$pythonUrl = "https://www.python.org/ftp/python/$pythonVersion/Python-$pythonVersion.tgz"

$centosSources = @(
    "https://vault.centos.org/7.9.2009/updates/x86_64/Packages/",
    "https://vault.centos.org/7.9.2009/os/x86_64/Packages/",
    "https://vault.centos.org/7.9.2009/extras/x86_64/Packages/",
    "https://archives.fedoraproject.org/pub/archive/epel/7/x86_64/Packages/z/"
)

$basePackages = @(
    "rsync",
    "gcc",
    "gcc-c++",
    "cpp",
    "make",
    "mpfr",
    "libmpc",
    "glibc-devel",
    "glibc-headers",
    "kernel-headers",
    "libstdc++-devel",
    "libicu",
    "zlib",
    "zlib-devel",
    "bzip2-devel",
    "openssl",
    "openssl-libs",
    "openssl-devel",
    "openssl11",
    "openssl11-libs",
    "openssl11-devel",
    "keyutils-libs-devel",
    "krb5-libs",
    "krb5-devel",
    "libcom_err-devel",
    "libverto-devel",
    "libkadm5",
    "libselinux-devel",
    "libsepol-devel",
    "pcre2",
    "pcre-devel",
    "ncurses-devel",
    "sqlite-devel",
    "readline-devel",
    "libffi-devel",
    "xz-devel"
)

$postgresBaseUrl = "https://ftp.postgresql.org/pub/repos/yum/13/redhat/rhel-7-x86_64/"
$postgresPackages = @(
    "postgresql13-libs",
    "postgresql13",
    "postgresql13-server"
)

$nginxBaseUrl = "https://nginx.org/packages/rhel/7Server/x86_64/RPMS/"
$nginxPackages = @(
    "nginx"
)

function Ensure-Dir {
    param([string]$Path)
    New-Item -ItemType Directory -Force -Path $Path | Out-Null
}

function Get-LinksFromIndex {
    param([string]$Url)

    $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing
    return [regex]::Matches($resp.Content, 'href="([^"]+)"') |
        ForEach-Object { $_.Groups[1].Value } |
        Where-Object { $_ -like "*.rpm" -or $_ -like "*.tgz" }
}

function Select-LatestPackage {
    param(
        [string[]]$Candidates,
        [string]$PackageName
    )

    $regex = "^" + [regex]::Escape($PackageName) + "-\d.+\.rpm$"
    $matches = $Candidates | Where-Object { $_ -match $regex }
    if (-not $matches) {
        throw "Package not found in index: $PackageName"
    }

    return $matches |
        Sort-Object `
            @{ Expression = {
                if ($_ -match ('^' + [regex]::Escape($PackageName) + '-(?<ver>\d+(?:\.\d+)+)')) {
                    try { [version]$matches['ver'] } catch { [version]'0.0.0.0' }
                } else {
                    [version]'0.0.0.0'
                }
            }; Descending = $true }, `
            @{ Expression = { $_ }; Descending = $true } |
        Select-Object -First 1
}

function Download-File {
    param(
        [string]$Url,
        [string]$TargetDir
    )

    Ensure-Dir $TargetDir
    $fileName = Split-Path $Url -Leaf
    $targetPath = Join-Path $TargetDir $fileName
    if (Test-Path $targetPath) {
        Write-Host "Skip existing $fileName" -ForegroundColor DarkGray
        return
    }

    Write-Host "Download $fileName" -ForegroundColor Gray
    Invoke-WebRequest -Uri $Url -OutFile $targetPath
}

function Remove-StalePackageFiles {
    param(
        [string]$TargetDir,
        [string]$PackageName,
        [string]$KeepFileName
    )

    if (-not (Test-Path $TargetDir)) {
        return
    }

    $regex = "^" + [regex]::Escape($PackageName) + "-\d.+\.rpm$"
    Get-ChildItem -Path $TargetDir -Filter "*.rpm" -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -match $regex -and $_.Name -ne $KeepFileName } |
        Remove-Item -Force
}

function Download-CentosPackage {
    param(
        [string]$PackageName,
        [string]$TargetDir
    )

    foreach ($source in $centosSources) {
        try {
            $links = Get-LinksFromIndex -Url $source
            $file = Select-LatestPackage -Candidates $links -PackageName $PackageName
            Remove-StalePackageFiles -TargetDir $TargetDir -PackageName $PackageName -KeepFileName $file
            Download-File -Url ($source + $file) -TargetDir $TargetDir
            return
        } catch {
            continue
        }
    }

    throw "Failed to locate package from CentOS vault: $PackageName"
}

function Download-IndexedPackage {
    param(
        [string]$BaseUrl,
        [string]$PackageName,
        [string]$TargetDir
    )

    $links = Get-LinksFromIndex -Url $BaseUrl
    $file = Select-LatestPackage -Candidates $links -PackageName $PackageName
    Remove-StalePackageFiles -TargetDir $TargetDir -PackageName $PackageName -KeepFileName $file
    Download-File -Url ($BaseUrl + $file) -TargetDir $TargetDir
}

Write-Host "=== Fetch offline assets for CentOS 7 ===" -ForegroundColor Green

Ensure-Dir $pythonDir
Ensure-Dir $baseRpmDir
Ensure-Dir $nginxRpmDir
Ensure-Dir $postgresRpmDir

Write-Host "`n[1/4] Python source" -ForegroundColor Cyan
Download-File -Url $pythonUrl -TargetDir $pythonDir

Write-Host "`n[2/4] Base RPMs" -ForegroundColor Cyan
foreach ($pkg in $basePackages) {
    Download-CentosPackage -PackageName $pkg -TargetDir $baseRpmDir
}

Write-Host "`n[3/4] PostgreSQL 13 RPMs" -ForegroundColor Cyan
foreach ($pkg in $postgresPackages) {
    Download-IndexedPackage -BaseUrl $postgresBaseUrl -PackageName $pkg -TargetDir $postgresRpmDir
}

Write-Host "`n[4/4] nginx RPMs" -ForegroundColor Cyan
foreach ($pkg in $nginxPackages) {
    Download-IndexedPackage -BaseUrl $nginxBaseUrl -PackageName $pkg -TargetDir $nginxRpmDir
}

Write-Host "`nOffline assets download complete." -ForegroundColor Green
