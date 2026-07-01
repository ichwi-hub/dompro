"""Применение schema.sql к PostgreSQL (Supabase)."""

from __future__ import annotations

import asyncio
import os
import re
import ssl
from pathlib import Path
from urllib.parse import urlparse

import asyncpg
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCHEMA_PATH = PROJECT_ROOT / "database" / "schema.sql"


def migration_database_url(url: str) -> str:
    """Для DDL используем session mode pooler (порт 5432)."""
    if ":6543/" in url:
        return url.replace(":6543/", ":5432/")
    return url


def parse_database_url(url: str) -> dict[str, str | int]:
    parsed = urlparse(url)
    return {
        "user": parsed.username or "postgres",
        "password": parsed.password or "",
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 5432,
        "database": (parsed.path or "/postgres").lstrip("/"),
    }


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

    params = parse_database_url(database_url)
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    schema_sql = re.sub(r"^BEGIN;\s*", "", schema_sql, flags=re.IGNORECASE)
    schema_sql = re.sub(r"\s*COMMIT;\s*$", "", schema_sql, flags=re.IGNORECASE)

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    conn = await asyncpg.connect(
        host=str(params["host"]),
        port=int(params["port"]),
        user=str(params["user"]),
        password=str(params["password"]),
        database=str(params["database"]),
        ssl=ssl_context if "supabase.com" in str(params["host"]) else None,
        statement_cache_size=0,
    )

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
