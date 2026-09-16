#!/usr/bin/env python3
import getpass
import os
from pathlib import Path
import re
import sys

if not sys.stdin.isatty():
    raise SystemExit('Run interactively using ssh -t; do not paste secrets into chat.')
tunnel = input('Tunnel ID: ').strip()
if not re.fullmatch(r'tunnel_[A-Za-z0-9_-]+', tunnel):
    raise SystemExit('Invalid tunnel ID')
key = getpass.getpass('Runtime API key (hidden): ').strip()
if not re.fullmatch(r'sk-[A-Za-z0-9_-]+', key):
    raise SystemExit('Invalid runtime API key format')
path = Path('/mnt/mcp/gaode/local-deploy/tunnel.env')
fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, 'w') as f:
    f.write('CONTROL_PLANE_TUNNEL_ID=' + tunnel + '\nCONTROL_PLANE_API_KEY=' + key + '\n')
print('Saved configuration with mode 0600. No secrets displayed. Ready for connection verification.')
