"""Загрузка и запуск setup_postgres.sh на AdminVPS."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import paramiko

HOST = "157.22.231.226"
SCRIPT = Path(__file__).with_name("setup_postgres.sh")
OUT = Path(__file__).with_name("step2_setup_output.txt")
CLIENT_IP = "87.121.38.47"


def main() -> int:
    password = os.environ.get("ADMINVPS_ROOT_PASSWORD")
    if not password:
        print("ADMINVPS_ROOT_PASSWORD not set", file=sys.stderr)
        return 1

    script = SCRIPT.read_text(encoding="utf-8").replace("\r\n", "\n")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username="root", password=password, timeout=30)

    sftp = ssh.open_sftp()
    with sftp.file("/root/setup_postgres.sh", "w") as remote:
        remote.write(script)
    sftp.chmod("/root/setup_postgres.sh", 0o755)
    sftp.close()

    cmd = f"bash /root/setup_postgres.sh {CLIENT_IP} 2>&1 | tee /root/setup_postgres.log"
    _stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    code = stdout.channel.recv_exit_status()

    OUT.write_text(out + ("\nSTDERR:\n" + err if err.strip() else ""), encoding="utf-8")
    ssh.close()

    print(f"exit={code}, written {OUT}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
