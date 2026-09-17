# MCP Service Collection

[中文](README.md)

This private repository manages source code, deployment configuration, verification scripts, and plugin assets for six MCP services. Services run on a Linux server under systemd and use **OpenAI Secure MCP Tunnel** for client access. Obsidian notes live separately in [obsidian_library](https://github.com/Luyzr/obsidian_library).

## Services

| Service | Recorded version | Purpose | Directory |
| --- | --- | --- | --- |
| Xiaohongshu | `xiaohongshu-mcp v2.5.0` | Search, read, and manage content | [xiaohongshu](xiaohongshu/) |
| Amap/Gaode | `@amap-lbs/amap-gui 1.0.3` | Place search and routing | [gaode](gaode/) |
| Playwright | `@playwright/mcp 0.0.81` | Browser automation and verification | [playwright](playwright/) |
| Firecrawl | `firecrawl-mcp 3.24.1` | Web search and content extraction | [firecrawl](firecrawl/) |
| Flypig | `@fly-ai/flyai-cli 1.0.16` | Travel information search | [flypig](flypig/) |
| Obsidian | `obsidian-remote-mcp 2.1.0` | Notes, search, links, and tags | [obsidian](obsidian/) |

Versions reflect deployment records, not necessarily the latest upstream releases.

## Deployment and access

- Code root: `/mnt/mcp`, branch `main`.
- Each MCP has its own systemd service and tunnel. Some services also use an authentication proxy or GUI unit.
- The tunnel establishes an outbound connection from the server; backend authentication remains enabled. Clients do not need Tailscale access to the MCP endpoint.
- Tunnel liveness/readiness is not proof of a successful client tool call. Verify an actual call after connecting a client.
- Server inventory and recovery record: `/mnt/codex/SERVER_INVENTORY.md`.

See service-specific documentation, including the [Obsidian deployment guide](obsidian/local-deploy/README.md).

## Obsidian library

Source: `/mnt/mcp/obsidian`. Vault: `/data/obsidian_library`. Notes are versioned in [Luyzr/obsidian_library](https://github.com/Luyzr/obsidian_library), branch `master`.

`obsidian-mcp.service` serves authorized note operations; `obsidian-tunnel.service` provides tunnel access. `obsidian-git-sync.timer` runs **bidirectional sync every minute on the minute**, committing local changes, fetching and merging remote updates, and pushing without force. The persistent timer is enabled at boot.

Incoming merges are previewed in a temporary worktree. MCP and tunnel services pause briefly only while applying incoming updates and are restored afterward. Conflicts preserve both commits and the original notes, record `blocked`, and require manual resolution. Network failures retry next minute. Git-ignored files are excluded.

This sync covers GitHub and the server vault. Separate Mac/iPhone vaults need their own client sync configuration. It provides eventual consistency, not real-time equality during edits or outages.

Plugin listing copy and a **256×256 PNG icon under 10 KB** are in [branding](obsidian/local-deploy/branding/).

## Operations

Run on the server:

```sh
systemctl is-active obsidian-mcp obsidian-tunnel obsidian-git-sync.timer
systemctl list-timers obsidian-git-sync.timer --no-pager
cat /var/lib/obsidian-git-sync/status.json
journalctl -u obsidian-git-sync.service --no-pager -n 30
```

The sync service is oneshot: `inactive` between runs is normal. Check the timer, last execution result, and status file. `synced` describes the most recently verified state.

## Credentials and Git

Keep API keys, Bearer credentials, SSH private keys, cookies, sessions, and secret configuration in restricted server files outside Git. Exclude dependencies, virtual environments, caches, runtime data, and tunnel runtime files. Do not copy sensitive connection details or credentials into documentation or logs.

Service code is reviewed and committed manually. Automatic minute-by-minute sync applies only to the vault, not this repository.

## Update workflow

1. Inspect server Git status and preserve unrelated work.
2. Make the intended change, run relevant checks, and verify service behavior.
3. Update the server inventory for service, deployment, or startup changes.
4. Review staged files for credentials, runtime data, and unrelated edits; commit and push to `main`.
