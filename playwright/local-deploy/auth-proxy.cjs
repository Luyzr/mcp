const http = require('node:http');
const fs = require('node:fs');
const crypto = require('node:crypto');
const bindHost = process.env.MCP_BIND_HOST;
const listenPort = Number(process.env.MCP_PORT);
const backendHost = process.env.MCP_BACKEND_HOST;
const backendPort = Number(process.env.MCP_BACKEND_PORT);
if (!bindHost || !listenPort || !backendHost || !backendPort) throw new Error('Missing local network configuration');
const expected = Buffer.from(fs.readFileSync('/mnt/mcp/playwright/local-deploy/mcp-authorization', 'utf8').trim());
const server = http.createServer((req, res) => {
  const token = Buffer.from(req.headers.authorization || '');
  if (token.length !== expected.length || !crypto.timingSafeEqual(token, expected)) {
    res.writeHead(401, {'WWW-Authenticate': 'Bearer', 'Content-Type': 'text/plain'});
    res.end('Unauthorized');
    return;
  }
  if (req.url !== '/mcp') {
    res.writeHead(404); res.end(); return;
  }
  const headers = {...req.headers, host: `${backendHost}:${backendPort}`};
  delete headers.authorization;
  const upstream = http.request({host: backendHost, port: backendPort, path: '/mcp', method: req.method, headers}, reply => {
    res.writeHead(reply.statusCode, reply.headers);
    res.flushHeaders();
    reply.pipe(res);
    reply.on('error', () => res.destroy());
  });
  upstream.on('error', () => {
    if (!res.headersSent) { res.writeHead(502); res.end('MCP upstream unavailable'); }
    else res.destroy();
  });
  req.on('aborted', () => upstream.destroy());
  res.on('close', () => upstream.destroy());
  req.pipe(upstream);
});
server.headersTimeout = 15000;
server.requestTimeout = 0;
server.listen(listenPort, bindHost, () => console.log('Authenticated MCP endpoint is ready'));
process.on('SIGTERM', () => server.close(() => process.exit(0)));
