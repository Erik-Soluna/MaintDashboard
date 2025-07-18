# Database Configuration Fix

## Issue
The Docker container initialization was failing with the following error:
```
❌ Database initialization failed: invalid dsn: invalid connection option "CONN_MAX_AGE"
```

## Root Cause
The issue was in the Django database configuration in `maintenance_dashboard/settings.py`. The `CONN_MAX_AGE` parameter was incorrectly placed inside the `OPTIONS` dictionary:

```python
# INCORRECT Configuration
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='maintenance_dashboard'),
        'USER': config('DB_USER', default='postgres'),
        'PASSWORD': config('DB_PASSWORD', default='postgres'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
        'OPTIONS': {
            'MAX_CONNS': 20,
            'CONN_MAX_AGE': 300,  # ❌ WRONG: This is not a PostgreSQL option
        },
    }
}
```

## Problem Explanation
- The `OPTIONS` dictionary in Django's database configuration is meant for database-specific connection options that are passed directly to the database driver (psycopg2 for PostgreSQL)
- `CONN_MAX_AGE` is a Django-specific parameter that controls connection reuse, not a PostgreSQL connection option
- `MAX_CONNS` is also not a valid PostgreSQL connection option
- These parameters were being passed to the PostgreSQL driver, causing the "invalid connection option" error

## Solution
Fixed the configuration by moving `CONN_MAX_AGE` to the top level of the database configuration:

```python
# CORRECT Configuration
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='maintenance_dashboard'),
        'USER': config('DB_USER', default='postgres'),
        'PASSWORD': config('DB_PASSWORD', default='postgres'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
        'CONN_MAX_AGE': 300,  # ✅ CORRECT: Django connection pooling setting
        'OPTIONS': {
            # PostgreSQL-specific connection options can go here
        },
    }
}
```

## Files Modified
1. **`maintenance_dashboard/settings.py`** - Fixed the database configuration
2. **`docs/database/setup.md`** - Updated documentation with correct configuration example

## Key Changes
- Moved `CONN_MAX_AGE` from `OPTIONS` to the top level of database configuration
- Removed invalid `MAX_CONNS` parameter from `OPTIONS`
- Added comments explaining the correct usage
- Updated documentation to reflect the correct configuration

## Result
The database initialization should now work correctly without the "invalid connection option" error. The Django application will be able to connect to PostgreSQL successfully with proper connection pooling enabled.

## How Connection Pooling Works
- `CONN_MAX_AGE`: Django-specific setting that controls how long database connections are reused (in seconds)
- When set to 300 (5 minutes), Django will reuse the same database connection for up to 5 minutes before creating a new one
- This reduces the overhead of creating new database connections for every request

## Testing
After applying this fix, the Docker container should initialize successfully without database connection errors. The application will maintain proper connection pooling while avoiding invalid PostgreSQL connection options.