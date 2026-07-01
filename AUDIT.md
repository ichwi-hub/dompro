# Аудит проекта DomPro

**Дата аудита:** 1 июля 2026  
**Версия API:** 0.1.0  
**Метод:** автоматический скрипт `backend/audit_script.py` + ручная проверка кода, БД и Swagger

---

## Резюме

| Категория | Статус |
|-----------|--------|
| **Что работает** | Онбординг эксперта (регистрация → профиль → верификация → админ-модерация), JWT, подключение к Supabase PostgreSQL, 8 таблиц в БД |
| **Что не работает / отсутствует** | Заказы, отклики, кошелёк (API), клиенты, фронт↔API, чат, PDF-договоры, уведомления, рейтинги |
| **Инфраструктура** | `.env` настроен, миграции применены, тестовые пользователи в БД (3 users, 2 experts) |
| **Git** | В репозитории только лендинг (2 коммита); весь backend — незакоммиченные локальные файлы |

### Что делать дальше (рекомендация)

1. Закоммитить backend в git
2. Подключить фронтенд к API (регистрация / вход / профиль / верификация)
3. Реализовать MVP маркетплейса: заказы → отклики → списание `response_fee`
4. Создать bucket `verifications` в Supabase Storage (если ещё не создан)
5. Добавить тестового клиента и верифицированного эксперта в `test_data.py`

---

## 1. Структура проекта

### Backend (Python/FastAPI)

- [x] **Файлы в `backend/`** (45 файлов проекта, без `.venv`):

```
backend/
├── main.py                    # Точка входа FastAPI
├── requirements.txt
├── pytest.ini
├── README.md
├── audit_script.py            # Скрипт аудита (создан при этом аудите)
├── test_data.py               # Создание тестовых пользователей
├── api/
│   ├── __init__.py
│   └── v1/
│       ├── __init__.py
│       ├── auth.py            # Регистрация, логин, /me
│       ├── expert_profile.py  # Профиль эксперта
│       ├── verification.py    # Верификация (документы)
│       └── admin.py           # Модерация верификаций
├── core/
│   ├── config.py              # Настройки из .env
│   ├── database.py            # Async SQLAlchemy
│   ├── dependencies.py        # JWT-зависимости, роли
│   ├── security.py            # bcrypt + JWT
│   └── supabase_client.py     # Клиент Supabase Storage
├── models/                    # 9 ORM-моделей (см. ниже)
├── schemas/                   # 21 Pydantic-схема (см. ниже)
├── services/
│   ├── fns_api.py             # Проверка ИНН (заглушка)
│   └── storage.py             # Загрузка файлов в Supabase
├── scripts/
│   ├── apply_schema.py
│   ├── apply_migrations.py
│   ├── list_tables.py
│   └── test_persist.py
└── tests/
    └── test_auth.py           # 1 тест (register + login + me)
```

- [x] **Модели (`models/`)** — 8 таблиц + 1 алиас:

| Модель | Файл | Таблица в БД | API реализован |
|--------|------|--------------|----------------|
| `User` | `user.py` | `users` | Да (auth) |
| `Expert` | `expert.py` | `experts` | Да (profile) |
| `ExpertVerification` | `verification.py` | `expert_verifications` | Да (verification, admin) |
| `Client` | `client.py` | `clients` | **НЕТ** |
| `Order` | `order.py` | `orders` | **НЕТ** |
| `Response` | `response.py` | `responses` | **НЕТ** |
| `Transaction` | `transaction.py` | `transactions` | **НЕТ** |
| `Contract` | `contract.py` | `contracts` | **НЕТ** |
| `Wallet` | `wallet.py` | (алиас `Expert`) | **НЕТ** |

- [x] **Схемы (`schemas/`)** — 21 класс Pydantic:

| Схема | Файл | Используется в API |
|-------|------|-------------------|
| `RegisterRequest`, `LoginRequest`, `TokenResponse`, `UserResponse`, `LoginResponse` | `user.py` | Да |
| `ExpertProfileUpdate`, `ExpertProfileResponse` | `expert.py` | Да |
| `VerificationStatusResponse`, `VerificationRejectRequest`, `ExpertVerificationResponse` | `verification.py` | Да |
| `ClientCreate`, `ClientResponse` | `client.py` | **НЕТ** |
| `OrderCreate`, `OrderResponse` | `order.py` | **НЕТ** |
| `ResponseCreate`, `ResponseResponse` | `response.py` | **НЕТ** |
| `TransactionCreate`, `TransactionResponse` | `transaction.py` | **НЕТ** |
| `ContractCreate`, `ContractResponse` | `contract.py` | **НЕТ** |
| `WalletResponse` | `wallet.py` | **НЕТ** |

- [x] **API эндпоинты (`api/v1/` + `main.py`)** — 13 эндпоинтов (проверено через Swagger `/openapi.json`):

