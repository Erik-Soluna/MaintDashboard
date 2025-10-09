# Clear Maintenance API Testing

## Endpoint
```
POST /core/api/clear-maintenance/
```

## Status
✅ Code deployed to GitHub  
⏳ Waiting for Docker container restart to pick up changes

---

## Test Commands

### 1. Dry Run (Safe - Preview Only)
```bash
curl -X POST https://dev.maintenance.errorlog.app/core/api/clear-maintenance/ \
  -d "dry_run=true" \
  -H "Content-Type: application/x-www-form-urlencoded"
```

**Expected Response:**
```json
{
  "success": true,
  "dry_run": true,
  "activities_deleted": 150,
  "schedules_deleted": 0,
  "message": "Dry run: Would delete 150 activities"
}
```

---

### 2. Clear Scheduled/Pending (Preserves History)
```bash
curl -X POST https://dev.maintenance.errorlog.app/core/api/clear-maintenance/ \
  -d "dry_run=false&clear_all=false" \
  -H "Content-Type: application/x-www-form-urlencoded"
```

**What it does:**
- Deletes activities with status: `scheduled` or `pending`
- ✅ Keeps: All completed activities (history)
- ✅ Keeps: All maintenance schedules
- ✅ Keeps: All equipment, users, locations

---

### 3. Clear ALL Activities
```bash
curl -X POST https://dev.maintenance.errorlog.app/core/api/clear-maintenance/ \
  -d "dry_run=false&clear_all=true" \
  -H "Content-Type: application/x-www-form-urlencoded"
```

**What it does:**
- Deletes ALL activities (scheduled, pending, completed, etc.)
- ✅ Keeps: All maintenance schedules
- ✅ Keeps: All equipment, users, locations

---

### 4. Nuclear Option (Clear Everything)
```bash
curl -X POST https://dev.maintenance.errorlog.app/core/api/clear-maintenance/ \
  -d "dry_run=false&clear_all=true&clear_schedules=true" \
  -H "Content-Type: application/x-www-form-urlencoded"
```

**What it does:**
- Deletes ALL activities
- Deletes ALL maintenance schedules
- ✅ Keeps: All equipment, users, locations

---

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `dry_run` | boolean | `true` | If true, only counts without deleting |
| `clear_all` | boolean | `false` | If true, clears all activities (including completed) |
| `clear_schedules` | boolean | `false` | If true, also clears maintenance schedules |

---

## Response Format

```json
{
  "success": true,
  "dry_run": false,
  "activities_deleted": 150,
  "schedules_deleted": 12,
  "message": "Successfully deleted 150 activities and 12 schedules"
}
```

---

## Security Notes

⚠️ **TEMPORARY:** This endpoint is currently unsecured for testing  
🔒 **TODO:** Add API key authentication before production  

The endpoint has a TODO comment:
```python
# TODO: Add API key authentication here
```

---

## How to Restart Container

If the endpoint returns 404, the container needs to restart to pick up the new code:

### Option 1: Portainer (Recommended)
1. Go to Portainer dashboard
2. Find your maintenance dashboard container
3. Click "Restart"

### Option 2: Docker Command
```bash
docker restart <container_name>
```

### Option 3: Wait for Webhook
If you have GitHub webhook configured, it should auto-deploy within a few minutes.

---

## Testing Workflow

```bash
# Step 1: Test with dry run first
curl -X POST https://dev.maintenance.errorlog.app/core/api/clear-maintenance/ \
  -d "dry_run=true"

# Output: "Would delete 150 activities"

# Step 2: If happy with preview, run for real
curl -X POST https://dev.maintenance.errorlog.app/core/api/clear-maintenance/ \
  -d "dry_run=false"

# Output: "Successfully deleted 150 activities"
```

---

## Common Issues

### 404 Not Found
- **Cause:** Container hasn't restarted yet
- **Fix:** Restart the Docker container

### CSRF Token Error
- **Note:** Endpoint is `@csrf_exempt` so this shouldn't happen
- **If it does:** Make sure you're using the `/core/api/clear-maintenance/` endpoint

### Permission Denied
- **Note:** Endpoint is currently unsecured for testing
- **If it happens:** Check that the `@login_required` decorator isn't active

---

## After API Keys Are Added

Future authentication will look like:

```bash
curl -X POST https://dev.maintenance.errorlog.app/core/api/clear-maintenance/ \
  -H "X-API-Key: your-secret-key-here" \
  -d "dry_run=false"
```

