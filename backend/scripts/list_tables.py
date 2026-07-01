import asyncio
import os
import re
import ssl
from pathlib import Path
from urllib.parse import urlparse

import asyncpg
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")


def migration_database_url(url: str) -> str:
    if ":6543/" in url:
        return url.replace(":6543/", ":5432/")
    return url


url = migration_database_url(os.environ["DATABASE_URL"])
parsed = urlparse(url)


async def main():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    conn = await asyncpg.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        user=parsed.username,
        password=parsed.password,
        database=parsed.path.lstrip("/"),
        ssl=ctx,
        statement_cache_size=0,
    )
    rows = await conn.fetch(
        "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY 1"
    )
    print([r["tablename"] for r in rows])
    await conn.close()


asyncio.run(main())
