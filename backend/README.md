# DomPro Backend

API маркетплейса экспертов на **FastAPI** + **PostgreSQL (AdminVPS)** + **SQLAlchemy**.

## Архитектура

| Компонент | Описание |
|-----------|----------|
| **FastAPI** | REST API (`/api/v1/*`) |
| **PostgreSQL 16** | БД на VPS `157.22.231.226` (SSL, 152-ФЗ) |
| **Локальное хранилище** | Файлы верификации и PDF-договоры в `data/storage/` |
| **Frontend** | Статический `frontend/` (отдельный HTTP-сервер или nginx) |

## Требования

- Python 3.11+
- PostgreSQL 14+ (удалённый AdminVPS или локальный)
- Применённая схема: `../database/schema.sql` + миграции в `../database/migrations/`

## Установка

```powershell
cd C:\projects\dompro\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Переменные окружения

Скопируйте `.env.example` в корень проекта (`C:\projects\dompro\.env`):

```env
DATABASE_URL=postgresql://dompro:PASSWORD@157.22.231.226:5432/dompro?sslmode=require
TEST_DATABASE_URL=postgresql://dompro:PASSWORD@157.22.231.226:5432/dompro_test?sslmode=require
SECRET_KEY=your-secret-key
STORAGE_BACKEND=local
LOCAL_STORAGE_PATH=./data/storage
API_PUBLIC_URL=http://127.0.0.1:8000
```

### AdminVPS PostgreSQL

1. PostgreSQL 16 на Ubuntu 24.04 (`backend/scripts/adminvps/setup_postgres.sh`)
2. SSL (`sslmode=require`), доступ к порту 5432 только с IP разработчика (UFW)
3. Применить схему и миграции:

```powershell
cd C:\projects\dompro\backend
.\.venv\Scripts\python.exe scripts\apply_schema.py
.\.venv\Scripts\python.exe scripts\apply_migrations.py
```

## Локальная разработка

Нужны **два терминала**:

```powershell
# Терминал 1 — API
cd C:\projects\dompro\backend
.\.venv\Scripts\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8000

# Терминал 2 — фронтенд
cd C:\projects\dompro
python -m http.server 5500 --bind 127.0.0.1
```

Точка входа: http://127.0.0.1:5500/frontend/login.html

## Деплой на VPS

Инфраструктурные файлы в `deploy/`:

| Файл | Назначение |
|------|------------|
| `deploy/dompro-api.service` | systemd unit для uvicorn |
| `deploy/nginx/dompro` | nginx: статика + proxy `/api/` |
| `deploy/deploy.sh` | копирование, venv, restart |
| `deploy/UFW.md` | правила файрвола и certbot |

```bash
# На VPS (после клонирования репозитория в /opt/dompro)
sudo bash /opt/dompro/deploy/deploy.sh
```

Certbot (после настройки DNS):

```bash
sudo certbot --nginx -d dompro.ru -d www.dompro.ru
```

## Тесты

Изолированная тестовая БД `dompro_test`:

```powershell
cd C:\projects\dompro\backend
.\.venv\Scripts\python.exe scripts\setup_test_db.py
.\.venv\Scripts\python.exe -m pytest tests/ -v
```

## Проверка API

| URL | Описание |
|-----|----------|
| http://127.0.0.1:8000/health | Проверка БД |
| http://127.0.0.1:8000/docs | Swagger UI |

## Структура

```
backend/
├── main.py
├── api/v1/           # Роутеры (auth, orders, contracts, feed, …)
├── core/             # config, database, storage, security
├── models/           # SQLAlchemy ORM
├── schemas/          # Pydantic
├── services/         # contract_service, storage, fns_api
├── templates/        # HTML-шаблоны договоров
├── scripts/          # миграции, setup_test_db, adminvps
└── tests/            # интеграционные pytest-тесты
```

## Механика оплаты

1. Эксперт пополняет внутренний баланс (`experts.balance`)
2. При отклике списывается `response_fee` (150 ₽)
3. Оплата услуги — напрямую между клиентом и экспертом
4. Платформа генерирует PDF-договор (`contracts`)
