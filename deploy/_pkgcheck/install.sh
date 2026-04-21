#!/bin/bash
# ZS2 offline deployment script
# Target: CentOS 7 without internet access

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PROJECT_DIR="/opt/zs2"
PYTHON_VERSION="3.10.14"
PYTHON_PREFIX="/usr/local/python3"
PYTHON_BIN="${PYTHON_PREFIX}/bin/python3.10"
PIP_BIN="${PYTHON_PREFIX}/bin/pip3.10"
OPENSSL11_PREFIX="/usr/local/openssl11"
CURRENT_DIR="$(cd "$(dirname "$0")" && pwd)"
OFFLINE_DIR="${CURRENT_DIR}/offline-assets"
WHEELS_DIR="${CURRENT_DIR}/wheels"
PG_SERVICE_NAME=""
PG_HBA_PATH=""
PG_AFTER_UNIT="network.target"

log() {
    echo -e "${GREEN}$1${NC}"
}

warn() {
    echo -e "${YELLOW}$1${NC}"
}

fail() {
    echo -e "${RED}$1${NC}"
    exit 1
}

show_nginx_debug_info() {
    warn "\nnginx startup diagnostics:"
    systemctl status nginx --no-pager -l || true
    journalctl -u nginx -n 50 --no-pager || true
    if command_exists ss; then
        warn "\nPort listeners for 80 and 9527:"
        ss -ltnp | grep -E ':(80|9527)\s' || true
    fi
    warn "\nEffective nginx listen directives:"
    nginx -T 2>/dev/null | grep -n "listen " || true
}

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

detect_pg_hba_path() {
    if [ -f /var/lib/pgsql/13/data/pg_hba.conf ]; then
        echo /var/lib/pgsql/13/data/pg_hba.conf
        return
    fi

    if [ -f /var/lib/pgsql/15/data/pg_hba.conf ]; then
        echo /var/lib/pgsql/15/data/pg_hba.conf
        return
    fi

    if [ -f /var/lib/pgsql/data/pg_hba.conf ]; then
        echo /var/lib/pgsql/data/pg_hba.conf
        return
    fi

    local found=""
    found="$(find /var/lib/pgsql -maxdepth 4 -name pg_hba.conf 2>/dev/null | head -n 1 || true)"
    if [ -n "$found" ]; then
        echo "$found"
    fi
}

detect_pg_service() {
    if systemctl list-unit-files | grep -q '^postgresql-13\.service'; then
        echo "postgresql-13"
        return
    fi

    if systemctl list-unit-files | grep -q '^postgresql-15\.service'; then
        echo "postgresql-15"
        return
    fi

    if systemctl list-unit-files | grep -q '^postgresql\.service'; then
        echo "postgresql"
        return
    fi
}

