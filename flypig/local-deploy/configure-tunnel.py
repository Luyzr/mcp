#!/usr/bin/env python3
"""Securely configure a dedicated OpenAI MCP tunnel for Flypig."""

import getpass
import os
from pathlib import Path
import re
import subprocess
import sys


if os.geteuid() != 0 or not sys.stdin.isatty():
    raise SystemExit("Run as root in an interactive terminal (for example, ssh -t).")

path = Path("/mnt/mcp/flypig/local-deploy/tunnel.env")
if path.exists():
    raise SystemExit("tunnel.env already exists; inspect it before changing credentials.")

tunnel = input("Flypig Tunnel ID: ").strip()
if not re.fullmatch(r"tunnel_[A-Za-z0-9_-]+", tunnel):
    raise SystemExit("Invalid tunnel ID")
key = getpass.getpass("OpenAI tunnel runtime API key (hidden): ").strip()
if not re.fullmatch(r"sk-[A-Za-z0-9_-]+", key):
    raise SystemExit("Invalid runtime API key")

fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, "w", encoding="utf-8") as file:
    file.write(f"CONTROL_PLANE_TUNNEL_ID={tunnel}\nCONTROL_PLANE_API_KEY={key}\n")

subprocess.run(["systemctl", "enable", "--now", "flypig-tunnel.service"], check=True)
print("Saved credentials without displaying them. Check the local tunnel readiness endpoint.")
