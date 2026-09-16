#!/bin/sh
set -eu

if [ "$(id -u)" -ne 0 ]; then
  echo "Run as root." >&2
  exit 1
fi

cd /mnt/mcp/flypig
npm ci --ignore-scripts --no-audit --no-fund
mkdir -p .python
python3 -m pip install --disable-pip-version-check --upgrade --target .python -r local-deploy/requirements.lock
mkdir -p local-deploy/data local-deploy/bin
chmod 700 local-deploy/data
if [ ! -f local-deploy/mcp-authorization ]; then
  local-deploy/create-authorization.py
fi
install -m 0644 local-deploy/flypig-mcp.service /etc/systemd/system/flypig-mcp.service
install -m 0644 local-deploy/flypig-tunnel.service /etc/systemd/system/flypig-tunnel.service
systemctl daemon-reload
systemctl enable --now flypig-mcp.service
PYTHONPATH=/mnt/mcp/flypig/.python local-deploy/smoke-test.py

echo "Flypig MCP installation is complete"
echo "Optional API key: python3 /mnt/mcp/flypig/local-deploy/configure-api-key.py"
echo "Optional tunnel: python3 /mnt/mcp/flypig/local-deploy/configure-tunnel.py"
