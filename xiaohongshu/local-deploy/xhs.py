#!/usr/bin/env python3
"""Local authenticated client; credentials are never printed."""
import argparse
import os
import base64
import json
from pathlib import Path
from urllib.request import Request, build_opener, ProxyHandler

ROOT = Path(__file__).resolve().parent
env = dict(line.split('=', 1) for line in (ROOT / 'service.env').read_text().splitlines() if '=' in line)
parser = argparse.ArgumentParser()
parser.add_argument('action', choices=['health', 'tools', 'status', 'qrcode'])
args = parser.parse_args()
paths = {'health': '/health', 'status': '/api/v1/login/status', 'qrcode': '/api/v1/login/qrcode', 'tools': '/mcp'}
headers = {'Authorization': 'Bearer ' + env['AUTH_TOKEN'], 'Accept': 'application/json, text/event-stream'}
body = None
if args.action == 'tools':
    headers['Content-Type'] = 'application/json'
    body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list', 'params': {}}).encode()
request = Request(os.environ['MCP_BASE_URL'] + paths[args.action], data=body, headers=headers)
with build_opener(ProxyHandler({})).open(request, timeout=180) as response:
    result = json.load(response)
if args.action == 'qrcode':
    data = result.get('data', {})
    encoded = data.get('img', '')
    if encoded:
        image = ROOT / 'data' / 'login-qrcode.png'
        image.write_bytes(base64.b64decode(encoded.split(',')[-1]))
        image.chmod(0o600)
        data['img'] = str(image)
print(json.dumps(result, ensure_ascii=False, indent=2))
