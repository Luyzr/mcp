import {createRequire} from 'node:module';
import {readFileSync,writeFileSync} from 'node:fs';
import assert from 'node:assert/strict';
const require = createRequire(import.meta.url);
const dep = createRequire(require.resolve('fastmcp'));
const {Client} = await import(dep.resolve('@modelcontextprotocol/sdk/client/index.js'));
const {StreamableHTTPClientTransport} = await import(dep.resolve('@modelcontextprotocol/sdk/client/streamableHttp.js'));
const url = new URL(process.env.MCP_URL);
for (const token of ['', 'Bearer incorrect']) assert.equal((await fetch(url,{headers:{Authorization:token}})).status,401);
console.log('PASS: missing and incorrect bearer rejected (401)');
const client=new Client({name:'firecrawl-deployment-check',version:'1.0.0'});
const transport=new StreamableHTTPClientTransport(url,{requestInit:{headers:{Authorization:readFileSync('/mnt/mcp/firecrawl/local-deploy/mcp-authorization','utf8').trim()}}});
try {
 await client.connect(transport);
 console.log('PASS: SDK initialize and initialized notification');
 const result=await client.listTools();
 for(const name of ['firecrawl_scrape','firecrawl_map','firecrawl_search','firecrawl_crawl']) assert.ok(result.tools.some(t=>t.name===name));
 writeFileSync('/mnt/mcp/firecrawl/local-deploy/tools.json',JSON.stringify(result,null,2)+'\n');
 console.log('PASS: tools/list',result.tools.length,'tools');
 if(process.argv.includes('--cloud')) {
  assert.match(readFileSync('/mnt/mcp/firecrawl/.env','utf8'),/^FIRECRAWL_API_KEY=fc-/m,'Configure API key first');
  const result=await client.callTool({name:'firecrawl_scrape',arguments:{url:'https://example.com',formats:['markdown']}},undefined,{timeout:90000});
  assert.ok(!result.isError,'Cloud scrape failed; check account credentials and credits');
  assert.match(JSON.stringify(result),/Example Domain/);
  console.log('PASS: cloud scrape https://example.com');
 } else console.log('SKIPPED: cloud scrape; API key pending');
} finally { await client.close(); }
