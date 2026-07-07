-- Образование эксперта в профиле

ALTER TABLE experts
    ADD COLUMN IF NOT EXISTS education TEXT;

COMMENT ON COLUMN experts.education IS 'Образование (ВУЗ, курсы, сертификаты)';
