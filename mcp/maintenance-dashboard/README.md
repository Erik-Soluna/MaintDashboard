# Maintenance Dashboard — MCP Server

An [MCP](https://modelcontextprotocol.io) server that lets an AI agent diagnose
the Maintenance Dashboard deployment through its **read-only** dynamic API
(`/api/v1/`). No write access.

## Tools

| Tool | Purpose |
| --- | --- |
| `get_system_health` | DB / cache / Celery worker+beat / email / system health |
| `get_diagnostics_summary` | Open + critical issues, overdue maintenance, equipment-by-status (best first call) |
| `list_open_issues(critical_only, limit)` | Open/in-progress equipment issues |
| `overdue_maintenance(limit)` | Overdue maintenance activities |
| `equipment_status()` | Fleet counts grouped by status |
| `list_models()` | Discover every model the API exposes + its fields |
| `query_model(app, model, filters, ordering, page_size)` | Ad-hoc query against any reflected model |
| `redeploy_status()` | Whether a Portainer stack redeploy is configured |
| `trigger_redeploy()` | **Privileged** — trigger a Portainer GitOps stack redeploy (needs `diagnostics.deploy`) |

## Setup

1. Provision a token on the server (web container):
   ```
   python manage.py create_api_token
   ```
   Copy the printed token.

2. Install deps:
   ```
   cd mcp/maintenance-dashboard
   pip install -r requirements.txt
   ```

3. Configure your MCP client. **Claude Desktop** (`claude_desktop_config.json`)
   or **Claude Code** (`.mcp.json` / `claude mcp add`):

   ```json
   {
     "mcpServers": {
       "maintenance-dashboard": {
         "command": "python",
         "args": ["/abs/path/to/mcp/maintenance-dashboard/server.py"],
         "env": {
           "MAINT_API_BASE": "https://maintenance.errorlog.app",
           "MAINT_API_TOKEN": "your-token-here"
         }
       }
     }
   }
   ```

   Claude Code one-liner:
   ```
   claude mcp add maintenance-dashboard \
     -e MAINT_API_BASE=https://maintenance.errorlog.app \
     -e MAINT_API_TOKEN=your-token \
     -- python /abs/path/to/mcp/maintenance-dashboard/server.py
   ```

## Security

- The token grants **read-only** access scoped by the `ai_diagnostics` role
  (`diagnostics.read` + view permissions). It cannot modify data.
- Keep the token out of git — use the client's `env` block or a local `.env`.
- Rotate with `python manage.py create_api_token --rotate`.
- For self-signed dev hosts only, set `MAINT_API_VERIFY_TLS=0`.
