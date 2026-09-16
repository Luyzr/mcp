#!/usr/bin/env python3
"""Create the local MCP bearer token once, without printing it."""

import os
from pathlib import Path
import secrets


path = Path("/mnt/mcp/flypig/local-deploy/mcp-authorization")
if path.exists():
    raise SystemExit("mcp-authorization already exists; leaving it unchanged.")
fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, "w", encoding="utf-8") as file:
    file.write("Bearer " + secrets.token_urlsafe(48) + "\n")
print("Created local MCP authorization with mode 0600.")
