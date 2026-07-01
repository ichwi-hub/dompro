# DomPro Backend

API маркетплейса экспертов на **FastAPI** + **PostgreSQL** + **SQLAlchemy**.

## Требования

- Python 3.11+
- PostgreSQL 14+
- Применённая схема: `../database/schema.sql`

## Установка

```powershell
cd C:\projects\dompro\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Переменные окружения

Скопируйте `.env.example` в корень проекта (`C:\projects\dompro\.env`).

### Supabase (рекомендуется)

В [Supabase Dashboard](https://supabase.com/dashboard/project/mgsaonfuqqbvpzqctjww/settings/database) возьмите **Connection pooling** → **Transaction mode** (порт `6543`).

Формат URL:

```env
DATABASE_URL=postgresql://postgres.PROJECT_REF:YOUR_PASSWORD@aws-0-REGION.pooler.supabase.com:6543/postgres
```

Для проекта DomPro регион: `eu-west-1`.

Прямое подключение `db.*.supabase.co:5432` на Windows часто не работает (таймаут IPv6). Используйте pooler.

Применить схему БД:

```powershell
cd C:\projects\dompro\backend
.\.venv\Scripts\Activate.ps1
python scripts\apply_schema.py
```

Таблицы также можно проверить в [Database → Schemas](https://supabase.com/dashboard/project/mgsaonfuqqbvpzqctjww/database/schemas).

### Локальный PostgreSQL

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/dompro
```

```powershell
psql -U postgres -d dompro -f ..\database\schema.sql
```

## Запуск сервера

```powershell
cd C:\projects\dompro\backend
.\.venv\Scripts\Activate.ps1
uvicorn main:app --reload
```

## Проверка

| URL | Описание |
|-----|----------|
| http://localhost:8000 | Статус сервиса |
| http://localhost:8000/health | Проверка БД |
| http://localhost:8000/api/v1/test | Тест API v1 |
| http://localhost:8000/docs | Swagger UI |

## Структура

```
backend/
├── main.py              # Точка входа FastAPI
├── requirements.txt
├── core/
│   ├── config.py        # Настройки из .env (pydantic-settings)
│   └── database.py      # Async SQLAlchemy
├── models/              # ORM-модели
└── schemas/             # Pydantic-схемы валидации
```

## Механика оплаты (без эскроу)

1. Эксперт пополняет **внутренний баланс** (`experts.balance`).
2. При отклике списывается **response_fee** (таблица `transactions`).
3. Оплата услуги — **напрямую** между клиентом и экспертом.
4. Платформа генерирует **PDF-договор** (`contracts`).
