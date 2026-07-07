# UFW — правила файрвола для DomPro (AdminVPS)

Выполнять на VPS под `root`. Замените `DEV_IP` на IP машины разработчика.

```bash
# Базовые правила
sudo ufw default deny incoming
sudo ufw default allow outgoing

# SSH (обязательно до enable!)
sudo ufw allow 22/tcp comment 'SSH'

# Веб-сервер (публичный доступ к сайту)
sudo ufw allow 80/tcp comment 'HTTP'
sudo ufw allow 443/tcp comment 'HTTPS'

# PostgreSQL — только с IP разработчика (не открывать всем!)
sudo ufw allow from DEV_IP to any port 5432 proto tcp comment 'PostgreSQL dev only'

# Применить
sudo ufw enable
sudo ufw status verbose
```

## Пример для IP `87.121.38.47`

```bash
sudo ufw allow from 87.121.38.47 to any port 5432 proto tcp comment 'PostgreSQL dev'
```

## Certbot (Let's Encrypt)

После настройки DNS `dompro.ru` → `157.22.231.226`:

```bash
sudo apt install -y certbot python3-certbot-nginx

# Получить сертификат (интерактивно)
sudo certbot --nginx -d dompro.ru -d www.dompro.ru

# Проверка автообновления
sudo certbot renew --dry-run
```

После certbot раскомментируйте SSL-блоки в `deploy/nginx/dompro` и HTTP→HTTPS редирект.

## Создание системного пользователя (один раз)

```bash
sudo useradd -r -m -d /opt/dompro -s /bin/bash dompro
sudo chown -R dompro:dompro /opt/dompro
```
