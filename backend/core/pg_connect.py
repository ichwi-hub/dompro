"""Provider-agnostic PostgreSQL connection helpers for runtime and scripts."""

from __future__ import annotations

import ssl
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse


def migration_database_url(url: str) -> str:
    """Нормализация URL для DDL/миграций (pooler → прямой порт при необходимости)."""
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


def _ssl_mode(url: str) -> str | None:
    query = parse_qs(urlparse(url).query)
    values = query.get("sslmode") or query.get("ssl")
    if not values:
        return None
    return values[0].lower()


def _is_local_host(host: str) -> bool:
    return host in {"localhost", "127.0.0.1", "::1"}


def build_ssl_context_for_url(url: str) -> ssl.SSLContext | None:
    """SSL-контекст для asyncpg/psycopg2 или None для локального подключения."""
    host = urlparse(url).hostname or ""
    mode = _ssl_mode(url)

    if _is_local_host(host) and mode in (None, "disable", "allow", "prefer"):
        return None

    if mode == "disable":
        return None

    if mode in {"require", "verify-ca", "verify-full"} or not _is_local_host(host):
        ctx = ssl.create_default_context()
        if mode in (None, "require") or mode == "require":
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        return ctx

    if mode in {"verify-ca", "verify-full"}:
        return ssl.create_default_context()

    # Удалённый хост без явного sslmode — шифруем по умолчанию (dev/prod VPS).
    if not _is_local_host(host):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx

    return None


def asyncpg_connect_kwargs(url: str) -> dict:
    """Параметры для asyncpg.connect / create_async_engine(connect_args=...)."""
    params = parse_database_url(url)
    host = str(params["host"])
    kwargs: dict = {
        "host": host,
        "port": int(params["port"]),
        "user": str(params["user"]),
        "password": str(params["password"]),
        "database": str(params["database"]),
    }

    ssl_context = build_ssl_context_for_url(url)
    if ssl_context is not None:
        kwargs["ssl"] = ssl_context

    return kwargs


def sqlalchemy_async_url(url: str) -> str:
    """URL для SQLAlchemy без sslmode в query (SSL передаётся через connect_args)."""
    parsed = urlparse(url)
    query = parse_qs(parsed.query, keep_blank_values=True)
    for key in list(query.keys()):
        if key.lower() in {"sslmode", "ssl"}:
            del query[key]
    clean = parsed._replace(query=urlencode(query, doseq=True))
    result = urlunparse(clean)
    if result.startswith("postgresql://"):
        return result.replace("postgresql://", "postgresql+asyncpg://", 1)
    if "+psycopg2" in result:
        return result.replace("+psycopg2", "+asyncpg", 1)
    return result


def sqlalchemy_connect_args(url: str) -> dict:
    """Параметры connect_args для SQLAlchemy async engine."""
    ssl_context = build_ssl_context_for_url(url)
    if ssl_context is None:
        return {}

    args: dict = {"ssl": ssl_context}
    return args
