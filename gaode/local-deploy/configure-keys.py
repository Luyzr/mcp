#!/usr/bin/env python3
import getpass
import os
from pathlib import Path
import re
import subprocess
import sys
if not sys.stdin.isatty():
    raise SystemExit('Run using ssh -t; keys are entered with hidden input.')
values = {name: getpass.getpass(name + ' (hidden): ').strip() for name in ('AMAP_KEY', 'AMAP_SECURITY_KEY')}
if any(not re.fullmatch(r'[A-Za-z0-9_-]+', value) for value in values.values()):
    raise SystemExit('Both keys must be nonempty, without whitespace or special characters.')
path = Path('/mnt/mcp/gaode/local-deploy/keys.env')
fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, 'w') as stream:
    for name, value in values.items():
        stream.write(name + '=' + value + '\n')
subprocess.run(['systemctl', 'restart', 'gaode-mcp'], check=True)
subprocess.run(['systemctl', 'enable', '--now', 'gaode-gui'], check=True)
print('Saved keys with mode 0600 and started services. Run gaode status to check mapReady.')
