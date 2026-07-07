"""Перенос данных из источника в целевую PostgreSQL (data-only)."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import asyncpg
from dotenv import load_dotenv

from core.pg_connect import asyncpg_connect_kwargs, migration_database_url

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Порядок важен из-за внешних ключей
TABLES = [
    "users",
    "experts",
    "clients",
    "orders",
    "responses",
    "transactions",
    "contracts",
    "expert_verifications",
]


async def copy_table(
    src: asyncpg.Connection,
    dst: asyncpg.Connection,
    table: str,
) -> int:
    exists_src = await src.fetchval(
        """
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = $1
        )
        """,
        table,
    )
    if not exists_src:
        print(f"SKIP {table}: нет в источнике")
        return 0

    rows = await src.fetch(f"SELECT * FROM {table} ORDER BY 1")
    if not rows:
        print(f"OK {table}: 0 строк")
        return 0

    columns = list(rows[0].keys())
    placeholders = ", ".join(f"${i + 1}" for i in range(len(columns)))
    col_list = ", ".join(columns)
    sql = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"

    count = 0
    for row in rows:
        await dst.execute(sql, *[row[c] for c in columns])
        count += 1

    pk = await dst.fetchval(
        """
        SELECT a.attname
        FROM pg_index i
        JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
        WHERE i.indrelid = $1::regclass AND i.indisprimary
        LIMIT 1
        """,
        table,
    )
    if pk:
        await dst.execute(
            f"""
            SELECT setval(
                pg_get_serial_sequence('{table}', '{pk}'),
                COALESCE((SELECT MAX({pk}) FROM {table}), 1)
            )
            """
        )

    print(f"OK {table}: {count} строк")
    return count


async def main() -> None:
    load_dotenv(PROJECT_ROOT / ".env")

    source_url = migration_database_url(
        os.environ.get("SOURCE_DATABASE_URL", "")
    )
    target_url = os.environ.get("TARGET_DATABASE_URL", "")
    if not source_url or not target_url:
        raise SystemExit("Нужны SOURCE_DATABASE_URL и TARGET_DATABASE_URL")

    src = await asyncpg.connect(**asyncpg_connect_kwargs(source_url))
    dst = await asyncpg.connect(**asyncpg_connect_kwargs(target_url))
    try:
        present = []
        for table in TABLES:
            if await src.fetchval(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                "WHERE table_schema='public' AND table_name=$1)",
                table,
            ):
                present.append(table)

        if present:
            await dst.execute(
                f"TRUNCATE {', '.join(present)} RESTART IDENTITY CASCADE"
            )

        total = 0
        for table in TABLES:
            total += await copy_table(src, dst, table)
        print(f"Готово. Всего строк: {total}")
    finally:
        await src.close()
        await dst.close()


if __name__ == "__main__":
    asyncio.run(main())
