#!/usr/bin/env python3
import getpass
import os
from pathlib import Path
import re
import subprocess
import sys
if os.geteuid() != 0 or not sys.stdin.isatty():
    raise SystemExit('Run as root interactively with ssh -t.')
path = Path('/mnt/mcp/firecrawl/local-deploy/tunnel.env')
if path.exists():
    raise SystemExit('tunnel.env already exists; inspect existing configuration before changing it.')
tunnel = input('Firecrawl Tunnel ID: ').strip()
if not re.fullmatch(r'tunnel_[A-Za-z0-9_-]+', tunnel):
    raise SystemExit('Invalid tunnel ID')
key = getpass.getpass('Runtime API key (hidden): ').strip()
if not re.fullmatch(r'sk-[A-Za-z0-9_-]+', key):
    raise SystemExit('Invalid runtime API key')
fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, 'w') as f:
    f.write('CONTROL_PLANE_TUNNEL_ID=' + tunnel + '\nCONTROL_PLANE_API_KEY=' + key + '\n')
subprocess.run(['systemctl', 'enable', '--now', 'firecrawl-tunnel.service'], check=True)
print('Saved credentials without displaying them. Tunnel started; check its local readiness endpoint.')
