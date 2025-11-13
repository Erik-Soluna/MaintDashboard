#!/bin/bash

# Fast Docker Entrypoint Script for Maintenance Dashboard
# Version: 2025-10-09-OPTIMIZED
# Purpose: Fast, efficient database initialization with smart caching

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Configuration
DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-maintenance_dashboard}"
DB_USER="${DB_USER:-maintenance_user}"
DB_PASSWORD="${DB_PASSWORD:-SecureProdPassword2024!}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-SecureProdPassword2024!}"
ADMIN_USERNAME="${ADMIN_USERNAME:-admin}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@maintenance.local}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-temppass123}"

# Wait for PostgreSQL server to be ready (using postgres superuser)
wait_for_postgres_server() {
    local attempt=1
    local max_attempts=30
    
    print_status "⏳ Waiting for PostgreSQL server to be ready..."
    while [ $attempt -le $max_attempts ]; do
        if PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$POSTGRES_USER" -d "postgres" -c "SELECT 1;" > /dev/null 2>&1; then
            [ $attempt -gt 1 ] && print_success "✅ PostgreSQL server ready (attempt $attempt)"
            return 0
        fi
        
        local sleep_time=$(awk "BEGIN {print ($attempt * 0.5 > 3) ? 3 : $attempt * 0.5}")
        sleep $sleep_time
        attempt=$((attempt + 1))
    done
    
    print_error "❌ PostgreSQL server timeout after $max_attempts attempts"
    return 1
}

