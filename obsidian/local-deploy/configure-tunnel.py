#!/usr/bin/env python3
"""Configure Obsidian's dedicated tunnel ID; reuse the established runtime principal.
Usage (root): python3 configure-tunnel.py tunnel_...
Never emits the runtime key. Does not alter any other MCP's configuration.
"""
import os
import re
import sys
from pathlib import Path

if os.geteuid() != 0:
    raise SystemExit('Run as root on the server.')
if len(sys.argv) != 2 or not re.fullmatch(r'tunnel_[A-Za-z0-9_-]+', sys.argv[1]):
    raise SystemExit('Usage: configure-tunnel.py tunnel_...')
base = Path('/mnt/mcp/obsidian/local-deploy')
target = base / 'tunnel.env'
if target.exists():
    raise SystemExit('tunnel.env already exists; inspect before changing tunnel identity.')
source = Path('/mnt/mcp/flypig/local-deploy/tunnel.env')
values = dict(line.split('=', 1) for line in source.read_text().splitlines() if '=' in line and not line.startswith('#'))
key = values['CONTROL_PLANE_API_KEY'].strip().strip('"').strip("'")
if not key.startswith('sk-') or '\n' in key:
    raise SystemExit('Existing runtime credential has an unsupported format.')
fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, 'w') as stream:
    stream.write('CONTROL_PLANE_TUNNEL_ID=' + sys.argv[1] + '\nCONTROL_PLANE_API_KEY=' + key + '\n')
print('Saved root-only tunnel configuration. Validate and start obsidian-tunnel, then update the inventory.')