install_local_rpms() {
    local dir="$1"
    local name="$2"

    [ -d "$dir" ] || fail "Missing offline RPM directory: $dir"

    shopt -s nullglob
    local rpms=("$dir"/*.rpm)
    shopt -u nullglob

    [ ${#rpms[@]} -gt 0 ] || fail "${name} RPM directory is empty: $dir"

    yum localinstall -y --disablerepo='*' "${rpms[@]}"
}

ensure_required_files() {
    [ "$EUID" -eq 0 ] || fail "Run as root: sudo bash install.sh"
    [ -d "${CURRENT_DIR}/backend" ] || fail "Missing backend directory"
    [ -d "${CURRENT_DIR}/frontend/dist" ] || fail "Missing frontend/dist directory"
    [ -d "${WHEELS_DIR}" ] || fail "Missing wheels directory"
    [ -f "${OFFLINE_DIR}/python/Python-${PYTHON_VERSION}.tgz" ] || fail "Missing Python bundle: offline-assets/python/Python-${PYTHON_VERSION}.tgz"
    [ -d "${OFFLINE_DIR}/rpms/base" ] || fail "Missing base RPM directory"
    [ -d "${OFFLINE_DIR}/rpms/nginx" ] || fail "Missing nginx RPM directory"
    [ -d "${OFFLINE_DIR}/rpms/postgresql13" ] || fail "Missing postgresql13 RPM directory"
}

prepare_project_dir() {
    mkdir -p "${PROJECT_DIR}"
    # Exclude backend/.env so any manually configured SSO secrets on the server are preserved
    rsync -a --delete --exclude 'backend/.env' "${CURRENT_DIR}/" "${PROJECT_DIR}/"
}

install_base_dependencies() {
    warn "\n[1/6] Install base system packages from bundled RPMs"
    install_local_rpms "${OFFLINE_DIR}/rpms/base" "Base dependency"
}

install_python() {
    warn "\n[2/6] Install Python ${PYTHON_VERSION}"
    if [ -x "${PYTHON_BIN}" ]; then
        if "${PYTHON_BIN}" -c "import ssl" >/dev/null 2>&1; then
            log "Python ${PYTHON_VERSION} already exists with ssl support, skip"
            return
        fi

        warn "Existing Python ${PYTHON_VERSION} is missing ssl support, rebuild"
        rm -rf "${PYTHON_PREFIX}"
    fi

    mkdir -p /usr/local/src
    mkdir -p "${OPENSSL11_PREFIX}/include" "${OPENSSL11_PREFIX}/lib"

    if [ -d /usr/include/openssl11/openssl ]; then
        ln -sfn /usr/include/openssl11/openssl "${OPENSSL11_PREFIX}/include/openssl"
    else
        fail "Missing OpenSSL 1.1.1 headers under /usr/include/openssl11/openssl"
    fi

    if [ -f /usr/lib64/openssl11/libssl.so.1.1 ] && [ -f /usr/lib64/openssl11/libcrypto.so.1.1 ]; then
        ln -sfn /usr/lib64/openssl11/libssl.so.1.1 "${OPENSSL11_PREFIX}/lib/libssl.so"
        ln -sfn /usr/lib64/openssl11/libcrypto.so.1.1 "${OPENSSL11_PREFIX}/lib/libcrypto.so"
    elif [ -f /usr/lib64/libssl.so.1.1 ] && [ -f /usr/lib64/libcrypto.so.1.1 ]; then
        ln -sfn /usr/lib64/libssl.so.1.1 "${OPENSSL11_PREFIX}/lib/libssl.so"
        ln -sfn /usr/lib64/libcrypto.so.1.1 "${OPENSSL11_PREFIX}/lib/libcrypto.so"
    else
        fail "Missing OpenSSL 1.1.1 runtime libs under /usr/lib64/openssl11 or /usr/lib64"
    fi

    cp "${OFFLINE_DIR}/python/Python-${PYTHON_VERSION}.tgz" /usr/local/src/
    cd /usr/local/src
    tar xzf "Python-${PYTHON_VERSION}.tgz"
    cd "Python-${PYTHON_VERSION}"
    export CPPFLAGS="-I${OPENSSL11_PREFIX}/include"
    export LDFLAGS="-L${OPENSSL11_PREFIX}/lib -Wl,-rpath,${OPENSSL11_PREFIX}/lib"
    ./configure --prefix="${PYTHON_PREFIX}" --with-openssl="${OPENSSL11_PREFIX}" --with-openssl-rpath=auto
    make -j"$(nproc)"
    make altinstall
    ln -sf "${PYTHON_BIN}" /usr/local/bin/python3
    ln -sf "${PIP_BIN}" /usr/local/bin/pip3
    "${PYTHON_BIN}" -c "import ssl; print(ssl.OPENSSL_VERSION)" >/dev/null
    log "Python installed"
}

install_postgresql() {
    warn "\n[3/6] Prepare PostgreSQL"

    if command_exists psql; then
        PG_SERVICE_NAME="$(detect_pg_service)"
        PG_HBA_PATH="$(detect_pg_hba_path)"
        if [ -n "${PG_SERVICE_NAME}" ]; then
            systemctl enable "${PG_SERVICE_NAME}" >/dev/null 2>&1 || true
            systemctl start "${PG_SERVICE_NAME}" >/dev/null 2>&1 || true
            PG_AFTER_UNIT="${PG_SERVICE_NAME}.service"
        fi
        log "Existing PostgreSQL detected, reuse current installation"
        return
    fi

    warn "PostgreSQL not found, install bundled PostgreSQL 13"
    if ! rpm -q postgresql13-server >/dev/null 2>&1; then
        install_local_rpms "${OFFLINE_DIR}/rpms/postgresql13" "PostgreSQL 13"
    else
        log "PostgreSQL 13 already installed, skip RPM install"
    fi

    if [ ! -f /var/lib/pgsql/13/data/PG_VERSION ]; then
        /usr/pgsql-13/bin/postgresql-13-setup initdb
    fi

    PG_SERVICE_NAME="postgresql-13"
    PG_HBA_PATH="/var/lib/pgsql/13/data/pg_hba.conf"
    PG_AFTER_UNIT="postgresql-13.service"

    systemctl enable "${PG_SERVICE_NAME}"
    systemctl start "${PG_SERVICE_NAME}"

    if [ -n "${PG_HBA_PATH}" ] && ! grep -q '^host\s\+all\s\+all\s\+127\.0\.0\.1/32\s\+md5' "${PG_HBA_PATH}"; then
        echo 'host all all 127.0.0.1/32 md5' >> "${PG_HBA_PATH}"
    fi
    systemctl restart "${PG_SERVICE_NAME}"
}

create_database() {
    local db_password="$1"

    if ! su - postgres -c "psql -tAc \"SELECT 1 FROM pg_roles WHERE rolname='zs2_user'\"" | grep -q 1; then
        su - postgres -c "psql -c \"CREATE USER zs2_user WITH PASSWORD '${db_password}';\""
    fi

    if ! su - postgres -c "psql -tAc \"SELECT 1 FROM pg_database WHERE datname='zs2_db'\"" | grep -q 1; then
        su - postgres -c "psql -c \"CREATE DATABASE zs2_db OWNER zs2_user;\""
    fi
}

install_nginx() {
    warn "\n[4/6] Install nginx from bundled RPMs"
    if ! rpm -q nginx >/dev/null 2>&1; then
        install_local_rpms "${OFFLINE_DIR}/rpms/nginx" "nginx"
    else
        log "nginx already installed, skip RPM install"
    fi
    systemctl enable nginx
}

install_backend() {
    local db_password="$1"
    local server_ip=""

    server_ip="$(hostname -I | awk '{print $1}')"
    if [ -z "${server_ip}" ]; then
        server_ip="127.0.0.1"
    fi

    warn "\n[5/6] Install backend and Python dependencies offline"
    cd "${PROJECT_DIR}/backend"

    "${PYTHON_BIN}" -m venv venv
    source venv/bin/activate

    pip install --no-index --find-links="${PROJECT_DIR}/wheels" -r requirements.txt
    pip install --no-index --find-links="${PROJECT_DIR}/wheels" daphne

    if [ -f .env ]; then
        warn "Existing backend/.env detected — preserving it."
        warn "If you need to enable SSO, manually add SSO_* keys to ${PROJECT_DIR}/backend/.env"
    else
        cat > .env <<EOF
DEBUG=False
SECRET_KEY=$(openssl rand -base64 32)
ALLOWED_HOSTS=*

DB_NAME=zs2_db
DB_USER=zs2_user
DB_PASSWORD=${db_password}
DB_HOST=127.0.0.1
DB_PORT=5432

CORS_ALLOWED_ORIGINS=http://${server_ip}:9527
CSRF_TRUSTED_ORIGINS=http://${server_ip}:9527

OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:35b
RAGFLOW_BASE_URL=
RAGFLOW_API_KEY=

# SSO 云南中烟登录（外网部署时填入，不要提交到版本库）
# APP_EXTERNAL_BASE_URL=https://yxcf-yzyy.ynzy-tobacco.com/zszngl
# SSO_ENABLED=False
# SSO_CLIENT_ID=
# SSO_CLIENT_SECRET=
# SSO_BASE_URL=
# SSO_AUTHORIZE_URL=
# SSO_TOKEN_URL=
# SSO_USERINFO_URL=
# SSO_REDIRECT_URI=https://yxcf-yzyy.ynzy-tobacco.com/zszngl/api/users/sso/callback/
EOF
        log "backend/.env created"
    fi

    export DJANGO_SETTINGS_MODULE=config.settings.development
    python manage.py migrate
    python manage.py collectstatic --noinput
    mkdir -p media

    python manage.py shell <<'PYEOF'
exec(open('scripts/init_demo_data.py', encoding='utf-8').read())
exec(open('scripts/init_safety_data.py', encoding='utf-8').read())
PYEOF

    deactivate
    log "Backend deployed"
}

configure_services() {
    warn "\n[6/6] Configure nginx and systemd"

    cat > /etc/nginx/conf.d/zs2.conf <<'NGINXEOF'
upstream daphne {
    server 127.0.0.1:8000;
}

server {
    listen 9527;
    server_name _;
    client_max_body_size 20M;

    location / {
        root /opt/zs2/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://daphne;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /opt/zs2/backend/staticfiles/;
    }

    location /media/ {
        alias /opt/zs2/backend/media/;
    }

    location /ws/ {
        proxy_pass http://daphne;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
NGINXEOF

    cat > /etc/systemd/system/zs2.service <<SERVICEEOF
[Unit]
Description=ZS2 Management System (Daphne)
After=${PG_AFTER_UNIT}

[Service]
Type=simple
User=root
WorkingDirectory=/opt/zs2/backend
Environment=DJANGO_SETTINGS_MODULE=config.settings.development
ExecStart=/opt/zs2/backend/venv/bin/daphne -b 0.0.0.0 -p 8000 config.asgi:application
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICEEOF

    nginx -t
    systemctl daemon-reload
    systemctl enable zs2
    if command_exists semanage; then
        semanage port -a -t http_port_t -p tcp 9527 >/dev/null 2>&1 || \
        semanage port -m -t http_port_t -p tcp 9527 >/dev/null 2>&1 || true
    fi
    restorecon -Rv /etc/nginx /run /var/run /usr/sbin/nginx >/dev/null 2>&1 || true
    setsebool -P httpd_can_network_connect 1 >/dev/null 2>&1 || true
    if ! systemctl restart nginx; then
        show_nginx_debug_info
        fail "Failed to restart nginx"
    fi
    systemctl restart zs2

    firewall-cmd --permanent --add-port=9527/tcp >/dev/null 2>&1 || true
    firewall-cmd --reload >/dev/null 2>&1 || true
}

main() {
    local db_password=""

    echo -e "${GREEN}=== ZS2 offline deployment for CentOS 7 ===${NC}"
    ensure_required_files

    read -rsp "Enter PostgreSQL password: " db_password
    echo
    [ -n "$db_password" ] || fail "Database password cannot be empty"

    install_base_dependencies
    prepare_project_dir
    install_python
    install_postgresql
    create_database "$db_password"
    install_nginx
    install_backend "$db_password"
    configure_services

    echo -e "\n${GREEN}========================================${NC}"
    echo -e "${GREEN}Deployment completed${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo -e "URL: ${YELLOW}http://$(hostname -I | awk '{print $1}'):9000${NC}"
    echo -e "Service: ${YELLOW}systemctl status zs2${NC}"
}

main "$@"