# Ensure database user exists (create if it doesn't)
ensure_database_user() {
    print_status "🔧 Ensuring database user '$DB_USER' exists..."
    
    # If DB_USER matches POSTGRES_USER, the user already exists (created by PostgreSQL init)
    if [ "$DB_USER" = "$POSTGRES_USER" ]; then
        print_success "✅ User '$DB_USER' matches PostgreSQL superuser - already exists"
        return 0
    fi
    
    # Check if user exists by trying to query pg_roles
    local user_exists=$(PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$POSTGRES_USER" -d "postgres" -t -c "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER';" 2>/dev/null | xargs)
    
    if [ "$user_exists" = "1" ]; then
        print_success "✅ User '$DB_USER' already exists"
        return 0
    fi
    
    # Create the user
    print_status "👤 Creating user '$DB_USER'..."
    if PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$POSTGRES_USER" -d "postgres" -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" > /dev/null 2>&1; then
        print_success "✅ User '$DB_USER' created successfully"
    else
        print_error "❌ Failed to create user '$DB_USER'"
        return 1
    fi
    
    # Grant CREATEDB privilege (needed for Django migrations)
    print_status "🔑 Granting CREATEDB privilege to '$DB_USER'..."
    PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$POSTGRES_USER" -d "postgres" -c "ALTER USER $DB_USER CREATEDB;" > /dev/null 2>&1 || true
    
    return 0
}

# Ensure database exists (create if it doesn't)
ensure_database() {
    print_status "🔧 Ensuring database '$DB_NAME' exists..."
    
    # Check if database exists
    local db_exists=$(PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$POSTGRES_USER" -d "postgres" -t -c "SELECT 1 FROM pg_database WHERE datname='$DB_NAME';" 2>/dev/null | xargs)
    
    if [ "$db_exists" = "1" ]; then
        print_success "✅ Database '$DB_NAME' already exists"
    else
        # Create the database
        print_status "📦 Creating database '$DB_NAME'..."
        if PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$POSTGRES_USER" -d "postgres" -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" > /dev/null 2>&1; then
            print_success "✅ Database '$DB_NAME' created successfully"
        else
            print_error "❌ Failed to create database '$DB_NAME'"
            return 1
        fi
    fi
    
    # Grant all privileges on database to the user
    print_status "🔑 Granting privileges on database '$DB_NAME' to '$DB_USER'..."
    PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$POSTGRES_USER" -d "postgres" -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;" > /dev/null 2>&1 || true
    
    # Grant privileges on schema public
    print_status "🔑 Granting privileges on schema public..."
    PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$POSTGRES_USER" -d "$DB_NAME" -c "GRANT ALL ON SCHEMA public TO $DB_USER; ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $DB_USER; ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $DB_USER;" > /dev/null 2>&1 || true
    
    return 0
}

# Fast database wait (optimized) - now connects with application user
wait_for_database() {
    local attempt=1
    local max_attempts=20
    
    print_status "⏳ Waiting for database connection with user '$DB_USER'..."
    while [ $attempt -le $max_attempts ]; do
        if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" > /dev/null 2>&1; then
            [ $attempt -gt 1 ] && print_success "✅ Database ready (attempt $attempt)"
            return 0
        fi
        
        # Exponential backoff: 0.5s, 1s, 1.5s, 2s, 2.5s, max 3s
        local sleep_time=$(awk "BEGIN {print ($attempt * 0.5 > 3) ? 3 : $attempt * 0.5}")
        sleep $sleep_time
        attempt=$((attempt + 1))
    done
    
    print_error "❌ Database timeout after $max_attempts attempts"
    exit 1
}

# Smart database initialization (fast-path for already-initialized databases)
initialize_database_smart() {
    print_status "🚀 Initializing..."
    
    # Single Python script to check database state (faster than multiple dbshell calls)
    local db_state=$(python - <<'PYTHON'
import os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maintenance_dashboard.settings')
try:
    import django
    django.setup()
    from django.db import connection
    
    with connection.cursor() as cursor:
        # Check key tables in one query
        tables = ['django_migrations', 'core_userprofile', 'maintenance_maintenanceactivity', 'equipment_equipment']
        exists = []
        for table in tables:
            try:
                cursor.execute(f"SELECT 1 FROM {table} LIMIT 1;")
                exists.append(True)
            except:
                exists.append(False)
        
        if all(exists):
            print("READY", end='')
        elif any(exists):
            print("PARTIAL", end='')
        else:
            print("FRESH", end='')
except Exception as e:
    print("ERROR", end='')
    sys.exit(1)
PYTHON
)
    
    case "$db_state" in
        "READY")
            # Fast path - database already initialized
            print_success "✅ Database ready - running migrations..."
            
            # Create migrations if model changes exist (will skip if nothing to do)
            print_status "📝 Checking for new migrations..."
            python manage.py makemigrations --noinput || print_warning "⚠️ No new migrations to create"
            
            # Always run migrations on boot (will skip if nothing to do)
            print_status "🔄 Applying migrations..."
            python manage.py migrate --noinput
            
            print_success "✅ Boot complete (migrations applied)"
            ;;
            
        "FRESH")
            # Fresh database - full initialization needed
            print_status "🆕 Fresh database - initializing..."
            
            # Create migrations first
            python manage.py makemigrations --noinput || print_warning "⚠️ Makemigrations skipped"
            
            # Run migrations
            python manage.py migrate --noinput
            python manage.py init_database --admin-username "$ADMIN_USERNAME" --admin-email "$ADMIN_EMAIL" --admin-password "$ADMIN_PASSWORD" --force
            print_success "✅ Fresh database initialized"
            ;;
            
        "PARTIAL"|"ERROR")
            # Partial state - run full migrations
            print_status "🔄 Running migrations..."
            
            # Create migrations first
            python manage.py makemigrations --noinput || print_warning "⚠️ Makemigrations skipped"
            
            # Run migrations
            python manage.py migrate --noinput || python manage.py migrate --fake-initial
            python manage.py init_database --admin-username "$ADMIN_USERNAME" --admin-email "$ADMIN_EMAIL" --admin-password "$ADMIN_PASSWORD" --force > /dev/null 2>&1 || true
            print_success "✅ Migrations complete"
            ;;
    esac
    
    rm -f /tmp/entrypoint_restart_count
}

main() {
    print_status "🚀 Starting Maintenance Dashboard..."
    
    # Step 1: Wait for PostgreSQL server (using postgres superuser)
    if ! wait_for_postgres_server; then
        exit 1
    fi
    
    # Step 2: Ensure database user exists
    if ! ensure_database_user; then
        exit 1
    fi
    
    # Step 3: Ensure database exists
    if ! ensure_database; then
        exit 1
    fi
    
    # Step 4: Wait for database connection (using application user)
    wait_for_database
    
    # Step 5: Initialize database schema and data
    initialize_database_smart
    
    print_success "✅ Ready to serve"
    
    # Start application
    if [ "$1" = "web" ] || [ "$1" = "gunicorn" ]; then
        exec gunicorn --bind 0.0.0.0:8000 --workers 3 --timeout 120 maintenance_dashboard.wsgi:application
    elif [ "$1" = "celery" ]; then
        exec celery -A maintenance_dashboard worker --loglevel=info
    elif [ "$1" = "celery-beat" ]; then
        exec celery -A maintenance_dashboard beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
    else
        exec "$@"
    fi
}

main "$@"

