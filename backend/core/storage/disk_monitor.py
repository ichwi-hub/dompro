"""Проверка свободного места на диске хранилища."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


def disk_usage_report(path: Path) -> dict[str, float]:
    usage = shutil.disk_usage(path)
    free_gb = usage.free / (1024**3)
    total_gb = usage.total / (1024**3)
    used_pct = (usage.used / usage.total) * 100 if usage.total else 0.0
    return {
        "path": str(path),
        "free_gb": round(free_gb, 2),
        "total_gb": round(total_gb, 2),
        "used_percent": round(used_pct, 1),
    }


def warn_if_low_disk(path: Path, min_free_gb: float = 2.0) -> dict[str, float]:
    report = disk_usage_report(path)
    if report["free_gb"] < min_free_gb:
        logger.warning(
            "Мало свободного места на диске хранилища: %.2f GB (порог %.2f GB) — %s",
            report["free_gb"],
            min_free_gb,
            report["path"],
        )
    return report
