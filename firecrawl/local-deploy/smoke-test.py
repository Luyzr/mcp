#!/usr/bin/env python3
import os,sys
os.execv('/mnt/mcp/firecrawl/local-deploy/runtime/node/bin/node', ['node', '/mnt/mcp/firecrawl/local-deploy/smoke-test.mjs', *sys.argv[1:]])
