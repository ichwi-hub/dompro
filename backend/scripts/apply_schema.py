"""Применение schema.sql к PostgreSQL."""

from __future__ import annotations

import asyncio
import os
import re
from pathlib import Path

import asyncpg
from dotenv import load_dotenv

from core.pg_connect import asyncpg_connect_kwargs, migration_database_url

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCHEMA_PATH = PROJECT_ROOT / "database" / "schema.sql"


def split_sql_statements(sql: str) -> list[str]:
    """Разбить SQL-файл на отдельные команды."""
    statements: list[str] = []
    buffer: list[str] = []
    for line in sql.splitlines():
        stripped = line.strip()
        if stripped.startswith("--") or not stripped:
            continue
        buffer.append(line)
        if stripped.endswith(";"):
            statement = "\n".join(buffer).strip().rstrip(";").strip()
            if statement:
                statements.append(statement)
            buffer = []
    return statements


async def apply_schema() -> None:
    load_dotenv(PROJECT_ROOT / ".env")

    database_url = migration_database_url(os.environ.get("DATABASE_URL", ""))
    if not database_url:
        raise SystemExit("DATABASE_URL не задан в .env")

    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    schema_sql = re.sub(r"^BEGIN;\s*", "", schema_sql, flags=re.IGNORECASE)
    schema_sql = re.sub(r"\s*COMMIT;\s*$", "", schema_sql, flags=re.IGNORECASE)

    conn = await asyncpg.connect(**asyncpg_connect_kwargs(database_url))

    try:
        for statement in split_sql_statements(schema_sql):
            try:
                await conn.execute(statement)
            except asyncpg.exceptions.DuplicateObjectError as exc:
                print("SKIP:", str(exc)[:100])
        await conn.execute("COMMIT")
        tables = await conn.fetch(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
        )
        print("Схема применена. Таблицы:", ", ".join(row["tablename"] for row in tables))
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(apply_schema())
