"""Authenticated, loopback-only MCP adapter for the official FlyAI CLI."""

from __future__ import annotations

import asyncio
import contextlib
from datetime import date
import hmac
import json
import os
from pathlib import Path
import signal
from typing import Literal

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from starlette.responses import JSONResponse
import uvicorn


ROOT = Path(__file__).resolve().parent
CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
MCP_BIND_HOST = os.environ["MCP_BIND_HOST"]
MCP_PORT = int(os.environ["MCP_PORT"])
AUTHORIZATION = (ROOT / "mcp-authorization").read_text(encoding="utf-8").strip()
if not AUTHORIZATION.startswith("Bearer ") or len(AUTHORIZATION) < 40:
    raise RuntimeError("Missing or invalid local MCP bearer authorization")

CLI = Path(CONFIG["cli"])
if not CLI.is_file():
    raise RuntimeError(f"FlyAI CLI is missing: {CLI}")

server = FastMCP(
    CONFIG["name"],
    host=MCP_BIND_HOST,
    port=MCP_PORT,
    stateless_http=True,
    json_response=True,
)
semaphore = asyncio.Semaphore(CONFIG.get("max_concurrency", 3))

READ_ONLY = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)


def _clean_required(name: str, value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError(f"{name} must not be empty")
    if len(value) > 2_000 or "\0" in value:
        raise ValueError(f"{name} exceeds input limits")
    return value


def _clean_optional(name: str, value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    if len(value) > 2_000 or "\0" in value:
        raise ValueError(f"{name} exceeds input limits")
    return value


def _valid_date(name: str, value: str | None) -> str | None:
    value = _clean_optional(name, value)
    if value is None:
        return None
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{name} must use YYYY-MM-DD and be a real date") from exc
    return value


def _positive(name: str, value: float | int | None) -> float | int | None:
    if value is not None and value <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return value


def _hour(name: str, value: int | None) -> int | None:
    if value is not None and not 0 <= value <= 23:
        raise ValueError(f"{name} must be between 0 and 23")
    return value


def _option(arguments: list[str], flag: str, value: object | None) -> None:
    if value is not None and value != "":
        arguments.extend((flag, str(value)))


async def _read_limited(stream: asyncio.StreamReader, limit: int) -> bytes:
    chunks: list[bytes] = []
    size = 0
    while chunk := await stream.read(8192):
        size += len(chunk)
        if size > limit:
            raise ValueError("FlyAI CLI output exceeds the configured 4 MB limit")
        chunks.append(chunk)
    return b"".join(chunks)


async def run_cli(arguments: list[str], *, timeout: int | None = None) -> dict:
    if len(arguments) > 40 or any(len(value) > 2_000 or "\0" in value for value in arguments):
        raise ValueError("FlyAI CLI arguments exceed safety limits")

    async with semaphore:
        process = await asyncio.create_subprocess_exec(
            str(CLI),
            *arguments,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            start_new_session=True,
            env=os.environ.copy(),
        )
        stdout_task = asyncio.create_task(_read_limited(process.stdout, 4_000_000))
        stderr_task = asyncio.create_task(_read_limited(process.stderr, 256_000))
        wait_task = asyncio.create_task(process.wait())
        try:
            stdout_raw, stderr_raw, exit_code = await asyncio.wait_for(
                asyncio.gather(stdout_task, stderr_task, wait_task),
                timeout=timeout or CONFIG.get("timeout_seconds", 120),
            )
        except asyncio.TimeoutError as exc:
            raise RuntimeError("FlyAI request timed out; retry or narrow the query") from exc
        finally:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
            await process.wait()
            for task in (stdout_task, stderr_task, wait_task):
                task.cancel()
            await asyncio.gather(stdout_task, stderr_task, wait_task, return_exceptions=True)

    stdout = stdout_raw.decode("utf-8", errors="replace").strip()
    stderr = stderr_raw.decode("utf-8", errors="replace").strip()
    secret = os.environ.get("FLYAI_API_KEY")
    if secret:
        stdout = stdout.replace(secret, "[REDACTED]")
        stderr = stderr.replace(secret, "[REDACTED]")
    if exit_code:
        raise RuntimeError(f"FlyAI CLI exited {exit_code}: {stderr or stdout or 'no details'}")

    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"FlyAI CLI returned invalid JSON: {stderr or stdout[:500]}") from exc

    if isinstance(payload, dict):
        status = payload.get("status")
        if status not in (None, 0, "0"):
            raise RuntimeError(str(payload.get("message") or payload.get("error") or payload))
        if payload.get("ok") is False or payload.get("success") is False:
            raise RuntimeError(str(payload.get("error") or payload.get("message") or payload))
    return payload


def _transport_arguments(
    command: str,
    origin: str,
    destination: str | None,
    dep_date: str | None,
    dep_date_start: str | None,
    dep_date_end: str | None,
    back_date: str | None,
    back_date_start: str | None,
    back_date_end: str | None,
    journey_type: Literal[1, 2] | None,
    seat_class_name: str | None,
    transport_no: str | None,
    transfer_city: str | None,
    dep_hour_start: int | None,
    dep_hour_end: int | None,
    arr_hour_start: int | None,
    arr_hour_end: int | None,
    total_duration_hour: float | None,
    max_price: int | None,
    sort_type: Literal[1, 2, 3, 4, 5, 6, 7, 8] | None,
) -> list[str]:
    arguments = [command, "--origin", _clean_required("origin", origin)]
    values = {
        "--destination": _clean_optional("destination", destination),
        "--dep-date": _valid_date("dep_date", dep_date),
        "--dep-date-start": _valid_date("dep_date_start", dep_date_start),
        "--dep-date-end": _valid_date("dep_date_end", dep_date_end),
        "--back-date": _valid_date("back_date", back_date),
        "--back-date-start": _valid_date("back_date_start", back_date_start),
        "--back-date-end": _valid_date("back_date_end", back_date_end),
        "--journey-type": journey_type,
        "--seat-class-name": _clean_optional("seat_class_name", seat_class_name),
        "--transport-no": _clean_optional("transport_no", transport_no),
        "--transfer-city": _clean_optional("transfer_city", transfer_city),
        "--dep-hour-start": _hour("dep_hour_start", dep_hour_start),
        "--dep-hour-end": _hour("dep_hour_end", dep_hour_end),
        "--arr-hour-start": _hour("arr_hour_start", arr_hour_start),
        "--arr-hour-end": _hour("arr_hour_end", arr_hour_end),
        "--total-duration-hour": _positive("total_duration_hour", total_duration_hour),
        "--max-price": _positive("max_price", max_price),
        "--sort-type": sort_type,
    }
    for flag, value in values.items():
        _option(arguments, flag, value)
    return arguments


@server.tool(annotations=READ_ONLY)
async def flypig_status() -> dict:
    """Check the local FlyAI adapter and CLI configuration without revealing credentials."""
    package = json.loads(
        (ROOT.parent / "node_modules" / "@fly-ai" / "flyai-cli" / "package.json").read_text(
            encoding="utf-8"
        )
    )
    return {
        "status": "ok",
        "service": CONFIG["name"],
        "cli_version": package["version"],
        "api_key_configured": bool(os.environ.get("FLYAI_API_KEY")),
        "note": "The CLI can use its bundled default access; a personal API key is optional and recommended for enhanced quota/results.",
    }


@server.tool(annotations=READ_ONLY)
async def flypig_help(
    command: Literal[
        "all",
        "keyword-search",
        "ai-search",
        "search-flight",
        "search-train",
        "search-hotel",
        "search-poi",
        "search-marriott-hotel",
        "search-marriott-package",
    ] = "all",
) -> dict:
    """Show the exact help text from the installed FlyAI CLI."""
    arguments = ["--help"] if command == "all" else [command, "--help"]
    process = await asyncio.create_subprocess_exec(
        str(CLI),
        *arguments,
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=15)
    text = (stdout or stderr).decode("utf-8", errors="replace")
    return {"command": command, "help": text, "exit_code": process.returncode}


@server.tool(annotations=READ_ONLY)
async def flypig_keyword_search(query: str) -> dict:
    """Search FlyAI/Fliggy travel products by keywords. Useful for broad discovery across flights, hotels, tickets, tours, cruises, visas and connectivity products."""
    return await run_cli(["keyword-search", "--query", _clean_required("query", query)])


@server.tool(annotations=READ_ONLY)
async def flypig_ai_search(query: str) -> dict:
    """Run FlyAI semantic travel search with the complete natural-language request, including dates, party size, budget, baggage, timing and other constraints. Treat returned prices and availability as candidates and verify booking-critical details in the booking page."""
    return await run_cli(["ai-search", "--query", _clean_required("query", query)])


@server.tool(annotations=READ_ONLY)
async def flypig_search_flight(
    origin: str,
    destination: str | None = None,
    dep_date: str | None = None,
    dep_date_start: str | None = None,
    dep_date_end: str | None = None,
    back_date: str | None = None,
    back_date_start: str | None = None,
    back_date_end: str | None = None,
    journey_type: Literal[1, 2] | None = None,
    seat_class_name: str | None = None,
    transport_no: str | None = None,
    transfer_city: str | None = None,
    dep_hour_start: int | None = None,
    dep_hour_end: int | None = None,
    arr_hour_start: int | None = None,
    arr_hour_end: int | None = None,
    total_duration_hour: float | None = None,
    max_price: int | None = None,
    sort_type: Literal[1, 2, 3, 4, 5, 6, 7, 8] | None = None,
) -> dict:
    """Search domestic/international flight candidates. sort_type: 1 price-desc, 2 recommended, 3 price-asc, 4 duration-asc, 5 duration-desc, 6 early departure, 7 late departure, 8 direct-first. journey_type: 1 direct, 2 connecting. The CLI does not guarantee party-size inventory, baggage allowance, or fare rules; verify those on the booking page with Playwright before presenting a final choice."""
    arguments = _transport_arguments(
        "search-flight", origin, destination, dep_date, dep_date_start, dep_date_end,
        back_date, back_date_start, back_date_end, journey_type, seat_class_name,
        transport_no, transfer_city, dep_hour_start, dep_hour_end, arr_hour_start,
        arr_hour_end, total_duration_hour, max_price, sort_type,
    )
    return await run_cli(arguments)


@server.tool(annotations=READ_ONLY)
async def flypig_search_train(
    origin: str,
    destination: str | None = None,
    dep_date: str | None = None,
    dep_date_start: str | None = None,
    dep_date_end: str | None = None,
    back_date: str | None = None,
    back_date_start: str | None = None,
    back_date_end: str | None = None,
    journey_type: Literal[1, 2] | None = None,
    seat_class_name: str | None = None,
    transport_no: str | None = None,
    transfer_city: str | None = None,
    dep_hour_start: int | None = None,
    dep_hour_end: int | None = None,
    arr_hour_start: int | None = None,
    arr_hour_end: int | None = None,
    total_duration_hour: float | None = None,
    max_price: int | None = None,
    sort_type: Literal[1, 2, 3, 4, 5, 6, 7, 8] | None = None,
) -> dict:
    """Search train candidates with date, time, seat, transfer, duration, price and sorting filters. Verify final availability and ticket rules on the booking page."""
    arguments = _transport_arguments(
        "search-train", origin, destination, dep_date, dep_date_start, dep_date_end,
        back_date, back_date_start, back_date_end, journey_type, seat_class_name,
        transport_no, transfer_city, dep_hour_start, dep_hour_end, arr_hour_start,
        arr_hour_end, total_duration_hour, max_price, sort_type,
    )
    return await run_cli(arguments)


HotelSort = Literal["distance_asc", "rate_desc", "price_asc", "price_desc", "no_rank"]


@server.tool(annotations=READ_ONLY)
async def flypig_search_hotel(
    dest_name: str,
    key_words: str | None = None,
    poi_name: str | None = None,
    hotel_types: str | None = None,
    sort: HotelSort | None = None,
    check_in_date: str | None = None,
    check_out_date: str | None = None,
    hotel_stars: str | None = None,
    hotel_bed_types: str | None = None,
    max_price: int | None = None,
) -> dict:
    """Search hotel candidates by destination, dates, nearby POI, type, stars, bed type and price. Verify room inventory, occupancy, taxes, cancellation and final price on the booking page."""
    arguments = ["search-hotel", "--dest-name", _clean_required("dest_name", dest_name)]
    values = {
        "--key-words": _clean_optional("key_words", key_words),
        "--poi-name": _clean_optional("poi_name", poi_name),
        "--hotel-types": _clean_optional("hotel_types", hotel_types),
        "--sort": sort,
        "--check-in-date": _valid_date("check_in_date", check_in_date),
        "--check-out-date": _valid_date("check_out_date", check_out_date),
        "--hotel-stars": _clean_optional("hotel_stars", hotel_stars),
        "--hotel-bed-types": _clean_optional("hotel_bed_types", hotel_bed_types),
        "--max-price": _positive("max_price", max_price),
    }
    for flag, value in values.items():
        _option(arguments, flag, value)
    return await run_cli(arguments)


PoiCategory = Literal[
    "自然风光", "山湖田园", "森林丛林", "峡谷瀑布", "沙滩海岛", "沙漠草原",
    "人文古迹", "古镇古村", "历史古迹", "园林花园", "宗教场所", "公园乐园",
    "主题乐园", "水上乐园", "影视基地", "动物园", "植物园", "海洋馆",
    "体育场馆", "演出赛事", "剧院剧场", "博物馆", "纪念馆", "展览馆",
    "地标建筑", "市集", "文创街区", "城市观光", "户外活动", "滑雪", "漂流",
    "冲浪", "潜水", "露营", "温泉",
]


@server.tool(annotations=READ_ONLY)
async def flypig_search_poi(
    city_name: str,
    poi_level: Literal[1, 2, 3, 4, 5] | None = None,
    keyword: str | None = None,
    category: PoiCategory | None = None,
) -> dict:
    """Search Fliggy attractions and activities by city, attraction grade, keyword and category."""
    arguments = ["search-poi", "--city-name", _clean_required("city_name", city_name)]
    _option(arguments, "--poi-level", poi_level)
    _option(arguments, "--keyword", _clean_optional("keyword", keyword))
    _option(arguments, "--category", category)
    return await run_cli(arguments)


@server.tool(annotations=READ_ONLY)
async def flypig_search_marriott_hotel(
    dest_name: str,
    key_words: str | None = None,
    poi_name: str | None = None,
    hotel_bed_types: str | None = None,
    max_price: int | None = None,
    sort: HotelSort | None = None,
    check_in_date: str | None = None,
    check_out_date: str | None = None,
) -> dict:
    """Search Marriott Group hotel candidates by destination and optional stay preferences. Verify final room inventory, occupancy, taxes and cancellation terms on the booking page."""
    arguments = ["search-marriott-hotel", "--dest-name", _clean_required("dest_name", dest_name)]
    values = {
        "--key-words": _clean_optional("key_words", key_words),
        "--poi-name": _clean_optional("poi_name", poi_name),
        "--hotel-bed-types": _clean_optional("hotel_bed_types", hotel_bed_types),
        "--max-price": _positive("max_price", max_price),
        "--sort": sort,
        "--check-in-date": _valid_date("check_in_date", check_in_date),
        "--check-out-date": _valid_date("check_out_date", check_out_date),
    }
    for flag, value in values.items():
        _option(arguments, flag, value)
    return await run_cli(arguments)


@server.tool(annotations=READ_ONLY)
async def flypig_search_marriott_package(
    keyword: str | None = None,
    hotel_name: str | None = None,
    province_or_city: str | None = None,
    sort_type: Literal["price_asc", "price_desc"] | None = None,
) -> dict:
    """Search Marriott Group package products. At least one of keyword, hotel_name or province_or_city is required."""
    values = {
        "--keyword": _clean_optional("keyword", keyword),
        "--hotel-name": _clean_optional("hotel_name", hotel_name),
        "--province-or-city": _clean_optional("province_or_city", province_or_city),
    }
    if not any(values.values()):
        raise ValueError("Provide keyword, hotel_name or province_or_city")
    arguments = ["search-marriott-package"]
    for flag, value in values.items():
        _option(arguments, flag, value)
    _option(arguments, "--sort-type", sort_type)
    return await run_cli(arguments)


@server.custom_route("/healthz", methods=["GET"])
async def health(_request):
    return JSONResponse({"status": "ok", "service": CONFIG["name"]})


class BearerAuth:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["path"] != "/healthz":
            supplied = dict(scope.get("headers", [])).get(b"authorization", b"")
            if not hmac.compare_digest(supplied, AUTHORIZATION.encode("utf-8")):
                await JSONResponse(
                    {"error": "unauthorized"},
                    status_code=401,
                    headers={"WWW-Authenticate": "Bearer"},
                )(scope, receive, send)
                return
        await self.app(scope, receive, send)


if __name__ == "__main__":
    uvicorn.run(
        BearerAuth(server.streamable_http_app()),
        host=MCP_BIND_HOST,
        port=MCP_PORT,
        access_log=False,
    )
