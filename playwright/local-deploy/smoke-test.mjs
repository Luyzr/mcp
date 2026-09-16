import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js';
import { readFileSync, writeFileSync } from 'node:fs';
import assert from 'node:assert/strict';
const url = new URL(process.env.MCP_URL);
const unauthorized = await fetch(url);
assert.equal(unauthorized.status, 401);
const wrong = await fetch(url, {headers: {Authorization: 'Bearer incorrect'}});
assert.equal(wrong.status, 401);
const client = new Client({name:'playwright-deployment-check',version:'1.0.0'});
const transport = new StreamableHTTPClientTransport(url, {requestInit:{headers:{Authorization:readFileSync('/mnt/mcp/playwright/local-deploy/mcp-authorization','utf8').trim()}}});
try {
 await client.connect(transport);
 const controller = new AbortController();
 const timer = setTimeout(() => controller.abort(), 2000);
 const headers = {Authorization:readFileSync('/mnt/mcp/playwright/local-deploy/mcp-authorization','utf8').trim(), Accept:'application/json, text/event-stream', 'Content-Type':'application/json'};
 let probeSession;
 try {
  const init = await fetch(url,{method:'POST',headers,signal:controller.signal,body:JSON.stringify({jsonrpc:'2.0',id:1,method:'initialize',params:{protocolVersion:'2024-11-05',capabilities:{},clientInfo:{name:'sse-probe',version:'1'}}})});
  assert.equal(init.status,200);
  probeSession=init.headers.get('mcp-session-id');
  await init.text();
  assert.ok(probeSession);
  const stream = await fetch(url,{headers:{...headers,Accept:'text/event-stream','Mcp-Session-Id':probeSession},signal:controller.signal});
  assert.equal(stream.status,200);
  await stream.body.cancel();
  console.log('SSE response headers within 2s PASS');
 } finally {
  clearTimeout(timer); controller.abort();
  if (probeSession) await fetch(url,{method:'DELETE',headers:{...headers,'Mcp-Session-Id':probeSession}});
 }
 const tools = await client.listTools();
 writeFileSync('/mnt/mcp/playwright/local-deploy/tools.json', JSON.stringify(tools,null,2)+'\n');
 console.log('tools/list:', tools.tools.length);
 const call = async (name,args) => {
  const result=await client.callTool({name,arguments:args});
  assert.ok(!result.isError, JSON.stringify(result));
  console.log(name, 'PASS'); return result;
 };
 const nav=await call('browser_navigate',{url:'https://example.com'});
 assert.match(JSON.stringify(nav), /Example Domain/);
 await call('browser_evaluate',{function:'() => { document.body.innerHTML = `<button id="test">Click me</button>`; document.getElementById("test").onclick = () => { document.getElementById("test").textContent = "Clicked"; }; }'});
 const before=await call('browser_snapshot',{});
 const text=before.content.filter(x=>x.type==='text').map(x=>x.text).join('\n');
 const buttonRef=text.match(/button "Click me" \[ref=(e[0-9]+)\]/)?.[1];
 assert.ok(buttonRef, text);
 await call('browser_click',{element:'test button',target:buttonRef});
 const snapshot=await call('browser_snapshot',{});
 assert.match(JSON.stringify(snapshot), /Clicked/);
 const shot=await call('browser_take_screenshot',{type:'png'});
 assert.ok(shot.content.some(x=>x.type==='image') || /png/.test(JSON.stringify(shot)));
 await call('browser_close',{});
 console.log('PASS: authentication, MCP handshake, tools, HTTPS navigation, DOM interaction, snapshot, screenshot, browser close');
} finally { await transport.terminateSession().catch(()=>{}); await client.close(); }
