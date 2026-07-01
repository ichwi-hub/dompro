-- Миграция: регистрация, профили экспертов, верификация
-- Применять после schema.sql

-- Новые ENUM-типы
DO $$ BEGIN
    CREATE TYPE verification_status AS ENUM (
        'unverified',
        'verification_pending',
        'verified',
        'rejected'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- user_role: добавить admin или создать тип заново
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user_role') THEN
        CREATE TYPE user_role AS ENUM ('client', 'expert', 'admin');
    ELSE
        ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'admin';
    END IF;
END $$;

DO $$ BEGIN
    CREATE TYPE expert_verification_status AS ENUM (
        'pending',
        'under_review',
        'approved',
        'rejected'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- users: верификация и timestamps
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS verification_status verification_status NOT NULL DEFAULT 'unverified',
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

ALTER TABLE users ALTER COLUMN full_name DROP NOT NULL;

UPDATE users SET phone = '+7999999' || LPAD(id::text, 4, '0') WHERE phone IS NULL;
ALTER TABLE users ALTER COLUMN phone SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_phone_unique ON users (phone);

COMMENT ON COLUMN users.verification_status IS 'Статус верификации эксперта';

-- experts: профиль и верификация
ALTER TABLE experts
    ADD COLUMN IF NOT EXISTS full_name VARCHAR(255),
    ADD COLUMN IF NOT EXISTS photo_url TEXT,
    ADD COLUMN IF NOT EXISTS specialization VARCHAR(255),
    ADD COLUMN IF NOT EXISTS inn VARCHAR(12),
    ADD COLUMN IF NOT EXISTS diploma_url TEXT,
    ADD COLUMN IF NOT EXISTS self_employment_url TEXT,
    ADD COLUMN IF NOT EXISTS bar_association_url TEXT,
    ADD COLUMN IF NOT EXISTS verified_by BIGINT REFERENCES users (id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS verified_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS rejection_reason TEXT,
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

ALTER TABLE experts ALTER COLUMN category DROP NOT NULL;
ALTER TABLE experts ALTER COLUMN category SET DEFAULT '';

COMMENT ON COLUMN experts.specialization IS 'Специализация эксперта';
COMMENT ON COLUMN experts.inn IS 'ИНН для верификации';

-- expert_verifications: заявки на верификацию
CREATE TABLE IF NOT EXISTS expert_verifications (
    id                    BIGSERIAL PRIMARY KEY,
    expert_id             BIGINT NOT NULL REFERENCES experts (id) ON DELETE CASCADE,
    inn                   VARCHAR(12) NOT NULL,
    diploma_url           TEXT NOT NULL,
    self_employment_url   TEXT NOT NULL,
    bar_association_url   TEXT,
    status                expert_verification_status NOT NULL DEFAULT 'pending',
    reviewed_by           BIGINT REFERENCES users (id) ON DELETE SET NULL,
    reviewed_at           TIMESTAMPTZ,
    rejection_reason      TEXT,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE expert_verifications IS 'Заявки экспертов на верификацию квалификации';

CREATE INDEX IF NOT EXISTS idx_expert_verifications_expert_id ON expert_verifications (expert_id);
CREATE INDEX IF NOT EXISTS idx_expert_verifications_status ON expert_verifications (status);
CREATE INDEX IF NOT EXISTS idx_expert_verifications_created_at ON expert_verifications (created_at DESC);
