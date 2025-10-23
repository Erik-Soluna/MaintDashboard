# Database Issues Fix Summary

## Issues Identified

1. **Missing `maintenance_maintenanceactivitytype` table**
   - Migration marked as applied but table doesn't exist
   - Caused by `--fake-initial` migrations that mark migrations as applied without creating tables

2. **Missing `celery-beat` command handling**
   - Docker containers using `command: ["celery-beat"]` but entrypoint script doesn't handle this
   - Results in "celery-beat: not found" error

3. **Pending migrations**
   - Models in `core`, `equipment`, and `events` apps have changes not reflected in migrations
   - Need to create new migration files

## Fixes Implemented

### 1. Fixed Docker Entrypoint Script (`scripts/deployment/docker-entrypoint.sh`)

**Added command handling for different services:**
```bash
# Handle different service commands
if [ "$1" = "web" ] || [ "$1" = "gunicorn" ]; then
    exec gunicorn --bind 0.0.0.0:8000 --workers 3 --timeout 120 maintenance_dashboard.wsgi:application
elif [ "$1" = "celery" ]; then
    exec celery -A maintenance_dashboard worker --loglevel=info
elif [ "$1" = "celery-beat" ]; then
    exec celery -A maintenance_dashboard beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
else
    # Default behavior for other commands
    exec "$@"
fi
```

**Added table verification function:**
- Checks for critical tables after migrations
- Automatically fixes missing tables by resetting problematic migrations
- Prevents the fake-initial issue from recurring

### 2. Created Missing Table Fix Script (`scripts/deployment/fix_missing_tables.py`)

**Features:**
- Detects when migrations are marked as applied but tables don't exist
- Automatically unapplies and reapplies problematic migrations
- Provides aggressive reset fallback for stubborn cases
- Verifies fixes were successful

### 3. Updated Dockerfile

**Added executable permissions for the fix script:**
```dockerfile
&& chmod +x /app/scripts/deployment/fix_missing_tables.py
```

## Root Cause Analysis

The issue occurs when:
1. Database initialization detects existing tables (like `core_userprofile`)
2. System assumes all migrations have been applied and runs `--fake-initial`
3. `--fake-initial` marks migrations as applied without checking if tables actually exist
4. Later operations fail because expected tables are missing

## Prevention

The updated entrypoint script now:
1. Verifies critical tables exist after any migration operation
2. Automatically fixes missing tables when detected
3. Provides detailed logging for debugging

## Testing

To test the fixes:
1. Rebuild Docker containers with the updated entrypoint script
2. The system should automatically detect and fix missing tables
3. Celery beat service should start correctly
4. All database operations should work properly

## Files Modified

1. `/workspace/scripts/deployment/docker-entrypoint.sh` - Added command handling and table verification
2. `/workspace/scripts/deployment/fix_missing_tables.py` - New fix script for missing tables  
3. `/workspace/fix_missing_tables.py` - Backup copy of fix script
4. `/workspace/Dockerfile` - Added executable permissions for fix script