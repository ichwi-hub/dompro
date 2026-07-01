-- =============================================================================
-- DomPro — схема базы данных PostgreSQL
-- Вертикальный маркетплейс экспертов
--
-- Механика оплаты:
--   • Эксперт пополняет внутренний баланс на платформе (deposit).
--   • При отклике на заказ списывается плата за лид (response_fee).
--   • Оплата услуги заказчик → исполнитель напрямую (вне платформы).
--   • Платформа генерирует PDF-договор между сторонами.
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- Перечисления (ENUM)
-- ---------------------------------------------------------------------------

CREATE TYPE user_role AS ENUM (
  'client',   -- заказчик
  'expert'    -- эксперт / исполнитель
);

COMMENT ON TYPE user_role IS 'Роль пользователя в системе';

CREATE TYPE order_status AS ENUM (
  'open',         -- открыт, принимает отклики
  'in_progress',  -- в работе (отклик принят)
  'completed',    -- завершён
  'cancelled'     -- отменён
);

COMMENT ON TYPE order_status IS 'Статус заказа клиента';

CREATE TYPE response_status AS ENUM (
  'pending',   -- ожидает решения клиента
  'accepted',  -- принят клиентом
  'rejected'   -- отклонён клиентом
);

COMMENT ON TYPE response_status IS 'Статус отклика эксперта на заказ';

CREATE TYPE transaction_type AS ENUM (
  'deposit',       -- пополнение баланса эксперта
  'response_fee'   -- списание за отклик (лид)
);

COMMENT ON TYPE transaction_type IS 'Тип внутренней транзакции эксперта на платформе';

-- ---------------------------------------------------------------------------
-- users — базовые учётные записи
-- ---------------------------------------------------------------------------

CREATE TABLE users (
  id            BIGSERIAL PRIMARY KEY,
  email         VARCHAR(255) NOT NULL UNIQUE,
  phone         VARCHAR(32),
  password_hash VARCHAR(255) NOT NULL,
  role          user_role NOT NULL,
  full_name     VARCHAR(255) NOT NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT users_email_lower_chk CHECK (email = LOWER(email))
);

COMMENT ON TABLE users IS 'Пользователи платформы (заказчики и эксперты)';
COMMENT ON COLUMN users.id IS 'Уникальный идентификатор пользователя';
COMMENT ON COLUMN users.email IS 'Email для входа (хранится в нижнем регистре)';
COMMENT ON COLUMN users.phone IS 'Номер телефона';
COMMENT ON COLUMN users.password_hash IS 'Хэш пароля (bcrypt и т.п.)';
COMMENT ON COLUMN users.role IS 'Роль: client — заказчик, expert — эксперт';
COMMENT ON COLUMN users.full_name IS 'ФИО или отображаемое имя';
COMMENT ON COLUMN users.created_at IS 'Дата и время регистрации';

CREATE INDEX idx_users_role ON users (role);
CREATE INDEX idx_users_created_at ON users (created_at);

-- ---------------------------------------------------------------------------
-- experts — профили экспертов
-- ---------------------------------------------------------------------------

CREATE TABLE experts (
  id               BIGSERIAL PRIMARY KEY,
  user_id          BIGINT NOT NULL UNIQUE REFERENCES users (id) ON DELETE CASCADE,
  category         VARCHAR(128) NOT NULL,
  experience_years INTEGER NOT NULL DEFAULT 0 CHECK (experience_years >= 0),
  description      TEXT,
  rating           NUMERIC(3, 2) NOT NULL DEFAULT 0.00 CHECK (rating >= 0 AND rating <= 5),
  balance          NUMERIC(12, 2) NOT NULL DEFAULT 0.00 CHECK (balance >= 0)
);

