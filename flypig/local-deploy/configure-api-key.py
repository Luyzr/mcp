#!/usr/bin/env python3
"""Securely save a FlyAI API key for the systemd service."""

import getpass
import os
from pathlib import Path
import re
import subprocess
import sys


if os.geteuid() != 0 or not sys.stdin.isatty():
    raise SystemExit("Run as root in an interactive terminal (for example, ssh -t).")

path = Path("/mnt/mcp/flypig/local-deploy/keys.env")
if path.exists():
    raise SystemExit("keys.env already exists; inspect it before replacing credentials.")

key = getpass.getpass("FLYAI_API_KEY (hidden): ").strip()
if not re.fullmatch(r"[A-Za-z0-9._-]{16,512}", key):
    raise SystemExit("The key format or length is invalid.")

fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, "w", encoding="utf-8") as file:
    file.write("FLYAI_API_KEY=" + key + "\n")

subprocess.run(["systemctl", "restart", "flypig-mcp.service"], check=True)
print("Saved the key without displaying it and restarted flypig-mcp.service.")
