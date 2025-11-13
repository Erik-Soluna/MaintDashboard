#!/bin/bash

# Enhanced Docker Entrypoint Script for Maintenance Dashboard
# Version: 2025-10-24-DEBUG-VERSION
# Purpose: Database initialization with comprehensive logging and debugging

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

# Configuration with debugging
DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-maintenance_dashboard_prod}"
DB_USER="${DB_USER:-postgres}"
DB_PASSWORD="${DB_PASSWORD:-SecureProdPassword2024!}"
ADMIN_USERNAME="${ADMIN_USERNAME:-admin}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@maintenance.local}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-temppass123}"

# Debug logging function
debug_log() {
    echo -e "${BLUE}[DEBUG]${NC} $1"
}

# Log all configuration
debug_log "=== CONFIGURATION DEBUG ==="
debug_log "DB_HOST: $DB_HOST"
debug_log "DB_PORT: $DB_PORT"
debug_log "DB_NAME: $DB_NAME"
debug_log "DB_USER: $DB_USER"
debug_log "DB_PASSWORD: [HIDDEN]"
debug_log "POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-[NOT SET]}"
debug_log "=========================="

# Wait for PostgreSQL to be ready (as postgres user)
wait_for_postgres() {
    local attempt=1
    local max_attempts=30
    
    print_status "⏳ Waiting for PostgreSQL to be ready..."
    debug_log "Attempting to connect to PostgreSQL at $DB_HOST:$DB_PORT as postgres user"
    
    while [ $attempt -le $max_attempts ]; do
        debug_log "Connection attempt $attempt/$max_attempts"
        
        if PGPASSWORD="${POSTGRES_PASSWORD:-SecureProdPassword2024!}" psql -h "$DB_HOST" -p "$DB_PORT" -U "postgres" -d "postgres" -c "SELECT 1;" > /dev/null 2>&1; then
            print_success "✅ PostgreSQL ready (attempt $attempt)"
            debug_log "PostgreSQL connection successful"
            return 0
        fi
        
        debug_log "PostgreSQL not ready yet, waiting..."
        local sleep_time=$(awk "BEGIN {print ($attempt * 0.5 > 3) ? 3 : $attempt * 0.5}")
        sleep $sleep_time
        attempt=$((attempt + 1))
    done
    
    print_error "❌ PostgreSQL timeout after $max_attempts attempts"
    debug_log "Failed to connect to PostgreSQL after $max_attempts attempts"
    exit 1
}

# Ensure database user has proper permissions
ensure_database_user() {
    print_status "🔧 Ensuring database user '$DB_USER' has proper permissions..."
    debug_log "Checking database user configuration..."
    
    # Since we're using postgres user, just ensure it has proper permissions
    if [ "$DB_USER" = "postgres" ]; then
        print_success "✅ Using postgres user (superuser privileges)"
        debug_log "Using postgres user - no additional user creation needed"
        
        # Ensure database exists
        debug_log "Ensuring database '$DB_NAME' exists..."
        if PGPASSWORD="${POSTGRES_PASSWORD:-SecureProdPassword2024!}" psql -h "$DB_HOST" -p "$DB_PORT" -U "postgres" -d "postgres" -c "SELECT 1 FROM pg_database WHERE datname='$DB_NAME';" | grep -q "1"; then
            debug_log "Database '$DB_NAME' already exists"
        else
            debug_log "Creating database '$DB_NAME'..."
            PGPASSWORD="${POSTGRES_PASSWORD:-SecureProdPassword2024!}" psql -h "$DB_HOST" -p "$DB_PORT" -U "postgres" -d "postgres" -c "CREATE DATABASE $DB_NAME;" > /dev/null 2>&1
            debug_log "Database '$DB_NAME' created successfully"
        fi
        
        # Grant all privileges on the database
        debug_log "Setting up permissions for postgres user on database '$DB_NAME'..."
        PGPASSWORD="${POSTGRES_PASSWORD:-SecureProdPassword2024!}" psql -h "$DB_HOST" -p "$DB_PORT" -U "postgres" -d "$DB_NAME" -c "GRANT ALL PRIVILEGES ON SCHEMA public TO postgres;" > /dev/null 2>&1 || true
        PGPASSWORD="${POSTGRES_PASSWORD:-SecureProdPassword2024!}" psql -h "$DB_HOST" -p "$DB_PORT" -U "postgres" -d "$DB_NAME" -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO postgres;" > /dev/null 2>&1 || true
        PGPASSWORD="${POSTGRES_PASSWORD:-SecureProdPassword2024!}" psql -h "$DB_HOST" -p "$DB_PORT" -U "postgres" -d "$DB_NAME" -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO postgres;" > /dev/null 2>&1 || true
        
        print_success "✅ Database permissions configured for postgres user"
        debug_log "Database permissions setup complete"
    else
        # Handle other users if needed
        print_status "👤 Configuring user '$DB_USER'..."
        debug_log "Configuring custom user '$DB_USER'..."
        
        # Check if user exists
        local user_exists=$(PGPASSWORD="${POSTGRES_PASSWORD:-SecureProdPassword2024!}" psql -h "$DB_HOST" -p "$DB_PORT" -U "postgres" -d "postgres" -t -c "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER';" 2>/dev/null | xargs)
        
        if [ "$user_exists" = "1" ]; then
            print_success "✅ User '$DB_USER' already exists"
            debug_log "User '$DB_USER' already exists"
        else
            print_status "👤 Creating user '$DB_USER'..."
            debug_log "Creating user '$DB_USER'..."
            
            # Create user
            PGPASSWORD="${POSTGRES_PASSWORD:-SecureProdPassword2024!}" psql -h "$DB_HOST" -p "$DB_PORT" -U "postgres" -d "postgres" -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" > /dev/null 2>&1
            
            # Grant privileges
            PGPASSWORD="${POSTGRES_PASSWORD:-SecureProdPassword2024!}" psql -h "$DB_HOST" -p "$DB_PORT" -U "postgres" -d "postgres" -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;" > /dev/null 2>&1
            PGPASSWORD="${POSTGRES_PASSWORD:-SecureProdPassword2024!}" psql -h "$DB_HOST" -p "$DB_PORT" -U "postgres" -d "$DB_NAME" -c "GRANT ALL PRIVILEGES ON SCHEMA public TO $DB_USER;" > /dev/null 2>&1
            PGPASSWORD="${POSTGRES_PASSWORD:-SecureProdPassword2024!}" psql -h "$DB_HOST" -p "$DB_PORT" -U "postgres" -d "$DB_NAME" -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $DB_USER;" > /dev/null 2>&1
            PGPASSWORD="${POSTGRES_PASSWORD:-SecureProdPassword2024!}" psql -h "$DB_HOST" -p "$DB_PORT" -U "postgres" -d "$DB_NAME" -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $DB_USER;" > /dev/null 2>&1
            
            print_success "✅ User '$DB_USER' created successfully"
            debug_log "User '$DB_USER' created and configured successfully"
        fi
    fi
}