| Метод | Путь | Описание | Файл |
|-------|------|----------|------|
| GET | `/` | Статус сервиса | `main.py` |
| GET | `/health` | Проверка БД | `main.py` |
| GET | `/api/v1/test` | Тест API | `main.py` |
| POST | `/api/v1/auth/register` | Регистрация эксперта | `auth.py` |
| POST | `/api/v1/auth/login` | Вход | `auth.py` |
| GET | `/api/v1/auth/me` | Текущий пользователь | `auth.py` |
| GET | `/api/v1/expert/profile` | Профиль эксперта | `expert_profile.py` |
| PUT | `/api/v1/expert/profile` | Обновление профиля | `expert_profile.py` |
| POST | `/api/v1/expert/verification/submit` | Подача документов | `verification.py` |
| GET | `/api/v1/expert/verification/status` | Статус верификации | `verification.py` |
| GET | `/api/v1/admin/verifications` | Список заявок (admin) | `admin.py` |
| PUT | `/api/v1/admin/verifications/{id}/approve` | Одобрить (admin) | `admin.py` |
| PUT | `/api/v1/admin/verifications/{id}/reject` | Отклонить (admin) | `admin.py` |

- [x] **Сервисы (`services/`)**:

| Файл | Назначение | Статус |
|------|------------|--------|
| `fns_api.py` | Проверка ИНН + уведомление админа | Заглушка (контрольная сумма, `print`) |
| `storage.py` | Загрузка файлов верификации | Реализовано (Supabase или `local://`) |

### Database

- [x] **Файлы миграций `database/`**:

| Файл | Описание |
|------|----------|
| `schema.sql` | Базовая схема (8 таблиц, ENUM-типы) |
| `migrations/002_auth_verification.sql` | Верификация, профили, `expert_verifications` |

- [x] **Таблицы в Supabase** (проверено `audit_script.py` + `list_tables.py`):

```
clients, contracts, expert_verifications, experts, orders, responses, transactions, users
```

| Таблица | Записей |
|---------|---------|
| `users` | 3 |
| `experts` | 2 |
| `orders` | 0 |
| `expert_verifications` | 0 |
| `responses` | 0 |
| `transactions` | 0 |
| `contracts` | 0 |
| `clients` | 0 |

### Frontend

- [x] **Папка `frontend/`** — **НЕТ**
- [x] **Статический лендинг в корне проекта**:

| Файл | Назначение |
|------|------------|
| `index.html` | Лендинг (Hero, категории, блоки) |
| `css/style.css` | Стили |
| `js/app.js` | Мобильное меню, демо-поиск (`alert`) |
| `assets/logo.png` | Логотип |

Фронтенд **не подключён к API**. Кнопки «Войти» и «Стать экспертом» — заглушки (`href="#"`).

---

## 2. Реализованный функционал

### Аутентификация

- [x] Регистрация пользователя — `POST /api/v1/auth/register` (только роль `expert`)
- [x] Вход (логин) — `POST /api/v1/auth/login` (email или телефон)
- [x] JWT токены — `create_access_token` / `decode_access_token` (HS256, bcrypt)
- [x] Защита роутов — FastAPI Depends (`get_current_user`, `get_current_expert`, `get_current_admin`, `get_verified_expert`)
- [ ] Middleware — **НЕТ отдельного middleware**; защита через dependency injection
- [ ] Регистрация клиента — **НЕ РЕАЛИЗОВАНО**

### Профили

- [x] Профиль эксперта (создание, редактирование) — `GET/PUT /api/v1/expert/profile`
- [x] Верификация эксперта (загрузка документов) — `POST /api/v1/expert/verification/submit`
- [x] Статус верификации — `GET /api/v1/expert/verification/status`
- [x] Админ-панель (одобрение/отклонение) — `GET/PUT /api/v1/admin/verifications/*`
- [ ] Профиль клиента — **НЕ РЕАЛИЗОВАНО** (модель и схема есть)
- [ ] Каталог экспертов — **НЕ РЕАЛИЗОВАНО**

### Заказы и отклики

- [ ] Создание заказа (клиент) — **НЕ РЕАЛИЗОВАНО**
- [ ] Лента заказов (просмотр) — **НЕ РЕАЛИЗОВАНО**
- [ ] Отклик на заказ (эксперт) — **НЕ РЕАЛИЗОВАНО** (`get_verified_expert` готов, но роутера нет)
- [ ] Принятие/отклонение отклика — **НЕ РЕАЛИЗОВАНО**

### Кошелёк и платежи

- [ ] Внутренний баланс эксперта — **поле `experts.balance` в БД есть, API НЕТ**
- [ ] Пополнение баланса — **НЕ РЕАЛИЗОВАНО**
- [ ] История транзакций — **НЕ РЕАЛИЗОВАНО** (таблица `transactions` есть)
- [ ] Списание средств за отклик — **НЕ РЕАЛИЗОВАНО** (задумано в `schema.sql`, кода нет)

