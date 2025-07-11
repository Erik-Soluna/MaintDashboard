# Database Connection Fix for Docker/Portainer Deployment

## Problem Description

You're experiencing this error when your application starts:
```
❌ Database initialization failed: connection to server at "db" (172.18.0.2), port 5432 failed: FATAL: database "maintenance_dashboard" does not exist
```

## Root Cause

The issue occurs because:
1. **PostgreSQL container is running** (shows as "healthy" in Portainer)
2. **Database is not created** - The `POSTGRES_DB` environment variable only creates the database on the **first run** when the data directory is empty
3. **Volume persistence** - If the PostgreSQL volume contains data from previous runs, the database creation is skipped

## Solutions (Choose One)

### 🚀 Solution 1: Quick Fix - Create Database Manually

**Step 1:** Connect to your PostgreSQL container and create the database:
```bash
docker exec -it slnh-maintenance-db-1 psql -U postgres -c "CREATE DATABASE maintenance_dashboard;"
```

**Step 2:** Restart your web container:
```bash
docker restart slnh-maintenance-web-1
```

**Step 3:** Check the logs in Portainer to verify the initialization completed.

---

### 🛠️ Solution 2: Use the Fix Script

I've created a script that automates the database creation process:

```bash
python3 fix_database.py
```

This script will:
- Check if containers are running
- Wait for PostgreSQL to be ready
- Create the database if it doesn't exist
- Restart the web container
- Provide detailed status updates

---

### 🔄 Solution 3: Reset PostgreSQL Volume (Nuclear Option)

If the above solutions don't work, you can completely reset the PostgreSQL volume:

**Step 1:** Stop the stack in Portainer (click "Stop" button)

**Step 2:** Remove the PostgreSQL volume:
```bash
docker volume rm slnh-maintenance_postgres_data
```

**Step 3:** Start the stack again in Portainer
- This will recreate the volume from scratch
- The `POSTGRES_DB` environment variable will create the database automatically

---

## Manual Database Creation Commands

If you prefer to do it manually, here are the exact commands:

### Check if database exists:
```bash
docker exec slnh-maintenance-db-1 psql -U postgres -t -c "SELECT 1 FROM pg_database WHERE datname='maintenance_dashboard';"
```

### Create database:
```bash
docker exec slnh-maintenance-db-1 psql -U postgres -c "CREATE DATABASE maintenance_dashboard;"
```

### Verify database was created:
```bash
docker exec slnh-maintenance-db-1 psql -U postgres -l | grep maintenance_dashboard
```

---

## Why This Happens

### Docker PostgreSQL Initialization Process

1. **First Run**: When PostgreSQL container starts with an empty data directory:
   - `POSTGRES_DB` environment variable creates the database
   - `POSTGRES_USER` and `POSTGRES_PASSWORD` are configured
   - Initialization completes successfully

2. **Subsequent Runs**: When the container restarts with existing data:
   - PostgreSQL uses the existing data directory
   - Environment variables are ignored
   - No new database creation happens

### Volume Persistence

Your `portainer-stack.yml` includes:
```yaml
volumes:
  - postgres_data:/var/lib/postgresql/data/
```

This volume persists between container restarts, which is good for data persistence but can cause initialization issues.

---

## Prevention for Future

To prevent this issue in the future:

### Option 1: Use Init Script (Recommended)

Create an initialization script that runs on every container start:

```bash
# Add to your Dockerfile or docker-compose
COPY init-db.sh /docker-entrypoint-initdb.d/
```

### Option 2: Database Creation Check

Add a database creation check to your application startup:

```python
# In your Django management command or startup script
def ensure_database_exists():
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
    
    conn = psycopg2.connect(
        host='db',
        user='postgres',
        password='postgres',
        database='postgres'  # Connect to default database
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    
    # Check if database exists
    cur.execute("SELECT 1 FROM pg_database WHERE datname='maintenance_dashboard'")
    exists = cur.fetchone()
    
    if not exists:
        cur.execute("CREATE DATABASE maintenance_dashboard")
        print("Database 'maintenance_dashboard' created")
    
    cur.close()
    conn.close()
```

---

## Troubleshooting

### If containers are not starting:
```bash
# Check container logs
docker logs slnh-maintenance-db-1
docker logs slnh-maintenance-web-1

# Check container status
docker ps -a --filter name=slnh-maintenance
```

### If PostgreSQL is not ready:
```bash
# Check PostgreSQL status
docker exec slnh-maintenance-db-1 pg_isready -U postgres

# Connect to PostgreSQL directly
docker exec -it slnh-maintenance-db-1 psql -U postgres
```

### If database creation fails:
```bash
# Check PostgreSQL logs
docker logs slnh-maintenance-db-1

# Check disk space
docker exec slnh-maintenance-db-1 df -h

# Check PostgreSQL configuration
docker exec slnh-maintenance-db-1 cat /var/lib/postgresql/data/postgresql.conf
```

---

## Summary

The quickest solution is **Solution 1** - manually create the database using:
```bash
docker exec -it slnh-maintenance-db-1 psql -U postgres -c "CREATE DATABASE maintenance_dashboard;"
docker restart slnh-maintenance-web-1
```

This issue is common in Docker PostgreSQL deployments and usually resolves quickly with database recreation.

After fixing, your application should start successfully and the Django `init_database` command will complete the setup with migrations and admin user creation.