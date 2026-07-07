"""Создание и сброс тестовой БД dompro_test."""

from __future__ import annotations

import asyncio
import os
import re
import sys
from pathlib import Path

import asyncpg
from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))

from core.pg_connect import asyncpg_connect_kwargs, migration_database_url

SCHEMA_PATH = PROJECT_ROOT / "database" / "schema.sql"
MIGRATIONS_DIR = PROJECT_ROOT / "database" / "migrations"


def split_sql_statements(sql: str) -> list[str]:
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


def _test_url(database_url: str) -> str:
    test = os.getenv("TEST_DATABASE_URL", "")
    if test:
        return migration_database_url(test)
    base = migration_database_url(database_url)
    if "/dompro_test" in base:
        return base
    return base.replace("/dompro", "/dompro_test", 1)


async def ensure_test_database(database_url: str, test_db_name: str = "dompro_test") -> None:
    """Создать test-БД, если у пользователя есть CREATEDB."""
    conn = await asyncpg.connect(**asyncpg_connect_kwargs(database_url))
    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            test_db_name,
        )
        if exists:
            print(f"БД уже существует: {test_db_name}")
            return
    finally:
        await conn.close()

    conn = await asyncpg.connect(**asyncpg_connect_kwargs(database_url))
    try:
        await conn.execute(f'CREATE DATABASE "{test_db_name}"')
        print(f"Создана БД: {test_db_name}")
    except Exception as exc:
        raise SystemExit(
            f"Не удалось создать {test_db_name}. На сервере выполните:\n"
            f'  sudo -u postgres psql -c "CREATE DATABASE {test_db_name} OWNER dompro;"'
        ) from exc
    finally:
        await conn.close()


async def reset_schema(test_url: str) -> None:
    conn = await asyncpg.connect(**asyncpg_connect_kwargs(test_url))
    try:
        await conn.execute("DROP SCHEMA IF EXISTS public CASCADE")
        await conn.execute("CREATE SCHEMA public")
        await conn.execute("GRANT ALL ON SCHEMA public TO public")

        schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
        schema_sql = re.sub(r"^BEGIN;\s*", "", schema_sql, flags=re.IGNORECASE)
        schema_sql = re.sub(r"\s*COMMIT;\s*$", "", schema_sql, flags=re.IGNORECASE)

        for statement in split_sql_statements(schema_sql):
            try:
                await conn.execute(statement)
            except asyncpg.exceptions.DuplicateObjectError:
                pass

        for migration in sorted(MIGRATIONS_DIR.glob("*.sql")):
            try:
                await conn.execute(migration.read_text(encoding="utf-8"))
            except asyncpg.exceptions.DuplicateObjectError:
                pass

        print("Схема тестовой БД применена")
    finally:
        await conn.close()


async def main() -> None:
    load_dotenv(PROJECT_ROOT / ".env")
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        raise SystemExit("DATABASE_URL не задан")

    base = migration_database_url(database_url)
    test = _test_url(database_url)
    await ensure_test_database(base)
    await reset_schema(test)
    print("TEST_DATABASE_URL:", test)


if __name__ == "__main__":
    asyncio.run(main())
