"""Убрать дубли hostssl в pg_hba.conf (после повторного запуска setup)."""
import os
import paramiko

password = os.environ["ADMINVPS_ROOT_PASSWORD"]
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("157.22.231.226", username="root", password=password, timeout=30)
cmd = r"""
python3 <<'PY'
from pathlib import Path
path = Path('/etc/postgresql/16/main/pg_hba.conf')
lines = path.read_text().splitlines()
seen = set()
out = []
for line in lines:
    key = line.strip()
    if key.startswith('hostssl dompro dompro'):
        if key in seen:
            continue
        seen.add(key)
    if key == '# DomPro dev — удалённый доступ только с IP разработчика, только SSL':
        if '# DomPro dev' in '\n'.join(out[-3:]):
            continue
    out.append(line)
path.write_text('\n'.join(out) + '\n')
PY
systemctl reload postgresql
"""
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
print(stderr.read().decode())
ssh.close()
