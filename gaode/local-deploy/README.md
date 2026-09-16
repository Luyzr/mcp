# gaode CLI + MCP
Host: <mcp-host>
Root: /mnt/mcp/gaode
MCP: http://<loopback-address>:<port>/mcp (local bearer auth)
Health: http://<loopback-address>:<port>/healthz
CLI: /mnt/mcp/gaode/local-deploy/bin/gaode
Services: gaode-mcp.service, gaode-tunnel.service

The MCP service starts at boot. The tunnel unit is installed but not enabled until configured.
Configure a dedicated tunnel using: python3 /mnt/mcp/gaode/local-deploy/configure-tunnel.py (interactive SSH).
Then: systemctl enable --now gaode-tunnel
Tunnel readiness: curl http://<loopback-address>:<port>/readyz
Never copy the Xiaohongshu tunnel identity into this service.
MCP authorization is stored in /mnt/mcp/gaode/local-deploy/mcp-authorization (0600).
Dependencies are recorded in requirements.lock.

Source: official npm package @amap-lbs/amap-gui@1.0.3; code in node_modules/@amap-lbs/amap-gui.
Save real keys in keys.env with chmod 600, then systemctl restart gaode-mcp && systemctl enable --now gaode-gui.
GUI runs inside Xvfb on this headless host.

## Map validation completed
JS API keys configured with mode 0600. gaode-gui reports mapReady=true. MCP initialize and six-tool discovery passed. Real MCP searchPOI for 北京南站 and driving route 北京南站 to 天安门 both returned success. gaode-mcp and gaode-gui are active and enabled. Tunnel still awaits tunnel.env.

## Tunnel validation completed
All gaode services active and enabled. tunnel.env mode 0600. Tunnel /healthz returns 200 live; /readyz returns 200 ready. MCP six-tool discovery and gaode_status mapReady=true verified. ChatGPT plugin UI connection must be created/selected in the intended workspace.
