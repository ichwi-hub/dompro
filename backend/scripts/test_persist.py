import asyncio
import os
import re
import ssl
from pathlib import Path

import asyncpg
from dotenv import load_dotenv

from scripts.apply_schema import (
    SCHEMA_PATH,
    migration_database_url,
    parse_database_url,
    split_sql_statements,
)

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")


async def main() -> None:
    url = migration_database_url(os.environ["DATABASE_URL"])
    params = parse_database_url(url)
    print("connect", params)

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    schema_sql = re.sub(r"^BEGIN;\s*", "", schema_sql, flags=re.IGNORECASE)
    schema_sql = re.sub(r"\s*COMMIT;\s*$", "", schema_sql, flags=re.IGNORECASE)

    conn1 = await asyncpg.connect(
        host=str(params["host"]),
        port=int(params["port"]),
        user=str(params["user"]),
        password=str(params["password"]),
        database=str(params["database"]),
        ssl=ctx,
        statement_cache_size=0,
    )
    for statement in split_sql_statements(schema_sql):
        await conn1.execute(statement)

    await conn1.execute("COMMIT")

    tables1 = await conn1.fetch(
        "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY 1"
    )
    print("conn1", [r["tablename"] for r in tables1])

    conn2 = await asyncpg.connect(
        host=str(params["host"]),
        port=int(params["port"]),
        user=str(params["user"]),
        password=str(params["password"]),
        database=str(params["database"]),
        ssl=ctx,
        statement_cache_size=0,
    )
    tables2 = await conn2.fetch(
        "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY 1"
    )
    print("conn2", [r["tablename"] for r in tables2])

    await conn1.close()
    await conn2.close()


if __name__ == "__main__":
    asyncio.run(main())
