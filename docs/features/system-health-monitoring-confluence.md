# System Health Monitoring & API Metrics

h1. Overview

The Maintenance Dashboard includes robust system health monitoring and API performance tracking to ensure reliability and fast troubleshooting. This page describes how health checks, Celery Beat heartbeat, and endpoint metrics work, and how to interpret and extend them.

h2. 1. System Health Panel

* *Location:* Accessible from the Settings page (`/core/settings/`).
* *Features:*
** Displays real-time status for:
*** *Database*
*** *Redis*
*** *Celery Beat* (scheduler)
*** *Disk Space*
** Shows recent health failures with timestamps and error messages.
** Allows admins to clear the health failure log.
** Color-coded status (Green = OK, Yellow = Warning, Red = Critical).
** Fully dark-mode compatible for easy readability.

h2. 2. Celery Beat Heartbeat

* *Purpose:* Ensures the Celery Beat scheduler is running and able to execute periodic tasks.
* *Implementation:*
** A dedicated Celery task (`core.tasks.celery_beat_heartbeat`) runs every minute.
** The task is automatically created and scheduled via a Django data migration.
** The health check logic:
*** Reports *OK* if a periodic task has run recently.
*** Warns if no periodic tasks have ever run or if the last run was too long ago.
*** Provides clear, actionable messages for troubleshooting.
* *Troubleshooting:*
** If you see a warning for Celery Beat, check that both the Beat and Worker containers are running and healthy.
** The heartbeat task is visible in Django admin under *Periodic Tasks*.

h2. 3. API Endpoint Metrics

* *API:* `/core/api/endpoint-metrics/`
* *What it does:*
** Tracks every API endpoint’s usage, response time, and error count.
** Returns a JSON object with:
*** `total_requests`
*** `total_time`
*** `error_count`
*** `last_request`
*** `avg_response_time`
* *Example Output:*
{code:json}
{
  "GET:/maintenance/activities/": {
    "total_requests": 2,
    "total_time": 0.22,
    "error_count": 0,
    "last_request": "2025-07-13T09:19:44.180867+00:00",
    "avg_response_time": 0.11
  },
  ...
}
{code}
* *Usage:*
** Use this endpoint to monitor API performance, detect slow endpoints, and spot error trends.

h2. 4. Dark Mode & UI Consistency

* The System Health panel and all modals are styled for high contrast and readability in dark mode.
* If you don’t see the latest styles, force-refresh your browser (`Ctrl+F5`).

h2. 5. Troubleshooting

* *Database errors:*
** If you see missing columns or tables, ensure all migrations are applied (`python manage.py migrate`).
* *Celery Beat warnings:*
** Make sure both Celery Beat and Worker containers are running. The heartbeat task should be enabled and scheduled.
* *Clear Logs button fails:*
** Ensure the backend has write permissions to the health log file and that CSRF tokens are correctly set up in the frontend.

h2. 6. Extending

* Add new health checks by editing `core/views.py` in the `health_check` function.
* Add new periodic tasks in Django admin or via migrations.
* Customize endpoint metrics by extending the middleware or API logic.

*For more details, see:*
* `core/views.py` (health check logic)
* `core/tasks.py` (heartbeat task)
* `core/migrations/0006_create_celery_beat_heartbeat.py` (auto-create heartbeat)
* `static/css/custom.css` (dark mode styles) 