# Obsidian MCP deployment

Source: `ykoellmann/obsidian-mcp` 2.1.0, pinned revision in `UPSTREAM.md`.
The imported source and deployment templates belong to `Luyzr/mcp`.

## Server layout

- Source and venv: `/mnt/mcp/obsidian`, `/mnt/mcp/obsidian/.venv`
- Python 3.12.13: `/opt/obsidian-python/cpython-3.12.13-linux-x86_64-gnu`
- Vault: `/data/obsidian_library`, private repository `Luyzr/obsidian_library`, branch `master`
- Unit: `/etc/systemd/system/obsidian-mcp.service` (enabled)
- Service identity: `obsidian-mcp`, no login shell
- Environment and Bearer secret: `/etc/obsidian-mcp/service.env`, root-only mode 0600
- Audit/locks: `/var/lib/obsidian-mcp`
- Vault deploy key: `/root/.ssh/obsidian_library_ed25519`, not accessible to the MCP process
- Server service inventory: `/mnt/codex/SERVER_INVENTORY.md`

## Connect

Streamable HTTP endpoint: `http://100.107.152.83:18076/mcp`.
Accessible over the encrypted Tailscale network only; no public listener or public HTTPS/tunnel was provisioned.
Send `Authorization: Bearer <API_KEY>` with the key from the root-only environment file. Do not paste the key into Git or logs.

A cloud ChatGPT connector cannot reach this private address directly. A dedicated secure tunnel or HTTPS/OAuth gateway is a separate connection step; no existing MCP tunnel credentials are reused.

## Operations

```sh
systemctl status obsidian-mcp --no-pager
systemctl is-enabled obsidian-mcp
curl --noproxy '*' http://100.107.152.83:18076/health
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
Install the checked-in unit, run `systemctl daemon-reload` and `systemctl enable --now obsidian-mcp`.
Verify `/health` and the smoke test; update `SERVER_INVENTORY.md` after service/deployment changes.

Do not regenerate or print existing credentials during routine upgrades. Keep the lockfile pinned, inspect upstream changes, and rerun relevant upstream tests before deployment.
