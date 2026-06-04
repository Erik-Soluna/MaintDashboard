#!/usr/bin/env python3
"""
MCP server for the Maintenance Dashboard.

Wraps the read-only dynamic API (/api/v1/) so an AI agent can diagnose the
deployment: system health, open/critical issues, overdue maintenance, fleet
status, and ad-hoc queries against any reflected model.

Config (environment):
    MAINT_API_BASE   e.g. https://maintenance.errorlog.app   (no trailing /api/v1)
    MAINT_API_TOKEN  DRF token from `manage.py create_api_token`
    MAINT_API_VERIFY_TLS  "0" to disable TLS verification (default on)

Run:
    pip install -r requirements.txt
    MAINT_API_BASE=https://host MAINT_API_TOKEN=xxxx python server.py
"""

import os

import httpx
from mcp.server.fastmcp import FastMCP

API_BASE = os.environ.get("MAINT_API_BASE", "http://localhost:8000").rstrip("/")
API_TOKEN = os.environ.get("MAINT_API_TOKEN", "")
VERIFY_TLS = os.environ.get("MAINT_API_VERIFY_TLS", "1") != "0"
API_ROOT = f"{API_BASE}/api/v1"

mcp = FastMCP("maintenance-dashboard")


def _client() -> httpx.Client:
    headers = {"Accept": "application/json"}
    if API_TOKEN:
        headers["Authorization"] = f"Token {API_TOKEN}"
    return httpx.Client(base_url=API_ROOT, headers=headers, timeout=30.0, verify=VERIFY_TLS)


def _get(path: str, params: dict | None = None):
    """GET a path under /api/v1 and return parsed JSON (or an error dict)."""
    try:
        with _client() as c:
            resp = c.get(path, params=params or {})
        if resp.status_code == 401:
            return {"error": "Unauthorized — check MAINT_API_TOKEN."}
        if resp.status_code == 403:
            return {"error": "Forbidden — the token's account lacks diagnostics.read."}
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as e:
        return {"error": f"Request failed: {e}"}


def _post(path: str, json_body: dict | None = None):
    """POST a path under /api/v1 (privileged actions) and return parsed JSON."""
    try:
        with _client() as c:
            resp = c.post(path, json=json_body or {})
        if resp.status_code == 401:
            return {"error": "Unauthorized — check MAINT_API_TOKEN."}
        if resp.status_code == 403:
            return {"error": "Forbidden — the token's account lacks the required permission."}
        # 200/202/502 all carry a JSON body we want to surface
        try:
            return resp.json()
        except ValueError:
            return {"error": f"Unexpected response: {resp.status_code}"}
    except httpx.HTTPError as e:
        return {"error": f"Request failed: {e}"}


@mcp.tool()
def get_system_health() -> dict:
    """Comprehensive system health: database, cache, Celery worker/beat, email, system."""
    return _get("/diagnostics/health/")


@mcp.tool()
def get_diagnostics_summary() -> dict:
    """At-a-glance state: open/critical issue counts + samples, overdue maintenance,
    equipment-by-status, totals. Best first call to diagnose the deployment."""
    return _get("/diagnostics/summary/")


@mcp.tool()
def list_open_issues(critical_only: bool = False, limit: int = 50) -> dict:
    """List open / in-progress equipment issues. Set critical_only to filter to
    critical severity. Returns up to `limit` rows."""
    params = {"status": "open", "ordering": "-created_at", "page_size": min(limit, 500)}
    if critical_only:
        params["severity"] = "critical"
    return _get("/data/equipment/equipmentissue/", params)


@mcp.tool()
def overdue_maintenance(limit: int = 50) -> dict:
    """Maintenance activities that are overdue (scheduled end in the past, not done).
    Use get_diagnostics_summary for the canonical overdue count + sample."""
    summary = _get("/diagnostics/summary/")
    if isinstance(summary, dict) and "overdue_sample" in summary:
        return {
            "overdue_maintenance": summary.get("overdue_maintenance"),
            "sample": summary.get("overdue_sample", [])[:limit],
        }
    return summary


@mcp.tool()
def equipment_status() -> dict:
    """Equipment counts grouped by status, plus the fleet total."""
    summary = _get("/diagnostics/summary/")
    if isinstance(summary, dict) and "equipment_by_status" in summary:
        return {
            "equipment_total": summary.get("equipment_total"),
            "equipment_by_status": summary.get("equipment_by_status", {}),
        }
    return summary


@mcp.tool()
def redeploy_status() -> dict:
    """Whether a stack redeploy is configured (Portainer webhook set) + the stack name."""
    return _get("/actions/redeploy/")


@mcp.tool()
def trigger_redeploy() -> dict:
    """Trigger a Portainer GitOps stack redeploy (re-pull + recreate the stack).
    PRIVILEGED — the token's account needs diagnostics.deploy / admin. Uses the
    webhook configured on the dashboard's Webhook Settings page."""
    return _post("/actions/redeploy/")


@mcp.tool()
def list_models() -> dict:
    """List every model the API exposes, with field metadata and row counts.
    Use this to discover what `query_model` can target."""
    root = _get("/")
    if isinstance(root, dict) and "models" in root:
        return {"models": [
            {"key": m["key"], "count": m.get("count"),
             "fields": [f["name"] for f in m.get("fields", [])]}
            for m in root["models"]
        ]}
    return root


@mcp.tool()
def query_model(app: str, model: str, filters: dict | None = None,
                ordering: str = "", page_size: int = 25) -> dict:
    """Query any exposed model dynamically.

    app/model: from list_models() keys, e.g. app='equipment', model='equipment'.
    filters: exact-match field filters, e.g. {"status": "active"} or
             {"name__icontains": "transformer"}.
    ordering: field to sort by, prefix '-' for descending.
    page_size: max rows (capped at 500).
    """
    params = dict(filters or {})
    if ordering:
        params["ordering"] = ordering
    params["page_size"] = min(page_size, 500)
    return _get(f"/data/{app}/{model}/", params)


if __name__ == "__main__":
    mcp.run()
