import asyncio

from core.pg_connect import asyncpg_connect_kwargs
import asyncpg

URL = "postgresql://dompro:EbZl8piYP0jpSkl2mHuuNNVV@157.22.231.226:5432/dompro?sslmode=require"


async def main() -> None:
    conn = await asyncpg.connect(**asyncpg_connect_kwargs(URL))
    for table in [
        "users",
        "experts",
        "clients",
        "orders",
        "responses",
        "transactions",
        "expert_verifications",
    ]:
        count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
        print(f"{table}: {count}")

    enums = await conn.fetch(
        """
        SELECT t.typname, array_agg(e.enumlabel ORDER BY e.enumsortorder) AS labels
        FROM pg_type t
        JOIN pg_enum e ON t.oid = e.enumtypid
        WHERE t.typname IN (
            'user_role', 'order_status', 'response_status', 'verification_status'
        )
        GROUP BY t.typname
        ORDER BY t.typname
        """
    )
    for row in enums:
        print(f"enum {row['typname']}: {row['labels']}")

    indexes = await conn.fetchval(
        "SELECT COUNT(*) FROM pg_indexes WHERE schemaname = 'public'"
    )
    print(f"indexes: {indexes}")
    await conn.close()


asyncio.run(main())
