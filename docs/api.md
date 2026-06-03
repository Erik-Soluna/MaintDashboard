# Dynamic API (`/api/v1/`)

A read-only, **model-introspecting** REST API (DRF). It reflects the live models
in the `core`, `equipment`, `maintenance`, and `events` apps, so it never goes
stale as the schema changes. Built for the AI diagnostics agent and the API Explorer.

## Auth

Token auth (DRF `TokenAuthentication`) or a logged-in session.

```
Authorization: Token <key>
```

Provision the service account + token (run in the web container):

```
python manage.py create_api_token            # create/show token for "ai-agent"
python manage.py create_api_token --rotate   # revoke + reissue
```

Store the token in the Portainer/MCP env — **never commit it**.

Access requires `diagnostics.read` (granted by the `ai_diagnostics` role) or
`administration.read`, or staff/superuser. Rate-limited to 600 req/hour/user.

## Endpoints

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/v1/` | Self-describing index: every exposed model, its fields, row count, and list URL. |
| GET | `/api/v1/data/<app>/<model>/` | Paginated list. Filter with `?<field>=<value>` (supports `field__lookup`), sort with `?ordering=<field>` (`-` for desc), `?page_size=N` (max 500). |
| GET | `/api/v1/data/<app>/<model>/<pk>/` | Single record. |
| GET | `/api/v1/diagnostics/health/` | Comprehensive system health (db, cache, celery worker/beat, email, system). |
| GET | `/api/v1/diagnostics/summary/` | Open/critical issues, overdue maintenance, equipment-by-status. |

Every record includes a `display` field (the model's `__str__`) for readability.

## Safety

- **Read-only.** No write methods are exposed by this API.
- Only the four domain apps are reflected; `auth`/`sessions`/`admin`/`authtoken` are never exposed.
- Models holding secrets are denylisted (`PortainerConfig`); fields whose names
  contain `password`/`secret`/`token`/`api_key`/`webhook_secret`/etc. are stripped
  from output as defence in depth.
