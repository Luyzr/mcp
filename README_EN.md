# MCP Service Collection

[中文](README.md)

This private repository tracks source code, deployment templates, and required offline files for several MCP services. Host addresses, bind addresses, ports, credentials, and network topology are deployment settings and are not stored in Git.

## Services

| Service | Version | Directory |
|---|---|---|
| Xiaohongshu | `xiaohongshu-mcp v2.5.0` | [`xiaohongshu/`](xiaohongshu/) |
| Amap/Gaode | `@amap-lbs/amap-gui 1.0.3` | [`gaode/`](gaode/) |
| Playwright | `@playwright/mcp 0.0.81` | [`playwright/`](playwright/) |
| Firecrawl | `firecrawl-mcp 3.24.1` | [`firecrawl/`](firecrawl/) |
| Flypig | `@fly-ai/flyai-cli 1.0.16` | [`flypig/`](flypig/) |

## Security

The following data must remain local to the deployment host:

- Host IPs, bind addresses, port mappings, and network topology
- `.env`, `ports.env`, `*.keys.env`, `*.service.env`, and `*.tunnel.env`
- MCP Bearer files, API keys, cookies, and login sessions
- Dependency trees, virtual environments, build output, browser data, and runtime caches

Tracked deployment files are templates. Addresses and ports are represented by environment variables or placeholders. Set their real values only in untracked local configuration, and never copy them into source files, documentation, or Git history.

## Operations

Services are managed by systemd. Generic status check:

```sh
ssh <mcp-host> 'systemctl --type=service --state=running --no-pager'
```

See each service README or `local-deploy/README.md` for configuration, validation, and troubleshooting guidance.

## Update workflow

1. Validate service changes on the deployment host.
2. Ensure `git status` contains no addresses, ports, credentials, cookies, caches, or generated files.
3. Run the relevant smoke tests and check systemd state.
4. Commit to `main` and push to `origin`.
