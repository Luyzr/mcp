# Obsidian MCP deployment

Source: `ykoellmann/obsidian-mcp` 2.1.0, pinned revision in `UPSTREAM.md`.
The imported source and deployment templates belong to `Luyzr/mcp`.

## Server layout

- Source and venv: `/mnt/mcp/obsidian`, `/mnt/mcp/obsidian/.venv`
- Python 3.12.13: `/opt/obsidian-python/cpython-3.12.13-linux-x86_64-gnu`
- Vault: `/data/obsidian_library`, private repository `Luyzr/obsidian_library`, branch `master`
- Units: `/etc/systemd/system/obsidian-mcp.service` and `obsidian-tunnel.service` (enabled and running)
- Service identity: `obsidian-mcp`, no login shell
- Environment and Bearer secret: `/etc/obsidian-mcp/service.env`, root-only mode 0600
- Audit/locks: `/var/lib/obsidian-mcp`
- Vault deploy key: `/root/.ssh/obsidian_library_ed25519`, not accessible to the MCP process
- Server service inventory: `/mnt/codex/SERVER_INVENTORY.md`

## Connect

Obsidian uses the same OpenAI Secure MCP Tunnel transport as the other server MCPs.
The backend listens only on `http://127.0.0.1:18076/mcp`; it is not exposed over Tailscale or the public network.
The outbound tunnel attaches to this authenticated backend, with readiness at `http://127.0.0.1:18077/readyz` and liveness at `/healthz`.

Configured tunnel: `tunnel_6aab5e3f57a4819184e1ed130637ec97` (name `obsidian`), in the same organization/workspace as the existing services. Liveness and readiness verified.

For first-time recovery when `tunnel.env` is absent:

```sh
python3 /mnt/mcp/obsidian/local-deploy/configure-tunnel.py tunnel_6aab5e3f57a4819184e1ed130637ec97
systemctl start obsidian-tunnel
curl --noproxy '*' http://127.0.0.1:18077/readyz
```

The helper copies the existing Flypig runtime principal into Obsidian's own root-only `tunnel.env`; it does not reuse Flypig's tunnel ID or modify its service. If that principal lacks permission for the new tunnel, replace only Obsidian's runtime key securely.
`local-deploy/mcp-authorization` holds the backend Authorization header (root-only, Git-ignored).
`local-deploy/runtime/bin/tunnel-client` is a copy of the established tunnel client (Git-ignored); its hash is recorded in `deployment.json`.
No API key or authorization file is committed to Git.

After readiness succeeds, select the Obsidian tunnel in the ChatGPT connector settings and verify a real note read. Readiness alone does not prove a cloud tool call succeeded.

## Operations

```sh
systemctl status obsidian-mcp obsidian-tunnel --no-pager
systemctl is-enabled obsidian-mcp
curl --noproxy '*' http://127.0.0.1:18076/health
/mnt/mcp/obsidian/.venv/bin/python /mnt/mcp/obsidian/local-deploy/smoke-test.py
journalctl -u obsidian-mcp --no-pager -n 50
```

`smoke-test.py` must run as root to read the credential. It verifies health, rejects missing/wrong credentials, discovers tools, writes/reads/searches a unique temporary note, verifies path restrictions, and removes its own test note.

MCP allows note edits throughout the vault, excluding `.git`, `.obsidian`, `.trash`, Git control files and `_AI_INSTRUCTIONS.md`. Existing-note replacement requires its read revision. Permanent deletion and bulk/move/delete tool groups remain disabled. Canvas, Excalidraw, Kanban and Bases tools are enabled.

Git sync is explicit, not automatic. On the server use:

```sh
git -c safe.directory=/data/obsidian_library -C /data/obsidian_library status
git -c safe.directory=/data/obsidian_library -C /data/obsidian_library pull --ff-only
# Review changes and stage the intended note paths before committing.
git -c safe.directory=/data/obsidian_library -C /data/obsidian_library add <paths>
git -c safe.directory=/data/obsidian_library -C /data/obsidian_library commit -m 'Update notes'
git -c safe.directory=/data/obsidian_library -C /data/obsidian_library push
```

Do not pull over concurrent writes; coordinate edits before Git merges. A non-fast-forward pull/push requires explicit conflict resolution. Git operations use the repository-scoped `core.sshCommand` and dedicated key, leaving other repositories' SSH credentials unchanged.

## Rebuild/recovery

Install the pinned Python with `UV_PYTHON_INSTALL_DIR=/opt/obsidian-python uv python install 3.12.13`.
From `/mnt/mcp/obsidian`, run `uv sync --frozen --python /opt/obsidian-python/cpython-3.12.13-linux-x86_64-gnu/bin/python3.12`.
Restore the vault repository, dedicated Git key, root-only environment file, service user and owned state directories from secure backup. Keep `.git` root-owned mode 0700 and the vault accessible to `obsidian-mcp`.
Restore the tunnel runtime binary, root-only `tunnel.env` and `mcp-authorization`. Install both checked-in units, run `systemctl daemon-reload` and `systemctl enable --now obsidian-mcp obsidian-tunnel`.
Verify `/health` and the smoke test; update `SERVER_INVENTORY.md` after service/deployment changes.

Do not regenerate or print existing credentials during routine upgrades. Keep the lockfile pinned, inspect upstream changes, and rerun relevant upstream tests before deployment.
