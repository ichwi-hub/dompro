-- Дедлайн заказа (опционально)
ALTER TABLE orders
    ADD COLUMN IF NOT EXISTS deadline DATE;

COMMENT ON COLUMN orders.deadline IS 'Желаемый срок выполнения заказа';