### Дополнительный функционал

- [ ] Чат между клиентом и экспертом — **НЕ РЕАЛИЗОВАНО**
- [ ] Генератор договоров (PDF) — **НЕ РЕАЛИЗОВАНО** (таблица `contracts` есть)
- [ ] Уведомления (email/SMS) — **НЕ РЕАЛИЗОВАНО** (заглушка `print` в `fns_api.py`)
- [ ] Рейтинги и отзывы — **НЕ РЕАЛИЗОВАНО** (поле `experts.rating` есть, логики нет)

---

## 3. Тестовые данные

### Тестовые аккаунты

Скрипт `backend/test_data.py` создаёт:

| Аккаунт | Email | Пароль | Роль | Верификация | В БД |
|---------|-------|--------|------|-------------|------|
| Администратор | `admin@dompro.ru` | `Admin12345` | `admin` | `verified` | Да (1 из 3 users) |
| Эксперт (пустой профиль) | `expert1@dompro.ru` | `Expert12345` | `expert` | `unverified` | Да |
| Эксперт (профиль заполнен) | `expert2@dompro.ru` | `Expert12345` | `expert` | `unverified` | Да |
| Верифицированный эксперт | — | — | — | — | **НЕТ** |
| Клиент | — | — | — | — | **НЕТ** |

### Тестовые данные в БД

- [ ] Заказы — **0 записей**
- [ ] Отклики — **0 записей**
- [ ] Транзакции — **0 записей**
- [ ] Заявки на верификацию — **0 записей**

### Тесты

- [x] `tests/test_auth.py` — 1 тест (register + login + me), **проходит** при `PYTHONPATH=.`

---

## 4. Инфраструктура

### База данных

- [x] Supabase подключен — `DATABASE_URL` → `aws-0-eu-west-1.pooler.supabase.com`
- [x] Таблицы созданы — 8 таблиц в `public`
- [x] Миграции применены — `002_auth_verification.sql` выполнена пользователем в Supabase SQL Editor

### Хранилище файлов

- [x] Переменные Supabase в `.env` — `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_STORAGE_BUCKET` заданы
- [ ] Bucket `verifications` — **не проверялся автоматически**; при отсутствии bucket загрузка упадёт (есть fallback `local://` без Supabase-клиента)

### Переменные окружения

- [x] `.env` файл — **существует** в корне проекта
- [x] Все необходимые переменные:

| Переменная | Статус |
|------------|--------|
| `DATABASE_URL` | OK |
| `SECRET_KEY` | OK |
| `SUPABASE_URL` | OK |
| `SUPABASE_KEY` | OK |
| `SUPABASE_STORAGE_BUCKET` | OK |

### Сервер

- [x] FastAPI запускается — `uvicorn main:app --reload`
- [x] Swagger UI — http://127.0.0.1:8000/docs (13 эндпоинтов)
- [x] Health check — `GET /health` → `database: connected`

---

## 5. Что НЕ реализовано (список задач)

### Критично для MVP

- [ ] API заказов (создание клиентом, лента для экспертов)
- [ ] API откликов (создание, принятие/отклонение, списание `response_fee`)
- [ ] Регистрация и профиль клиента
- [ ] Подключение фронтенда к API (формы auth, профиль, верификация)
- [ ] Верифицированный тестовый эксперт для проверки откликов
- [ ] Bucket Supabase Storage `verifications`
- [ ] Закоммитить backend в git

### Важно, но не срочно

- [ ] Реальная проверка ИНН через DaData / API ФНС (сейчас заглушка)
- [ ] Email/Telegram уведомления админу о новых заявках
- [ ] Пополнение баланса (хотя бы заглушка deposit)
- [ ] Каталог экспертов (публичный список verified)
- [ ] Тесты для verification, profile, admin
- [ ] `pytest.ini` / conftest: исправить `PYTHONPATH` для тестов

### В будущем

- [ ] Генерация PDF-договоров
- [ ] Чат клиент ↔ эксперт
- [ ] Рейтинги и отзывы
- [ ] Платёжная интеграция (реальное пополнение баланса)
- [ ] React/Vue SPA вместо статического лендинга
- [ ] CI/CD, Docker, деплой

---

## Приложение: вывод `audit_script.py`

```
Models: Client, Contract, Expert, Order, Response, Transaction, User, ExpertVerification
Schemas: 21 класс (см. раздел 1)
API: 13 эндпоинтов (см. раздел 1)
DB: 8 таблиц, users=3, experts=2, orders=0, expert_verifications=0
.env: все 5 переменных OK
```

Запуск повторного аудита:

```powershell
cd C:\projects\dompro\backend
.\.venv\Scripts\Activate.ps1
python audit_script.py
```
