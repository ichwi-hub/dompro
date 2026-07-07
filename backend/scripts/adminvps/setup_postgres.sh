#!/usr/bin/env bash
# DomPro — первичная настройка PostgreSQL 16 на AdminVPS (1 GB RAM, dev).
# Запуск на сервере от root:
#   bash setup_postgres.sh <CLIENT_IP> [DB_PASSWORD]
set -euo pipefail

CLIENT_IP="${1:?Usage: setup_postgres.sh <CLIENT_IP> [DB_PASSWORD]}"
DB_PASSWORD="${2:-$(openssl rand -base64 24 | tr -d '/+=' | head -c 24)}"
DB_NAME="dompro"
DB_USER="dompro"

export DEBIAN_FRONTEND=noninteractive

echo "==> Обновление пакетов и установка PostgreSQL 16"
apt-get update -qq
apt-get install -y -qq postgresql-16 postgresql-contrib-16 ufw openssl

PG_CONF="/etc/postgresql/16/main/postgresql.conf"
PG_HBA="/etc/postgresql/16/main/pg_hba.conf"
TUNE_CONF="/etc/postgresql/16/main/conf.d/dompro-low-memory.conf"

echo "==> Тюнинг PostgreSQL под 1 GB RAM (консервативный dev-профиль)"
mkdir -p /etc/postgresql/16/main/conf.d
cat > "${TUNE_CONF}" <<'EOF'
# DomPro dev — VPS 1 GB RAM (AdminVPS)
# Оставляем ~700+ MB для ОС, SSH и прочих процессов.

shared_buffers = 128MB
effective_cache_size = 256MB
work_mem = 4MB
maintenance_work_mem = 64MB
max_connections = 20
wal_buffers = 4MB
random_page_cost = 1.1
effective_io_concurrency = 200
checkpoint_completion_target = 0.9
max_wal_size = 256MB
min_wal_size = 64MB
default_statistics_target = 100
huge_pages = off
EOF

echo "==> Сеть и SSL"
sed -i "s/^#*listen_addresses.*/listen_addresses = '*'/" "${PG_CONF}"
sed -i "s/^#*ssl = .*/ssl = on/" "${PG_CONF}"
# Ubuntu snakeoil — достаточно для dev (шифрование в транзите)
if ! grep -q "^ssl_cert_file" "${PG_CONF}"; then
  cat >> "${PG_CONF}" <<'EOF'

ssl_cert_file = '/etc/ssl/certs/ssl-cert-snakeoil.pem'
ssl_key_file = '/etc/ssl/private/ssl-cert-snakeoil.key'
EOF
fi

echo "==> pg_hba: только SSL с IP разработчика"
# Удаляем широкие host/hostssl-правила (local unix-сокеты оставляем)
grep -Ev '^(host|hostssl) ' "${PG_HBA}" > "${PG_HBA}.tmp" || true
mv "${PG_HBA}.tmp" "${PG_HBA}"
cat >> "${PG_HBA}" <<EOF

# DomPro dev — удалённый доступ только с IP разработчика, только SSL
hostssl ${DB_NAME} ${DB_USER} ${CLIENT_IP}/32 scram-sha-256
EOF

echo "==> База и пользователь"
sudo -u postgres psql -v ON_ERROR_STOP=1 <<SQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '${DB_USER}') THEN
    CREATE ROLE ${DB_USER} LOGIN PASSWORD '${DB_PASSWORD}';
  ELSE
    ALTER ROLE ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';
  END IF;
END
\$\$;
SQL
if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1; then
  sudo -u postgres createdb -O "${DB_USER}" "${DB_NAME}"
fi
sudo -u postgres psql -v ON_ERROR_STOP=1 -c "GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};"

sudo -u postgres psql -d "${DB_NAME}" -v ON_ERROR_STOP=1 <<SQL
GRANT ALL ON SCHEMA public TO ${DB_USER};
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO ${DB_USER};
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO ${DB_USER};
SQL

echo "==> Firewall (ufw)"
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp comment 'SSH'
ufw allow from "${CLIENT_IP}" to any port 5432 proto tcp comment 'PostgreSQL dev client'
ufw --force enable

systemctl restart postgresql
systemctl enable postgresql

echo ""
echo "========== DomPro PostgreSQL готов =========="
echo "Host:     $(curl -s -4 ifconfig.me || hostname -I | awk '{print $1}')"
echo "Port:     5432"
echo "Database: ${DB_NAME}"
echo "User:     ${DB_USER}"
echo "Password: ${DB_PASSWORD}"
echo "SSL:      require (snakeoil cert)"
echo "Allowed:  ${CLIENT_IP}/32"
echo ""
echo "DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@$(curl -s -4 ifconfig.me):5432/${DB_NAME}?sslmode=require"
echo "============================================="
