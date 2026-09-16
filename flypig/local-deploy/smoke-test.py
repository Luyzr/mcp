#!/usr/bin/env python3
"""Validate auth, MCP initialization, tool discovery and local status."""

import asyncio
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.request

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


ROOT = Path(__file__).resolve().parent
URL = os.environ["MCP_URL"]
HEALTH_URL = os.environ["MCP_HEALTH_URL"]
EXPECTED_TOOLS = {
    "flypig_status",
    "flypig_help",
    "flypig_keyword_search",
    "flypig_ai_search",
    "flypig_search_flight",
    "flypig_search_train",
    "flypig_search_hotel",
    "flypig_search_poi",
    "flypig_search_marriott_hotel",
    "flypig_search_marriott_package",
}


def wait_for_service() -> None:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(HEALTH_URL, timeout=2) as response:
                if response.status == 200:
                    return
        except (OSError, urllib.error.URLError):
            time.sleep(0.25)
    raise RuntimeError("Flypig MCP did not become healthy within 30 seconds")


def check_rejected(token: str) -> None:
    request = urllib.request.Request(URL, headers={"Authorization": token})
    try:
        urllib.request.urlopen(request, timeout=5)
    except urllib.error.HTTPError as exc:
        assert exc.code == 401, f"Expected 401, got {exc.code}"
    else:
        raise AssertionError("Unauthenticated MCP request was accepted")


async def main() -> None:
    wait_for_service()
    check_rejected("")
    check_rejected("Bearer incorrect")
    print("PASS: missing and incorrect bearer rejected (401)")

    authorization = (ROOT / "mcp-authorization").read_text(encoding="utf-8").strip()
    async with httpx.AsyncClient(headers={"Authorization": authorization}) as http_client:
        async with streamable_http_client(URL, http_client=http_client) as streams:
            async with ClientSession(streams[0], streams[1]) as session:
                await session.initialize()
                print("PASS: MCP initialize")
                result = await session.list_tools()
                names = {tool.name for tool in result.tools}
                missing = EXPECTED_TOOLS - names
                assert not missing, f"Missing MCP tools: {sorted(missing)}"
                (ROOT / "tools.json").write_text(
                    json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
                print(f"PASS: tools/list ({len(names)} tools)")
                status = await session.call_tool("flypig_status", {})
                assert not status.isError, status
                status_text = "\n".join(item.text for item in status.content if hasattr(item, "text"))
                assert '"status":"ok"' in status_text.replace(" ", ""), status_text
                print("PASS: flypig_status")


if __name__ == "__main__":
    asyncio.run(main())
