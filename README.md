# mcp-swarmia

A local [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server that exposes the [Swarmia Export API](https://help.swarmia.com/getting-started/integrations/data-export/export-api) as tools for AI assistants such as Claude.

Once connected, Claude (or any MCP-compatible client) can query your engineering metrics—pull request cycle times, DORA metrics, investment balance, CapEx reports, and FTE effort—in natural language without you having to write a single API call.

---

## Requirements

- Python 3.11+
- A Swarmia account with an API token (Settings → API tokens)
- `mcp` Python package (only external dependency)

---

## Installation

```bash
# 1. Clone or copy this directory
cd mcp-swarmia

# 2. Create and activate a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

---

## Configuration

Export your Swarmia API token as an environment variable:

```bash
export SWARMIA_API_TOKEN="your-token-here"
```

Alternatively, add it to a `.env` file and source it, or configure it in your MCP client settings (see below).

---

## Running the server

```bash
python server.py
```

The server communicates over **stdio** (standard input/output), which is the transport expected by Claude Desktop and most other MCP clients. You do not need to expose any network ports.

---

## Connecting to Claude Desktop

Add the following block to your Claude Desktop configuration file:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "swarmia": {
      "command": "/absolute/path/to/.venv/bin/python",
      "args": ["/absolute/path/to/mcp-swarmia/server.py"],
      "env": {
        "SWARMIA_API_TOKEN": "your-token-here"
      }
    }
  }
}
```

Replace the paths and token with your actual values, then restart Claude Desktop.

---

## Available tools

| Tool | Description | Required params |
|------|-------------|-----------------|
| `get_pull_requests` | Team-level PR metrics (cycle time, review time, size, …) | — |
| `get_dora_metrics` | Organisation DORA metrics (deployment frequency, lead time, CFR, MTTR) | — |
| `get_investment_balance` | Monthly FTE investment balance by category | `startDate`, `endDate` |
| `get_capex` | Software capitalisation report | `startDate`, `endDate` |
| `get_capex_employees` | Per-employee CapEx breakdown | `year` |
| `get_fte` | Monthly engineering effort (FTE) by author | `month` |

### Shared optional parameters

All time-series endpoints accept:

| Parameter | Description | Example |
|-----------|-------------|---------|
| `timeframe` | Preset window | `last_30_days` |
| `startDate` | Custom start (YYYY-MM-DD) | `2024-01-01` |
| `endDate` | Custom end (YYYY-MM-DD) | `2024-03-31` |
| `timezone` | tz database identifier | `America/New_York` |

`timeframe` and `startDate`/`endDate` are mutually exclusive. Defaults to `last_7_days` when neither is provided.

### DORA-specific parameters

| Parameter | Description |
|-----------|-------------|
| `app` | Filter by deployment application name |
| `environment` | Filter by deployment environment |

### FTE-specific parameters

| Parameter | Description | Values |
|-----------|-------------|--------|
| `groupBy` | How to group effort | `highestLevelIssue` (default), `lowestLevelIssue`, `customField` |
| `customField` | Jira field ID | Required when `groupBy=customField` |

---

## Response format

All tools return **CSV text** with a header row and comma delimiters, exactly as returned by the Swarmia API. No summary aggregations are added.

---

## Example prompts

After connecting the server to Claude, try:

- *"Show me our DORA metrics for the last 30 days."*
- *"What does our pull request cycle time look like for Q1 2024?"*
- *"Fetch the investment balance for January 2024."*
- *"Get the CapEx report for 2024."*
- *"Show FTE effort for March 2024, grouped by highest-level issue."*

---

## Security note

Swarmia recommends passing tokens via the `Authorization` header rather than query parameters, as some proxies log query strings. This server always uses the header approach.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `SWARMIA_API_TOKEN is not set` | Export the env var or add it to your MCP client config |
| `HTTP 401` | Token is invalid or expired — regenerate it in Swarmia |
| `HTTP 400` | Check that required parameters (e.g. `startDate`/`endDate`) are provided and in the correct format |
| Server not appearing in Claude | Verify the absolute paths in `claude_desktop_config.json` and restart Claude Desktop |
