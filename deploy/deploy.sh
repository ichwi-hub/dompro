#!/usr/bin/env bash
# deploy.sh — деплой DomPro на Ubuntu VPS (AdminVPS)
# Запуск с машины разработчика (rsync) или на сервере после git pull.
#
# Использование:
#   ./deploy/deploy.sh                    # локально на VPS
#   REMOTE=root@157.22.231.226 ./deploy/deploy.sh  # с dev-машины через rsync
#
set -euo pipefail

APP_DIR="/opt/dompro"
APP_USER="dompro"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "==> DomPro deploy → $APP_DIR"

# --- Опционально: синхронизация с dev-машины ---
if [[ -n "${REMOTE:-}" ]]; then
  echo "==> Rsync $PROJECT_ROOT → $REMOTE:$APP_DIR"
  rsync -avz --delete \
    --exclude '.venv' \
    --exclude '__pycache__' \
    --exclude '.git' \
    --exclude 'data/storage' \
    --exclude '.env' \
    "$PROJECT_ROOT/" "$REMOTE:$APP_DIR/"
  ssh "$REMOTE" "bash $APP_DIR/deploy/deploy.sh"
  exit 0
fi

# --- Подготовка каталогов ---
sudo mkdir -p "$APP_DIR"/{backend,frontend,data/storage,deploy}
sudo chown -R "$APP_USER:$APP_USER" "$APP_DIR"

# Если скрипт запущен из репозитория — копируем файлы
if [[ "$PROJECT_ROOT" != "$APP_DIR" ]]; then
  echo "==> Копирование backend и frontend"
  rsync -a --delete \
    --exclude '.venv' --exclude '__pycache__' \
    "$PROJECT_ROOT/backend/" "$APP_DIR/backend/"
  rsync -a --delete "$PROJECT_ROOT/frontend/" "$APP_DIR/frontend/"
  rsync -a "$PROJECT_ROOT/deploy/" "$APP_DIR/deploy/"
  rsync -a "$PROJECT_ROOT/database/" "$APP_DIR/database/" 2>/dev/null || true
fi

# --- .env ---
if [[ ! -f "$APP_DIR/.env" ]]; then
  if [[ -f "$APP_DIR/backend/.env" ]]; then
    cp "$APP_DIR/backend/.env" "$APP_DIR/.env"
  else
    echo "ERROR: создайте $APP_DIR/.env (см. .env.example)"
    exit 1
  fi
fi
# Production URL для ссылок на файлы
if ! grep -q '^API_PUBLIC_URL=' "$APP_DIR/.env"; then
  echo 'API_PUBLIC_URL=https://dompro.ru' >> "$APP_DIR/.env"
fi

# --- Python venv ---
echo "==> Python venv + requirements"
sudo -u "$APP_USER" bash -c "
  cd $APP_DIR/backend
  python3 -m venv .venv
  .venv/bin/pip install --upgrade pip
  .venv/bin/pip install -r requirements.txt
"

# --- Хранилище ---
sudo -u "$APP_USER" mkdir -p "$APP_DIR/data/storage"/{verifications,contracts}

# --- Systemd ---
echo "==> systemd dompro-api"
sudo cp "$APP_DIR/deploy/dompro-api.service" /etc/systemd/system/dompro-api.service
sudo systemctl daemon-reload
sudo systemctl enable dompro-api
sudo systemctl restart dompro-api
sudo systemctl status dompro-api --no-pager || true

# --- Nginx ---
echo "==> nginx"
sudo cp "$APP_DIR/deploy/nginx/dompro" /etc/nginx/sites-available/dompro
sudo ln -sf /etc/nginx/sites-available/dompro /etc/nginx/sites-enabled/dompro
sudo nginx -t
sudo systemctl reload nginx

echo "==> Deploy complete. Проверка: curl -s http://127.0.0.1/health"
