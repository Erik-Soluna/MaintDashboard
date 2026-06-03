# Slack Integration — Implementation Plan

Status: **proposed (plan only)** · Relates to SSDEV-26 (issue reporting / no-login reporting)

## Goal
Let the team report and track equipment issues through Slack, and (optionally) receive
maintenance alerts in Slack. Slack becomes the low-friction "no-login issue reporting"
channel referenced in SSDEV-26, on top of the in-app Issues tab already shipped.

## Directions
1. **Inbound (Slack → app):** create an `EquipmentIssue` from Slack.
   - **Slash command** `/report-issue` opens a modal (equipment picker + severity +
     description) → submit creates the issue. Cleanest UX.
   - Or **message shortcut** / a monitored channel where a posted message becomes an issue.
2. **Outbound (app → Slack):** push notifications to a channel.
   - New issue logged (esp. critical), maintenance overdue/due-soon, activity completed.
   - Sent from the existing Celery reminder tasks + issue post_save signal.

## Slack app setup (one-time, done by Erik)
Create a Slack app at api.slack.com/apps for the workspace and capture:
- **Bot token** `xoxb-…` (scopes: `commands`, `chat:write`, `users:read`; `chat:write` to the
  target channel; add `views:*` if using modals).
- **Signing secret** (to verify inbound requests).
- (Outbound-only alternative) an **Incoming Webhook URL** for one channel — simplest, no bot.

These go in the Portainer stack env (never in git):
`SLACK_BOT_TOKEN`, `SLACK_SIGNING_SECRET`, `SLACK_ALERT_CHANNEL` (and/or `SLACK_WEBHOOK_URL`).

## App-side design (Django)
New app/module `integrations/slack/` (or extend `events`):
- **URLs** (public; the app is already reachable at maintenance.errorlog.app):
  - `POST /integrations/slack/command/` — slash command handler.
  - `POST /integrations/slack/interactivity/` — modal submissions / interactive payloads.
  - (Events API `POST /integrations/slack/events/` only if monitoring channel messages.)
- **Security (required):** verify every inbound request with the Slack **signing secret**
  (HMAC of timestamp + raw body, 5-min replay window). Reject otherwise. These endpoints are
  CSRF-exempt (Slack can't send a CSRF token) but signature-verified instead.
- **Inbound flow:** slash command → `views.open` a modal (block kit: external-select for
  equipment by name/asset-tag, severity select, description) → on submit, resolve equipment,
  `EquipmentIssue.objects.create(...)`, map the Slack user to a Django user if possible (else
  record the Slack display name in the description / a new `reported_via`+`reporter_name`
  field), reply with the created issue link.
- **Equipment resolution:** Slack users won't know IDs. Use an external-select backed by a
  search endpoint over `Equipment` (name / asset_tag), reusing the same query as the equipment
  list search. Fallback: free-text + a later "assign to equipment" step in-app.
- **Outbound flow:** a thin `notify_slack(text, blocks=None, channel=…)` helper using
  `chat.postMessage` (bot token) or the incoming-webhook URL. Call it from:
  - `EquipmentIssue` post_save (new / critical), and
  - the existing reminder Celery tasks (overdue / due-soon).
  Make it best-effort (never break the request/task if Slack is down).

## Data model touchpoints
- Optional `EquipmentIssue.reported_via` (`web` / `slack`) and `reporter_name` for
  attribution when the reporter has no Django account (supports true no-login reporting).
- No other schema changes required.

## Phasing (each its own PR, dev → prod)
1. **Outbound alerts** (smallest): `notify_slack` helper + webhook/bot token + wire to issue
   post_save and reminder tasks. Immediate value, no inbound security surface.
2. **Inbound slash command + modal**: signature verification, `/report-issue` → modal →
   `EquipmentIssue`. Covers the no-login reporting ask.
3. **Polish**: equipment external-select search, Slack↔Django user mapping, threaded replies,
   per-event channel routing, optional channel-message monitoring.

## Open questions for Erik
- Which workspace + target channel(s)? One alert channel, or per-site?
- Bot (full inbound+outbound) or just an incoming webhook (outbound only) to start?
- Who can report via Slack — anyone in the workspace, or a specific channel/usergroup?
- Map Slack users to existing Django accounts, or treat all Slack reports as "external"?
- Which events should alert: new issues only, critical only, overdue maintenance, completions?

## Notes
- The Slack tools available in the Claude Code session are for assistant use, not the app
  runtime — the app needs its own Slack app/bot as above.
- Keep all tokens in Portainer env; the settings module already fails loud on missing
  required secrets, so add these as optional (feature-flag the integration off when unset).