COMMENT ON TABLE experts IS 'Профили экспертов с внутренним балансом для оплаты откликов';
COMMENT ON COLUMN experts.id IS 'Уникальный идентификатор профиля эксперта';
COMMENT ON COLUMN experts.user_id IS 'Ссылка на учётную запись пользователя';
COMMENT ON COLUMN experts.category IS 'Основная категория экспертизы (юрист, бухгалтер и т.д.)';
COMMENT ON COLUMN experts.experience_years IS 'Стаж работы в годах';
COMMENT ON COLUMN experts.description IS 'Описание услуг и компетенций';
COMMENT ON COLUMN experts.rating IS 'Средний рейтинг (0.00–5.00)';
COMMENT ON COLUMN experts.balance IS 'Внутренний баланс для списания платы за отклики';

CREATE INDEX idx_experts_category ON experts (category);
CREATE INDEX idx_experts_rating ON experts (rating DESC);
CREATE INDEX idx_experts_balance ON experts (balance);

-- ---------------------------------------------------------------------------
-- clients — профили заказчиков
-- ---------------------------------------------------------------------------

CREATE TABLE clients (
  id           BIGSERIAL PRIMARY KEY,
  user_id      BIGINT NOT NULL UNIQUE REFERENCES users (id) ON DELETE CASCADE,
  company_name VARCHAR(255)
);

COMMENT ON TABLE clients IS 'Профили заказчиков (физ. лица и компании)';
COMMENT ON COLUMN clients.id IS 'Уникальный идентификатор профиля заказчика';
COMMENT ON COLUMN clients.user_id IS 'Ссылка на учётную запись пользователя';
COMMENT ON COLUMN clients.company_name IS 'Название компании (если B2B)';

CREATE INDEX idx_clients_company_name ON clients (company_name);

-- ---------------------------------------------------------------------------
-- orders — заказы клиентов
-- ---------------------------------------------------------------------------

