# AI Agent Access — remote use & diagnostics (plan)

Status: **proposed (plan only)**

Goal: let an AI assistant query the dashboard remotely to **diagnose issues** (system
health, errors, overdue maintenance, open equipment issues) and, later, take **safe
actions** (e.g. log an issue, acknowledge) — without handing it a human admin login.

## What already exists (building blocks)
- **System Health API** — `comprehensive_health_check` / `health_check_api`, `database_stats_api` (DB, cache, Celery, email, metrics).
- **API Explorer** + assorted `/api/*` JSON endpoints (equipment, locations, roles, activities).
- **Issues** model + `issues_list` (open/critical, per equipment) and **Maintenance** overdue/upcoming.
- **Docker logs** view + Portainer integration (container-level diagnosis).
- **RBAC** (roles/permissions) — can scope exactly what an agent may see/do.
- Request/error logging (`core/logging_utils`).

## Recommended approach: token-scoped read API + an MCP server
1. **Service account + token auth.** Add a dedicated `ai-agent` user bound to a new
   **read-only "Diagnostics" role** (site_map.read, maintenance.view, issues.view,
   reports.view, a new `diagnostics.read`). Issue an API token (DRF TokenAuthentication
   or a signed key in the Portainer env). No human/admin credentials shared.
2. **Consolidated diagnostics endpoint(s)** (read-only, token-auth, RBAC-checked):
   - `GET /api/diagnostics/health` — the comprehensive health payload.
   - `GET /api/diagnostics/summary` — open/critical issues, overdue maintenance, equipment by status, recent errors (last N log lines).
   - Reuse existing querysets; just expose JSON + token auth.
3. **MCP server** (`mcp/maintenance-dashboard`) wrapping those endpoints as tools
   (`get_system_health`, `list_open_issues`, `overdue_maintenance`, `equipment_status`,
   `recent_errors`). Any Claude session can then diagnose by calling tools — fits the
   current Claude-in-the-loop workflow and is far more robust than UI scraping.
4. **Phase 2 — safe writes** (opt-in): allow the agent to *log an issue* or *add a note*
   via the same token, gated by an explicit write permission on its role. Everything the
   agent does is audit-logged (actor = `ai-agent`).

## Alternatives (and why not, to start)
- **Browser automation** (Playwright / Claude-in-Chrome driving the real UI): literally
  "uses the website," but brittle, slow, and needs a logged-in session. Use only if a
  task truly requires the UI; prefer API/MCP for diagnostics.
- **Open/unauthenticated diagnostics**: never — must be token + RBAC scoped.

## Security
- Dedicated, least-privilege service account; **read-only first**.
- Token in Portainer env (never in git); rotate-able; rate-limit the endpoints.
- All agent actions audit-logged; writes behind an explicit permission.
- Ties into the recent RBAC hardening — the agent simply gets a narrow role.

## Open questions for Erik
- Diagnose-only to start, or also allow safe writes (log issue / acknowledge)?
- Delivery: an **MCP server** (best for a Claude workflow) or a plain **REST token API**
  the agent calls directly?
- Token auth via DRF tokens, or a simple signed `X-API-Key` env secret?
- Should "recent errors" expose log tails (and how much), given they can contain data?
