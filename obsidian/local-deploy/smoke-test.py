#!/usr/bin/env python3
"""Run as root with ../.venv/bin/python; create and remove only a unique test note."""
import asyncio
import json
import uuid
from pathlib import Path
import httpx
from fastmcp import Client

cfg = dict(line.split('=', 1) for line in Path('/etc/obsidian-mcp/service.env').read_text().splitlines() if '=' in line)
base = f"http://{cfg['HOST']}:{cfg['PORT']}"
path = f"MCP-Smoke-{uuid.uuid4().hex}.md"
marker = uuid.uuid4().hex

def payload(result):
    return result.structured_content or result.data

async def main():
    checks = {}
    async with httpx.AsyncClient(trust_env=False) as http:
        health = await http.get(base + '/health')
        assert health.status_code == 200 and health.json()['index_ready']
        checks['health'] = True
        for headers in ({}, {'Authorization': 'Bearer invalid-test-key'}):
            response = await http.post(base + '/mcp', headers=headers, json={'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-03-26','capabilities':{},'clientInfo':{'name':'smoke-test','version':'1'}}})
            assert response.status_code == 401, response.status_code
        checks['auth_rejection'] = True
    try:
        async with Client(base + '/mcp', auth=cfg['API_KEY']) as client:
            tools = await client.list_tools()
            checks['tool_count'] = len(tools)
            written = await client.call_tool('write_note_tool', {'path':path,'content':f'# MCP smoke test\n\n{marker}\n','create_only':True})
            assert not written.is_error
            read = await client.call_tool('read_note_tool', {'path':path})
            assert marker in json.dumps(payload(read))
            checks['write_read'] = True
            found = await client.call_tool('search_notes_tool', {'query':marker})
            assert path in json.dumps(payload(found))
            checks['search'] = True
            for forbidden in ('.git/config','../outside.md'):
                denied = False
                try:
                    result = await client.call_tool('read_note_tool', {'path':forbidden})
                    data = payload(result)
                    denied = result.is_error or (isinstance(data,dict) and data.get('ok') is False)
                except Exception as exc:
                    denied = any(term in str(exc).lower() for term in ('denied','not allowed','outside','forbidden','traversal','blocked','invalid','protected'))
                assert denied, f'Expected denied access: {forbidden}'
            checks['path_isolation'] = True
    finally:
        (Path(cfg['VAULT_PATH']) / path).unlink(missing_ok=True)
    print(json.dumps(checks, indent=2))

asyncio.run(main())
