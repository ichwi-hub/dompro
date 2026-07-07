import asyncio
import os
import sys
from pathlib import Path

import asyncpg
from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from core.pg_connect import asyncpg_connect_kwargs, migration_database_url

load_dotenv(BACKEND_ROOT.parent / ".env")


async def main() -> None:
    url = migration_database_url(os.environ["DATABASE_URL"])
    conn = await asyncpg.connect(**asyncpg_connect_kwargs(url))
    rows = await conn.fetch(
        "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY 1"
    )
    print([r["tablename"] for r in rows])
    await conn.close()


asyncio.run(main())