CREATE TABLE orders (
  id          BIGSERIAL PRIMARY KEY,
  client_id   BIGINT NOT NULL REFERENCES clients (id) ON DELETE CASCADE,
  title       VARCHAR(255) NOT NULL,
  description TEXT,
  category    VARCHAR(128) NOT NULL,
  budget      NUMERIC(12, 2) CHECK (budget IS NULL OR budget >= 0),
  status      order_status NOT NULL DEFAULT 'open',
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE orders IS 'Заказы, публикуемые заказчиками для откликов экспертов';
COMMENT ON COLUMN orders.id IS 'Уникальный идентификатор заказа';
COMMENT ON COLUMN orders.client_id IS 'Заказчик, создавший заказ';
COMMENT ON COLUMN orders.title IS 'Краткое название задачи';
COMMENT ON COLUMN orders.description IS 'Подробное описание заказа';
COMMENT ON COLUMN orders.category IS 'Категория услуги';
COMMENT ON COLUMN orders.budget IS 'Ориентировочный бюджет (оплата вне платформы)';
COMMENT ON COLUMN orders.status IS 'Текущий статус заказа';
COMMENT ON COLUMN orders.created_at IS 'Дата и время публикации';

CREATE INDEX idx_orders_client_id ON orders (client_id);
CREATE INDEX idx_orders_status ON orders (status);
CREATE INDEX idx_orders_category ON orders (category);
CREATE INDEX idx_orders_created_at ON orders (created_at DESC);

-- ---------------------------------------------------------------------------
-- responses — отклики экспертов на заказы
-- ---------------------------------------------------------------------------

CREATE TABLE responses (
  id         BIGSERIAL PRIMARY KEY,
  order_id   BIGINT NOT NULL REFERENCES orders (id) ON DELETE CASCADE,
  expert_id  BIGINT NOT NULL REFERENCES experts (id) ON DELETE CASCADE,
  message    TEXT,
  cost       NUMERIC(12, 2) NOT NULL CHECK (cost >= 0),
  status     response_status NOT NULL DEFAULT 'pending',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT uq_responses_order_expert UNIQUE (order_id, expert_id)
);

COMMENT ON TABLE responses IS 'Отклики экспертов; при создании списывается response_fee с баланса';
COMMENT ON COLUMN responses.id IS 'Уникальный идентификатор отклика';
COMMENT ON COLUMN responses.order_id IS 'Заказ, на который откликнулся эксперт';
COMMENT ON COLUMN responses.expert_id IS 'Эксперт, отправивший отклик';
COMMENT ON COLUMN responses.message IS 'Сопроводительное сообщение эксперта';
COMMENT ON COLUMN responses.cost IS 'Предложенная стоимость услуги (оплата напрямую заказчиком)';
COMMENT ON COLUMN responses.status IS 'Статус рассмотрения отклика';
COMMENT ON COLUMN responses.created_at IS 'Дата и время отклика';

CREATE INDEX idx_responses_order_id ON responses (order_id);
CREATE INDEX idx_responses_expert_id ON responses (expert_id);
CREATE INDEX idx_responses_status ON responses (status);
CREATE INDEX idx_responses_created_at ON responses (created_at DESC);

-- ---------------------------------------------------------------------------
-- transactions — внутренние операции с балансом эксперта
-- ---------------------------------------------------------------------------

CREATE TABLE transactions (
  id          BIGSERIAL PRIMARY KEY,
  expert_id   BIGINT NOT NULL REFERENCES experts (id) ON DELETE CASCADE,
  type        transaction_type NOT NULL,
  amount      NUMERIC(12, 2) NOT NULL CHECK (amount > 0),
  description TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE transactions IS 'История пополнений и списаний внутреннего баланса эксперта';
COMMENT ON COLUMN transactions.id IS 'Уникальный идентификатор транзакции';
COMMENT ON COLUMN transactions.expert_id IS 'Эксперт, чей баланс изменился';
COMMENT ON COLUMN transactions.type IS 'deposit — пополнение, response_fee — плата за отклик';
COMMENT ON COLUMN transactions.amount IS 'Сумма операции (всегда положительная)';
COMMENT ON COLUMN transactions.description IS 'Комментарий к операции';
COMMENT ON COLUMN transactions.created_at IS 'Дата и время операции';

CREATE INDEX idx_transactions_expert_id ON transactions (expert_id);
CREATE INDEX idx_transactions_type ON transactions (type);
CREATE INDEX idx_transactions_created_at ON transactions (created_at DESC);

-- ---------------------------------------------------------------------------
-- contracts — PDF-договоры между заказчиком и экспертом
-- ---------------------------------------------------------------------------

CREATE TABLE contracts (
  id         BIGSERIAL PRIMARY KEY,
  order_id   BIGINT NOT NULL REFERENCES orders (id) ON DELETE CASCADE,
  expert_id  BIGINT NOT NULL REFERENCES experts (id) ON DELETE CASCADE,
  client_id  BIGINT NOT NULL REFERENCES clients (id) ON DELETE CASCADE,
  pdf_url    TEXT NOT NULL,
  signed_at  TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE contracts IS 'Автоматически сгенерированные PDF-договоры между сторонами';
COMMENT ON COLUMN contracts.id IS 'Уникальный идентификатор договора';
COMMENT ON COLUMN contracts.order_id IS 'Заказ, по которому заключён договор';
COMMENT ON COLUMN contracts.expert_id IS 'Исполнитель по договору';
COMMENT ON COLUMN contracts.client_id IS 'Заказчик по договору';
COMMENT ON COLUMN contracts.pdf_url IS 'URL или путь к файлу PDF-договора';
COMMENT ON COLUMN contracts.signed_at IS 'Дата подписания (если применимо)';
COMMENT ON COLUMN contracts.created_at IS 'Дата генерации договора';

CREATE INDEX idx_contracts_order_id ON contracts (order_id);
CREATE INDEX idx_contracts_expert_id ON contracts (expert_id);
CREATE INDEX idx_contracts_client_id ON contracts (client_id);
CREATE INDEX idx_contracts_created_at ON contracts (created_at DESC);

COMMIT;
