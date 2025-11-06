# Database Initialization Fix

## Problem
When initializing from scratch, the application containers (web, celery, celery-beat) were failing with:
```
FATAL: password authentication failed for user "maintenance_user"
DETAIL: Role "maintenance_user" does not exist.
```

This happened because:
1. PostgreSQL container initializes with the default `postgres` superuser
2. Application containers try to connect using `maintenance_user` which doesn't exist yet
3. The entrypoint script was trying to connect with `maintenance_user` before ensuring it exists

## Solution
Updated the `docker-entrypoint.sh` script to:
1. **Wait for PostgreSQL server** using the `postgres` superuser
2. **Create the `maintenance_user`** if it doesn't exist (using `postgres` superuser)
3. **Create the database** if it doesn't exist
4. **Grant necessary privileges** to `maintenance_user`
5. **Wait for database connection** using `maintenance_user`
6. **Run Django migrations and initialization**

## Changes Made

### 1. `scripts/deployment/docker-entrypoint.sh`
- Added `wait_for_postgres_server()` function to wait for PostgreSQL using superuser
- Added `ensure_database_user()` function to create `maintenance_user` if needed
- Added `ensure_database()` function to create database and grant privileges
- Updated `main()` function to call these functions in the correct order
- Added support for cases where `DB_USER` matches `POSTGRES_USER` (dev environment)

### 2. `portainer-stack.yml` (Production)
- Added `POSTGRES_USER` environment variable to web, celery, and celery-beat services
- Ensures all services can create the database user if needed

### 3. `portainer-stack-dev.yml` (Development)
- Added `POSTGRES_USER` environment variable to web-dev, celery-dev, and celery-beat-dev services
- Set to use `DB_USER` value (which is `maintenance_user_dev` in dev environment)

## How It Works

### Production Environment
1. PostgreSQL container starts with `POSTGRES_USER=postgres`
2. Application containers connect as `postgres` to create `maintenance_user`
3. Database is created and `maintenance_user` is granted privileges
4. Application connects using `maintenance_user` for normal operations

### Development Environment
1. PostgreSQL container starts with `POSTGRES_USER=maintenance_user_dev`
2. Since `DB_USER` matches `POSTGRES_USER`, user creation is skipped (already exists)
3. Database is created and privileges are granted
4. Application connects using `maintenance_user_dev`

## Testing

To test the fix with a fresh database:

1. **Stop all containers**
2. **Remove the database volume** (if testing locally):
   ```bash
   docker volume rm maintenance_postgres_data
   ```

3. **Redeploy the stack** in Portainer

4. **Monitor the logs** - you should see:
   ```
   [INFO] ⏳ Waiting for PostgreSQL server to be ready...
   [SUCCESS] ✅ PostgreSQL server ready
   [INFO] 🔧 Ensuring database user 'maintenance_user' exists...
   [INFO] 👤 Creating user 'maintenance_user'...
   [SUCCESS] ✅ User 'maintenance_user' created successfully
   [INFO] 🔧 Ensuring database 'maintenance_dashboard_prod' exists...
   [SUCCESS] ✅ Database 'maintenance_dashboard_prod' created successfully
   [SUCCESS] ✅ Ready to serve
   ```

## Environment Variables

The following environment variables are now required/used:

- `POSTGRES_USER` - PostgreSQL superuser (default: `postgres`)
- `POSTGRES_PASSWORD` - PostgreSQL superuser password
- `DB_USER` - Application database user (default: `maintenance_user`)
- `DB_PASSWORD` - Application database user password
- `DB_NAME` - Database name (default: `maintenance_dashboard_prod`)
- `DB_HOST` - Database host (default: `db`)
- `DB_PORT` - Database port (default: `5432`)

## Notes

- The fix is backward compatible - if the database and user already exist, the script will skip creation
- The script handles both production (separate user) and development (same user) configurations
- All database operations use proper error handling and will exit with clear error messages if something fails

