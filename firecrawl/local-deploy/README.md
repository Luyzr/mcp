# Firecrawl MCP deployment on <mcp-host>

## Status

Source: https://github.com/firecrawl/firecrawl-mcp-server
Version: 3.24.1; commit: `4db752ee00910e17ec73f28b40796f0830fe86da`.
Node.js: isolated 22.23.2, verified against nodejs.org SHA-256 manifest.
pnpm: 10.32.1; installation uses upstream frozen pnpm-lock.yaml including FastMCP patch.
Upstream source is unchanged. Service runs under dedicated firecrawl-mcp user.

MCP, authentication and tunnel services are active and enabled. Firecrawl API key is configured.
Dedicated tunnel credentials are configured; /readyz returns HTTP 200 ready.
Official SDK tool discovery lists 25 tools. A real Firecrawl cloud scrape of https://example.com returned Example Domain.
Cloud API: https://api.firecrawl.dev (not a self-hosted crawler).

## Endpoints

- Authenticated MCP: http://<loopback-address>:<port>/mcp
- Tunnel health (after configuration): http://<loopback-address>:<port>/readyz
- Internal MCP backend: http://<loopback-address>:<port>/mcp

All listeners bind loopback. No inbound firewall opening is required.
`mcp-authorization` contains an independent local Bearer credential; tunnel.env and .env contain provider credentials. Do not include these in logs or commits.

## Configure Firecrawl cloud API

Create a key at https://www.firecrawl.dev/app/api-keys.
From your terminal:

```sh
ssh -t <mcp-host> python3 /mnt/mcp/firecrawl/local-deploy/configure-api-key.py
ssh <mcp-host> python3 /mnt/mcp/firecrawl/local-deploy/smoke-test.py --cloud
```

The helper hides input, atomically writes `/mnt/mcp/firecrawl/.env` with mode 0600 and restarts the backend.
Alternatively edit FIRECRAWL_API_KEY in that file and restart firecrawl-mcp.
The cloud test scrapes one example.com page and may consume a Firecrawl credit.

## Configure ChatGPT tunnel

Create a NEW Firecrawl tunnel at https://platform.openai.com/settings/organization/tunnels and associate the intended ChatGPT workspace. Do not reuse another service's Tunnel ID.
Then run:

```sh
ssh -t <mcp-host> python3 /mnt/mcp/firecrawl/local-deploy/configure-tunnel.py
ssh <mcp-host> curl -fsS http://<loopback-address>:<port>/readyz
```

The helper asks for Tunnel ID and a hidden OpenAI runtime API key, saves tunnel.env with mode 0600, and enables/starts firecrawl-tunnel.
Open https://chatgpt.com/plugins, create a developer app named Firecrawl, choose Tunnel and select this dedicated tunnel. Availability requires workspace developer-mode and Platform tunnel permissions.
Official guide: https://developers.openai.com/api/docs/guides/secure-mcp-tunnels

## Validation and operations

```sh
python3 /mnt/mcp/firecrawl/local-deploy/smoke-test.py
systemctl status firecrawl-mcp firecrawl-mcp-auth firecrawl-tunnel
journalctl -u firecrawl-mcp -u firecrawl-mcp-auth -u firecrawl-tunnel --since '10 minutes ago'
```

The smoke test uses the MCP SDK from the locked dependency tree. It checks 401 for absent/incorrect bearer, initialize, initialized notification and tools/list. `--cloud` additionally validates Example Domain content via firecrawl_scrape.
Results: validation.log; tool schemas: tools.json; deployment versions: deployment.json.
Cloud scrape and tunnel readiness are verified. Actual invocation from the ChatGPT UI has not been verified by the server-side checks.

Rebuild without updating versions:

```sh
cd /mnt/mcp/firecrawl
export PATH="/mnt/mcp/firecrawl/local-deploy/runtime/node/bin:$PATH"
node local-deploy/build-tools/node_modules/pnpm/bin/pnpm.cjs install --frozen-lockfile
systemctl restart firecrawl-mcp
```

Stop this deployment: `systemctl disable --now firecrawl-tunnel firecrawl-mcp-auth firecrawl-mcp`.
Local deployment files are excluded through .git/info/exclude; .env is ignored by upstream.
