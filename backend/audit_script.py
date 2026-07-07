"""Автоматический аудит проекта DomPro.

Сканирует файлы, модели, схемы, эндпоинты и (опционально) БД.
Запуск: cd backend && python audit_script.py
"""

from __future__ import annotations

import ast
import os
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_ROOT = PROJECT_ROOT / "backend"

ROUTE_PATTERN = re.compile(
    r"@(?:app|router)\.(get|post|put|patch|delete)\(\s*[\"']([^\"']+)[\"']",
    re.MULTILINE,
)
MODEL_PATTERN = re.compile(r"^class\s+(\w+)\s*\(\s*Base\s*\)", re.MULTILINE)
SCHEMA_PATTERN = re.compile(r"^class\s+(\w+)\s*\(\s*BaseModel\s*\)", re.MULTILINE)


def list_files(directory: Path, extensions: tuple[str, ...] | None = None) -> list[str]:
    if not directory.exists():
        return []
    skip_dirs = {".venv", "__pycache__", ".pytest_cache", "node_modules"}
    files: list[str] = []
    for path in sorted(directory.rglob("*")):
        if any(part in skip_dirs for part in path.parts):
            continue
        if path.is_file() and path.name != "__pycache__":
            if extensions and path.suffix not in extensions:
                continue
            files.append(str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"))
    return files


def scan_routes() -> list[dict[str, str]]:
    routes: list[dict[str, str]] = []
    scan_paths = [BACKEND_ROOT / "main.py", *sorted((BACKEND_ROOT / "api").rglob("*.py"))]
    for py_file in scan_paths:
        if not py_file.exists():
            continue
        content = py_file.read_text(encoding="utf-8")
        router_prefix = ""
        prefix_match = re.search(
            r'APIRouter\(\s*prefix\s*=\s*["\']([^"\']+)["\']',
            content,
        )
        if prefix_match:
            router_prefix = prefix_match.group(1)

        for method, path in ROUTE_PATTERN.findall(content):
            full_path = path if path.startswith("/api") else f"{router_prefix}{path}"
            routes.append(
                {
                    "method": method.upper(),
                    "path": full_path,
                    "file": str(py_file.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                }
            )
    return routes


def scan_classes(pattern: re.Pattern[str], directory: Path) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for py_file in sorted(directory.rglob("*.py")):
        if py_file.name == "__init__.py":
            continue
        content = py_file.read_text(encoding="utf-8")
        for name in pattern.findall(content):
            items.append(
                {
                    "name": name,
                    "file": str(py_file.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                }
            )
    return items


async def check_database() -> dict[str, object]:
    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env")
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        return {"connected": False, "error": "DATABASE_URL не задан"}

    try:
        import asyncpg

        sys.path.insert(0, str(BACKEND_ROOT))
        from core.pg_connect import asyncpg_connect_kwargs, migration_database_url

        conn = await asyncpg.connect(
            **asyncpg_connect_kwargs(migration_database_url(database_url))
        )
        try:
            tables = await conn.fetch(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                ORDER BY table_name
                """
            )
            table_names = [row["table_name"] for row in tables]
            counts: dict[str, int | str] = {}
            for table in ("users", "experts", "orders", "expert_verifications"):
                if table in table_names:
                    counts[table] = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                else:
                    counts[table] = "таблица отсутствует"
            return {
                "connected": True,
                "host": migration_database_url(database_url).split("@")[-1].split("/")[0],
                "tables": table_names,
                "counts": counts,
            }
        finally:
            await conn.close()
    except Exception as exc:
        return {"connected": False, "error": str(exc)}


def check_env() -> dict[str, bool]:
    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env")
    keys = [
        "DATABASE_URL",
        "SECRET_KEY",
        "STORAGE_BACKEND",
        "LOCAL_STORAGE_PATH",
        "API_PUBLIC_URL",
    ]
    return {key: bool(os.environ.get(key)) for key in keys}


def print_section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(title)
    print("=" * 60)


def main() -> None:
    print_section("DomPro Audit Script")
    print(f"Корень проекта: {PROJECT_ROOT}")

    print_section("Backend files")
    for path in list_files(BACKEND_ROOT, (".py", ".txt", ".ini", ".md")):
        print(f"  {path}")

    print_section("Models (class ... Base)")
    for item in scan_classes(MODEL_PATTERN, BACKEND_ROOT / "models"):
        print(f"  {item['name']:25} — {item['file']}")

    print_section("Schemas (class ... BaseModel)")
    for item in scan_classes(SCHEMA_PATTERN, BACKEND_ROOT / "schemas"):
        print(f"  {item['name']:25} — {item['file']}")

    print_section("API endpoints")
    for route in scan_routes():
        print(f"  {route['method']:6} {route['path']:45} — {route['file']}")

    print_section("Services")
    for path in list_files(BACKEND_ROOT / "services", (".py",)):
        print(f"  {path}")

    print_section("Database migrations")
    for path in list_files(PROJECT_ROOT / "database", (".sql",)):
        print(f"  {path}")

    print_section("Frontend")
    frontend_files = [
        p
        for p in [
            PROJECT_ROOT / "index.html",
            PROJECT_ROOT / "css" / "style.css",
            PROJECT_ROOT / "js" / "app.js",
            PROJECT_ROOT / "assets" / "logo.png",
        ]
        if p.exists()
    ]
    if (PROJECT_ROOT / "frontend").exists():
        print("  Папка frontend/ найдена")
    else:
        print("  Папка frontend/ — НЕТ (статический лендинг в корне)")
    for path in frontend_files:
        print(f"  {path.relative_to(PROJECT_ROOT)}")

    print_section("Environment variables")
    env_status = check_env()
    for key, present in env_status.items():
        status = "OK" if present else "ОТСУТСТВУЕТ"
        print(f"  {key:30} [{status}]")

    print_section("Database check")
    import asyncio

    db_info = asyncio.run(check_database())
    if db_info.get("connected"):
        print(f"  Подключение: OK ({db_info.get('host')})")
        print(f"  Таблицы: {', '.join(db_info.get('tables', []))}")
        for table, count in db_info.get("counts", {}).items():
            print(f"  COUNT {table}: {count}")
    else:
        print(f"  Подключение: НЕТ — {db_info.get('error')}")


if __name__ == "__main__":
    main()
