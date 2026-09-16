#!/usr/bin/env python3
import getpass, os, re, subprocess, sys
from pathlib import Path
if os.geteuid() != 0 or not sys.stdin.isatty():
    raise SystemExit('Run as root interactively with ssh -t.')
key = getpass.getpass('Firecrawl cloud API key (hidden): ').strip()
if not re.fullmatch(r'fc-[A-Za-z0-9_-]+', key):
    raise SystemExit('Expected an fc- API key.')
p = Path('/mnt/mcp/firecrawl/.env')
tmp = p.with_suffix('.env.new')
fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, 'w') as f:
    f.write('FIRECRAWL_API_KEY=' + key + '\n')
os.replace(tmp, p)
subprocess.run(['systemctl', 'restart', 'firecrawl-mcp.service'], check=True)
print('API key saved without displaying it. Run local-deploy/smoke-test.py --cloud to verify.')
