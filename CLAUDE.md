# CLAUDE.md — mcp-swarmia

This file documents the project architecture and conventions for AI assistants working in this repository.

---

## Project purpose

`mcp-swarmia` is a **Model Context Protocol (MCP) server** written in Python. It wraps the [Swarmia Export API](https://help.swarmia.com/getting-started/integrations/data-export/export-api) and exposes each endpoint as an MCP tool, allowing Claude and other MCP-compatible clients to fetch engineering metrics in natural language.

---

## File structure

```
mcp-swarmia/
├── server.py          # MCP server — all logic lives here
├── requirements.txt   # Single external dependency: mcp>=1.0.0
├── README.md          # End-user setup and usage guide
└── CLAUDE.md          # This file — AI assistant context
```

---

## Architecture

The server is intentionally a **single-file implementation** to minimise complexity and dependencies.

### Key components in `server.py`

| Symbol | Purpose |
|--------|---------|
| `BASE_URL` | Root URL for the Swarmia API (`https://app.swarmia.com/api/v0`) |
| `app` | `mcp.server.Server` instance — the MCP application object |
| `fetch_swarmia(endpoint, params)` | Synchronous helper that builds a URL, sets the `Authorization` header, calls `urllib.request.urlopen`, and returns the CSV body as a string |
| `list_tools()` | MCP handler that declares all six tools and their JSON Schema input definitions |
| `_TOOL_ENDPOINTS` | Dict mapping tool names → API paths, used by the dispatcher |
| `call_tool(name, arguments)` | MCP handler that routes a tool call to `fetch_swarmia` and wraps the result in `TextContent` |
| `main()` | Async entry point; sets up stdio transport and runs the server loop |

### Transport

The server uses **stdio** transport (`mcp.server.stdio.stdio_server`). Claude Desktop and the Claude Code CLI both communicate with MCP servers over stdio, so no network setup is required.

### Authentication

The Swarmia API token is read from the `SWARMIA_API_TOKEN` environment variable at call time (not at startup), so the server can be started before the variable is set, and will surface a clear error message if it is missing when a tool is invoked.

---

## Swarmia API reference

**Base URL:** `https://app.swarmia.com/api/v0`

**Auth:** `Authorization: Bearer <token>` header (preferred over query param).

**Response format:** CSV, comma-delimited, with a header row.

### Endpoints and their MCP tools

| MCP tool | HTTP path | Notes |
|----------|-----------|-------|
| `get_pull_requests` | `GET /reports/pullRequests` | Accepts timeframe/date range + timezone |
| `get_dora_metrics` | `GET /reports/dora` | Also accepts `app` and `environment` filters |
| `get_investment_balance` | `GET /reports/investment` | `startDate`/`endDate` required (first/last day of month) |
| `get_capex` | `GET /reports/capex` | `startDate`/`endDate` required; same calendar year |
| `get_capex_employees` | `GET /reports/capex/employees` | `year` required |
| `get_fte` | `GET /reports/fte` | `month` required (YYYY-MM); optional `groupBy` and `customField` |

### Timeframe parameters

- **Preset:** `timeframe` = one of `last_7_days`, `last_14_days`, `last_30_days`, `last_60_days`, `last_90_days`, `last_180_days`, `last_365_days`
- **Custom:** `startDate` + `endDate` in `YYYY-MM-DD` format
- **Default:** last 7 days in UTC when neither is supplied

---

## Dependencies

| Package | Reason |
|---------|--------|
| `mcp>=1.0.0` | MCP server framework (Anthropic) |
| Python stdlib (`asyncio`, `urllib`, `os`) | HTTP requests and async runtime — no `requests` or `httpx` needed |

---

## Development guidelines

- **Do not add new files** unless strictly necessary. All server logic belongs in `server.py`.
- **Do not add HTTP client libraries** (`requests`, `httpx`, `aiohttp`). The stdlib `urllib.request` is sufficient and keeps the dependency footprint minimal.
- **Error handling:** tool errors are returned as `TextContent` strings starting with `"Error: …"` so that the LLM can relay the problem to the user rather than crashing.
- **Async vs sync:** `fetch_swarmia` is synchronous (blocking). This is acceptable because the Swarmia API calls are infrequent and short-lived, and the MCP server handles one request at a time over stdio.
- **Schema changes:** If the Swarmia API adds new endpoints or parameters, update both the `list_tools` return value and `_TOOL_ENDPOINTS` dict in `server.py`, then document the change in `README.md`.

---

## Running locally for testing

```bash
# Install dependencies
pip install -r requirements.txt

# Set token
export SWARMIA_API_TOKEN="your-token-here"

# Start the server (it will wait for MCP messages on stdin)
python server.py
```

To smoke-test without a real MCP client you can send a raw `initialize` JSON-RPC message to stdin, but it is easier to connect the server to Claude Desktop and ask a question.
