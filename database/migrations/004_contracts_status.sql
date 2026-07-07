-- Миграция 004: статус договора, pdf_path, updated_at

DO $$ BEGIN
    CREATE TYPE contract_status AS ENUM ('draft', 'signed', 'cancelled');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Переименование pdf_url → pdf_path (если ещё не переименовано)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'contracts' AND column_name = 'pdf_url'
    ) THEN
        ALTER TABLE contracts RENAME COLUMN pdf_url TO pdf_path;
    END IF;
END $$;

ALTER TABLE contracts
    ADD COLUMN IF NOT EXISTS status contract_status NOT NULL DEFAULT 'draft',
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

COMMENT ON COLUMN contracts.status IS 'Статус договора: draft, signed, cancelled';
COMMENT ON COLUMN contracts.pdf_path IS 'Относительный путь к PDF в LOCAL_STORAGE_PATH';
