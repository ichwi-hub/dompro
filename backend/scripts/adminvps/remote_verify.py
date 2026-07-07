"""Проверка настройки PostgreSQL на AdminVPS (одноразовый скрипт)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import paramiko

HOST = "157.22.231.226"
OUT = Path(__file__).with_name("step2_verify.txt")


def main() -> int:
    password = os.environ.get("ADMINVPS_ROOT_PASSWORD")
    if not password:
        print("ADMINVPS_ROOT_PASSWORD not set", file=sys.stderr)
        return 1

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username="root", password=password, timeout=30)

    cmds = [
        "systemctl is-active postgresql",
        "sudo -u postgres psql -tAc 'SHOW shared_buffers'",
        "sudo -u postgres psql -tAc 'SHOW max_connections'",
        "sudo -u postgres psql -tAc 'SHOW work_mem'",
        "sudo -u postgres psql -tAc 'SHOW ssl'",
        "ufw status numbered",
        "cat /etc/postgresql/16/main/conf.d/dompro-low-memory.conf",
        "tail -8 /etc/postgresql/16/main/pg_hba.conf",
        "grep -E '^Password:|^DATABASE_URL=' /root/setup_postgres.log 2>/dev/null || true",
        "test -f /root/setup_postgres.log && tail -20 /root/setup_postgres.log || echo 'no log file'",
    ]

    lines: list[str] = []
    for cmd in cmds:
        lines.append(f"### {cmd}")
        _stdin, stdout, stderr = ssh.exec_command(cmd)
        lines.append(stdout.read().decode("utf-8", errors="replace"))
        err = stderr.read().decode("utf-8", errors="replace").strip()
        if err:
            lines.append(f"ERR: {err}")

    ssh.close()
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"written {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