# Fast database wait (optimized) - using configured DB_USER
wait_for_database() {
    local attempt=1
    local max_attempts=20
    
    debug_log "Testing database connection as '$DB_USER' to database '$DB_NAME'"
    
    while [ $attempt -le $max_attempts ]; do
        debug_log "Database connection attempt $attempt/$max_attempts"
        
        if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" > /dev/null 2>&1; then
            [ $attempt -gt 1 ] && print_success "✅ Database ready (attempt $attempt)"
            debug_log "Database connection successful as '$DB_USER'"
            return 0
        fi
        
        debug_log "Database connection failed, retrying..."
        # Exponential backoff: 0.5s, 1s, 1.5s, 2s, 2.5s, max 3s
        local sleep_time=$(awk "BEGIN {print ($attempt * 0.5 > 3) ? 3 : $attempt * 0.5}")
        sleep $sleep_time
        attempt=$((attempt + 1))
    done
    
    print_error "❌ Database timeout after $max_attempts attempts"
    debug_log "Failed to connect to database as '$DB_USER' after $max_attempts attempts"
    exit 1
}

# Smart database initialization (fast-path for already-initialized databases)
initialize_database_smart() {
    print_status "🚀 Initializing..."
    debug_log "Starting database initialization process..."
    
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
    
    debug_log "Database state detected: $db_state"
    
    case "$db_state" in
        "READY")
            # Fast path - database already initialized
            print_success "✅ Database ready - checking for new migrations..."
            debug_log "Database is ready, running migration check..."
            
            # Run migrations (will skip if nothing to do)
            python manage.py migrate --noinput > /dev/null 2>&1 || print_warning "⚠️ Migration check skipped"
            
            print_success "✅ Boot complete (fast path)"
            debug_log "Fast path initialization complete"
            ;;
            
        "FRESH")
            # Fresh database - full initialization needed
            print_status "🆕 Fresh database - initializing..."
            debug_log "Fresh database detected, running full initialization..."
            python manage.py migrate --noinput
            python manage.py init_database --admin-username "$ADMIN_USERNAME" --admin-email "$ADMIN_EMAIL" --admin-password "$ADMIN_PASSWORD" --force
            print_success "✅ Fresh database initialized"
            debug_log "Fresh database initialization complete"
            ;;
            
        "PARTIAL"|"ERROR")
            # Partial state - run full migrations
            print_status "🔄 Running migrations..."
            debug_log "Partial database state detected, running migrations..."
            python manage.py migrate --noinput || python manage.py migrate --fake-initial
            python manage.py init_database --admin-username "$ADMIN_USERNAME" --admin-email "$ADMIN_EMAIL" --admin-password "$ADMIN_PASSWORD" --force > /dev/null 2>&1 || true
            print_success "✅ Migrations complete"
            debug_log "Migration process complete"
            ;;
    esac
    
    rm -f /tmp/entrypoint_restart_count
}

main() {
    print_status "🚀 Starting Maintenance Dashboard..."
    debug_log "=== DOCKER ENTRYPOINT START ==="
    debug_log "Container started with command: $*"
    
    # Step 1: Wait for PostgreSQL to be ready
    wait_for_postgres
    
    # Step 2: Ensure maintenance_user exists
    ensure_database_user
    
    # Step 3: Wait for database to be accessible with maintenance_user
    wait_for_database
    
    # Step 4: Initialize database
    initialize_database_smart
    
    print_success "✅ Ready to serve"
    debug_log "=== DOCKER ENTRYPOINT COMPLETE ==="
    
    # Start application
    if [ "$1" = "web" ] || [ "$1" = "gunicorn" ]; then
        debug_log "Starting web server with gunicorn..."
        exec gunicorn --bind 0.0.0.0:8000 --workers 3 --timeout 120 maintenance_dashboard.wsgi:application
    elif [ "$1" = "celery" ]; then
        debug_log "Starting celery worker..."
        exec celery -A maintenance_dashboard worker --loglevel=info
    elif [ "$1" = "celery-beat" ]; then
        debug_log "Starting celery beat scheduler..."
        exec celery -A maintenance_dashboard beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
    else
        debug_log "Starting with custom command: $*"
        exec "$@"
    fi
}

main "$@"
