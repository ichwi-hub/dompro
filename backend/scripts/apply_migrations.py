"""Применение SQL-миграций к PostgreSQL (Supabase)."""

from __future__ import annotations

import asyncio
import os
import ssl
from pathlib import Path
from urllib.parse import urlparse

import asyncpg
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MIGRATIONS_DIR = PROJECT_ROOT / "database" / "migrations"


async def apply_file(conn: asyncpg.Connection, path: Path) -> None:
    sql = path.read_text(encoding="utf-8")
    await conn.execute(sql)
    await conn.execute("COMMIT")
    print(f"OK: {path.name}")


def migration_database_url(url: str) -> str:
    if ":6543/" in url:
        return url.replace(":6543/", ":5432/")
    return url


async def main() -> None:
    load_dotenv(PROJECT_ROOT / ".env")
    database_url = migration_database_url(os.environ.get("DATABASE_URL", ""))
    if not database_url:
        raise SystemExit("DATABASE_URL не задан")

    parsed = urlparse(database_url)
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    conn = await asyncpg.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        user=parsed.username,
        password=parsed.password,
        database=parsed.path.lstrip("/"),
        ssl=ssl_context if parsed.hostname and "supabase.com" in parsed.hostname else None,
        statement_cache_size=0 if parsed.hostname and "supabase.com" in parsed.hostname else 100,
    )
    try:
        for migration in sorted(MIGRATIONS_DIR.glob("*.sql")):
            try:
                await apply_file(conn, migration)
            except asyncpg.exceptions.DuplicateObjectError as exc:
                print(f"SKIP (exists): {migration.name} — {exc}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
