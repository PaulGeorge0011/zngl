# ZS2 offline packaging and deployment

This deployment bundle targets `CentOS 7` without internet access.

## Current approach

- Do not access online yum repositories during deployment
- Do not download Python source on the server
- Do not install Python packages from the internet on the server
- Reuse an existing PostgreSQL installation when the server already has `psql`
- If PostgreSQL is not installed, install bundled `PostgreSQL 13`

## Offline assets required before packaging

Place these files under `deploy/offline-assets`:

- `deploy/offline-assets/python/Python-3.10.14.tgz`
- `deploy/offline-assets/rpms/base/*.rpm`
- `deploy/offline-assets/rpms/nginx/*.rpm`
- `deploy/offline-assets/rpms/postgresql13/*.rpm`

## Package

Run from the project root:

```powershell
.\deploy\pack-with-migrations.ps1
```

Or without generating migrations:

```powershell
.\deploy\pack.ps1
```

If the default Python index is unavailable:

```powershell
$env:ZS2_PIP_INDEX_URL = "https://pypi.tuna.tsinghua.edu.cn/simple"
.\deploy\pack-with-migrations.ps1
```

## Deploy

```bash
mkdir -p /opt/zs2
tar xzf zs2-deploy.tar.gz -C /opt/zs2
cd /opt/zs2
bash install.sh
```

## PostgreSQL note

The deployment script now prefers:

1. Reuse existing PostgreSQL on the target server
2. Otherwise install bundled `PostgreSQL 13`

This avoids the `PostgreSQL 15 + libzstd` dependency chain that is troublesome on offline `CentOS 7`.

## Python 3.10 note

`Python 3.10` requires `OpenSSL 1.1.1+`.

CentOS 7 system `openssl` is usually `1.0.2k`, which is not enough to build Python 3.10 with `_ssl`.
So the offline bundle must also include:

- `openssl11`
- `openssl11-libs`
- `openssl11-devel`
