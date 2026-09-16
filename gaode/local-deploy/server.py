"""Authenticated loopback MCP adapter for the locally installed CLI."""
import asyncio
import contextlib
import hmac
import json
import os
from pathlib import Path
import signal

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from starlette.responses import JSONResponse
import uvicorn

ROOT = Path(__file__).resolve().parent
CONFIG = json.loads((ROOT / 'config.json').read_text())
MCP_BIND_HOST = os.environ['MCP_BIND_HOST']
MCP_PORT = int(os.environ['MCP_PORT'])
AUTH = (ROOT / 'mcp-authorization').read_text().strip()
if not AUTH.startswith('Bearer ') or len(AUTH) < 40:
    raise RuntimeError('Missing or invalid local authentication configuration')
server = FastMCP(CONFIG['name'], host=MCP_BIND_HOST, port=MCP_PORT,
                 stateless_http=True, json_response=True)
semaphore = asyncio.Semaphore(2)

async def run_cli(arguments: list[str]) -> dict:
    if len(arguments) > 80 or any(len(x) > 16384 or '\0' in x for x in arguments):
        raise ValueError('CLI arguments exceed limits')
    async with semaphore:
        process = await asyncio.create_subprocess_exec(
            CONFIG['cli'], *arguments, stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            start_new_session=True,
        )
        async def limited_read(stream):
            chunks = []
            size = 0
            while chunk := await stream.read(8192):
                size += len(chunk)
                if size > 2_000_000:
                    raise ValueError('CLI output exceeds 2 MB; narrow the query')
                chunks.append(chunk)
            return b''.join(chunks).decode('utf-8', errors='replace')
        tasks = [asyncio.create_task(limited_read(process.stdout)),
                 asyncio.create_task(limited_read(process.stderr)),
                 asyncio.create_task(process.wait())]
        try:
            stdout, stderr, code = await asyncio.wait_for(asyncio.gather(*tasks), timeout=90)
        finally:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
            await process.wait()
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
    for secret_name in ('AMAP_KEY', 'AMAP_SECURITY_KEY'):
        secret = os.environ.get(secret_name)
        if secret:
            stdout, stderr = stdout.replace(secret, '[REDACTED]'), stderr.replace(secret, '[REDACTED]')
    if code:
        raise RuntimeError(f'CLI exited {code}: {stderr or stdout}')
    try:
        payload = json.loads(stdout)
    except (ValueError, TypeError):
        payload = None
    if isinstance(payload, dict) and (payload.get('ok') is False or payload.get('success') is False):
        raise RuntimeError(json.dumps(payload.get('error', payload), ensure_ascii=False))
    if payload is not None:
        return {'exit_code': code, 'data': payload, 'stderr': stderr}
    return {'exit_code': code, 'stdout': stdout, 'stderr': stderr}

@server.tool(name=CONFIG['name'] + '_help', annotations=ToolAnnotations(readOnlyHint=True))
async def cli_help(command: str = '') -> dict:
    """Show CLI commands or exact arguments for one command. Call before using unfamiliar options."""
    if command and command not in CONFIG['commands']:
        raise ValueError('Unknown command')
    return await run_cli(([command] if command else []) + ['--help'])

def register(command, description, readonly):
    async def invoke(arguments: list[str] | None = None) -> dict:
        args = list(arguments or [])
        if CONFIG['name'] == 'gaode' and command not in ('status', 'getLastEvent') and not os.environ.get('AMAP_KEY'):
            raise RuntimeError('AMAP_KEY is not configured. Configure local-deploy/keys.env and start gaode-gui.service.')
        return await run_cli([command, *args])
    server.add_tool(invoke, name=CONFIG['name'] + '_' + command.replace('-', '_'),
                    description=description + ' Pass CLI arguments as a string array; consult the help tool for flags.',
                    annotations=ToolAnnotations(readOnlyHint=readonly, destructiveHint=not readonly,
                                                idempotentHint=readonly, openWorldHint=True))

for command, settings in CONFIG['commands'].items():
    register(command, settings['description'], settings['readonly'])

@server.custom_route('/healthz', methods=['GET'])
async def health(request):
    return JSONResponse({'status': 'ok', 'service': CONFIG['name']})

class BearerAuth:
    def __init__(self, app):
        self.app = app
    async def __call__(self, scope, receive, send):
        if scope['type'] == 'http' and scope['path'] != '/healthz':
            headers = dict(scope.get('headers', []))
            if not hmac.compare_digest(headers.get(b'authorization', b''), AUTH.encode()):
                await JSONResponse({'error': 'unauthorized'}, status_code=401)(scope, receive, send)
                return
        await self.app(scope, receive, send)

if __name__ == '__main__':
    uvicorn.run(BearerAuth(server.streamable_http_app()), host=MCP_BIND_HOST, port=MCP_PORT, access_log=False)
