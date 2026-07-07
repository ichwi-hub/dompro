"""Применение SQL-миграций к PostgreSQL."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import asyncpg
from dotenv import load_dotenv

from core.pg_connect import asyncpg_connect_kwargs, migration_database_url

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MIGRATIONS_DIR = PROJECT_ROOT / "database" / "migrations"


async def apply_file(conn: asyncpg.Connection, path: Path) -> None:
    sql = path.read_text(encoding="utf-8")
    await conn.execute(sql)
    await conn.execute("COMMIT")
    print(f"OK: {path.name}")


async def main() -> None:
    load_dotenv(PROJECT_ROOT / ".env")
    database_url = migration_database_url(os.environ.get("DATABASE_URL", ""))
    if not database_url:
        raise SystemExit("DATABASE_URL не задан")

    conn = await asyncpg.connect(**asyncpg_connect_kwargs(database_url))
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
