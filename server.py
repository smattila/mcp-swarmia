#!/usr/bin/env python3
"""Swarmia Export API MCP Server.

Exposes Swarmia's Export API endpoints as MCP tools so that AI assistants
(e.g. Claude) can query engineering metrics directly.

Authentication:
    Set the SWARMIA_API_TOKEN environment variable to your Swarmia API token.

Usage:
    python server.py
"""

import asyncio
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server

BASE_URL = "https://app.swarmia.com/api/v0"

app = Server("swarmia-export-api")


def fetch_swarmia(endpoint: str, params: dict[str, Any]) -> str:
    """Make an authenticated GET request to the Swarmia Export API.

    Args:
        endpoint: API path, e.g. "/reports/pullRequests".
        params: Query parameters; None values are stripped automatically.

    Returns:
        Raw CSV response body as a string.

    Raises:
        ValueError: If SWARMIA_API_TOKEN is not set.
        RuntimeError: If the API returns an HTTP error.
    """
    token = os.environ.get("SWARMIA_API_TOKEN")
    if not token:
        raise ValueError(
            "SWARMIA_API_TOKEN environment variable is not set. "
            "Create an API token in Swarmia under Settings → API tokens."
        )

    clean_params = {k: str(v) for k, v in params.items() if v is not None}
    query_string = urllib.parse.urlencode(clean_params)
    url = f"{BASE_URL}{endpoint}?{query_string}" if query_string else f"{BASE_URL}{endpoint}"

    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}"},
    )

    try:
        with urllib.request.urlopen(req) as response:
            return response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        raise RuntimeError(f"HTTP {exc.code} from Swarmia API: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error reaching Swarmia API: {exc.reason}") from exc


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

_TIMEFRAME_ENUM = [
    "last_7_days",
    "last_14_days",
    "last_30_days",
    "last_60_days",
    "last_90_days",
    "last_180_days",
    "last_365_days",
]

_TIMEFRAME_PROPS = {
    "timeframe": {
        "type": "string",
        "description": (
            "Preset timeframe. One of: last_7_days, last_14_days, last_30_days, "
            "last_60_days, last_90_days, last_180_days, last_365_days. "
            "Mutually exclusive with startDate/endDate."
        ),
        "enum": _TIMEFRAME_ENUM,
    },
    "startDate": {
        "type": "string",
        "description": "Start date in YYYY-MM-DD format (inclusive). Use with endDate.",
    },
    "endDate": {
        "type": "string",
        "description": "End date in YYYY-MM-DD format (inclusive). Use with startDate.",
    },
    "timezone": {
        "type": "string",
        "description": (
            "Timezone for date aggregation using tz database identifiers "
            "(e.g. America/New_York). Defaults to UTC."
        ),
    },
}


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="get_pull_requests",
            description=(
                "Fetch team-level pull request metrics from Swarmia. "
                "Returns CSV data with PR cycle time, review time, size and other metrics."
            ),
            inputSchema={
                "type": "object",
                "properties": _TIMEFRAME_PROPS,
            },
        ),
        types.Tool(
            name="get_dora_metrics",
            description=(
                "Fetch organisation-level DORA metrics from Swarmia (deployment frequency, "
                "lead time for changes, change failure rate, mean time to restore). "
                "Returns CSV data."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    **_TIMEFRAME_PROPS,
                    "app": {
                        "type": "string",
                        "description": "Deployment application name(s) to filter by.",
                    },
                    "environment": {
                        "type": "string",
                        "description": "Deployment environment(s) to filter by.",
                    },
                },
            },
        ),
        types.Tool(
            name="get_investment_balance",
            description=(
                "Fetch monthly FTE investment balance from Swarmia showing how engineering "
                "effort is distributed across investment categories. "
                "Requires startDate set to the first day of a month and endDate to the last "
                "day of a month. Data is generated on the 10th of the following month. "
                "Returns CSV data."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "startDate": {
                        "type": "string",
                        "description": "First day of the month range in YYYY-MM-DD format.",
                    },
                    "endDate": {
                        "type": "string",
                        "description": "Last day of the month range in YYYY-MM-DD format.",
                    },
                    "timezone": _TIMEFRAME_PROPS["timezone"],
                },
                "required": ["startDate", "endDate"],
            },
        ),
        types.Tool(
            name="get_capex",
            description=(
                "Fetch the software capitalisation (CapEx) report from Swarmia. "
                "startDate and endDate must fall within the same calendar year. "
                "Returns CSV data."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "startDate": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format (same year as endDate).",
                    },
                    "endDate": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format (same year as startDate).",
                    },
                    "timezone": _TIMEFRAME_PROPS["timezone"],
                },
                "required": ["startDate", "endDate"],
            },
        ),
        types.Tool(
            name="get_capex_employees",
            description=(
                "Fetch the capitalisation employee breakdown from Swarmia for a given year. "
                "Returns CSV data with per-employee CapEx allocation."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "year": {
                        "type": "integer",
                        "description": "Four-digit calendar year (e.g. 2024).",
                    },
                },
                "required": ["year"],
            },
        ),
        types.Tool(
            name="get_fte",
            description=(
                "Fetch monthly engineering effort (FTE) by author from Swarmia. "
                "Returns CSV data broken down by issue hierarchy level or custom Jira field."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "month": {
                        "type": "string",
                        "description": "Month to fetch data for in YYYY-MM format (e.g. 2024-03).",
                    },
                    "customField": {
                        "type": "string",
                        "description": "Optional Jira field ID used when groupBy is 'customField'.",
                    },
                    "groupBy": {
                        "type": "string",
                        "description": (
                            "How to group the effort data. "
                            "One of: highestLevelIssue (default), lowestLevelIssue, customField."
                        ),
                        "enum": ["highestLevelIssue", "lowestLevelIssue", "customField"],
                    },
                    "timezone": _TIMEFRAME_PROPS["timezone"],
                },
                "required": ["month"],
            },
        ),
    ]


# ---------------------------------------------------------------------------
# Tool dispatch
# ---------------------------------------------------------------------------

_TOOL_ENDPOINTS: dict[str, str] = {
    "get_pull_requests": "/reports/pullRequests",
    "get_dora_metrics": "/reports/dora",
    "get_investment_balance": "/reports/investment",
    "get_capex": "/reports/capex",
    "get_capex_employees": "/reports/capex/employees",
    "get_fte": "/reports/fte",
}


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
    endpoint = _TOOL_ENDPOINTS.get(name)
    if endpoint is None:
        return [types.TextContent(type="text", text=f"Error: unknown tool '{name}'")]

    try:
        csv_data = fetch_swarmia(endpoint, arguments)
        return [types.TextContent(type="text", text=csv_data)]
    except (ValueError, RuntimeError) as exc:
        return [types.TextContent(type="text", text=f"Error: {exc}")]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
