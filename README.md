# DomPro (ДомПро)

Платформа для профессиональных фрилансеров — юристов, бухгалтеров, консультантов. Не доска объявлений, а **рабочая среда**: заказы, клиенты, договоры, кошелёк, Expert Workspace.

## Стек

- **Backend:** FastAPI + PostgreSQL (AdminVPS, Россия)
- **Frontend:** статический HTML/JS/CSS (`frontend/`)
- **Хранилище:** локальная ФС (`data/storage/`)

## Быстрый старт (локально)

```powershell
# 1. API
cd C:\projects\dompro\backend
.\.venv\Scripts\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8000

# 2. Фронтенд (второй терминал)
cd C:\projects\dompro
python -m http.server 5500 --bind 127.0.0.1
```

Откройте: **http://127.0.0.1:5500/frontend/login.html**

## Структура

```
dompro/
├── backend/          # FastAPI API
├── frontend/         # Кабинеты, workspace, заказы
├── database/         # schema.sql + миграции
├── deploy/           # systemd, nginx, deploy.sh
├── data/storage/     # Файлы (верификация, договоры)
└── docs/             # Онбординг, чеклисты
```

## Деплой

См. `deploy/deploy.sh` и `backend/README.md`.

## Документация

- `AUDIT.md` — аудит проекта и дорожная карта
- `docs/onboarding-checklist.md` — онбординг первого эксперта
- `backend/README.md` — API, БД, тесты

## Разработчик

Максимов Игорь Юрьевич
