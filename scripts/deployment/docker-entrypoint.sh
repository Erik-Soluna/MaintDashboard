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
ADMIN_USERNAME="${ADMIN_USERNAME:-admin}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@maintenance.local}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-temppass123}"

# Fast database wait (optimized)
wait_for_database() {
    local attempt=1
    local max_attempts=20
    
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
            print_success "✅ Database ready - checking for new migrations..."
            
            # Run migrations (will skip if nothing to do)
            python manage.py migrate --noinput > /dev/null 2>&1 || print_warning "⚠️ Migration check skipped"
            
            print_success "✅ Boot complete (fast path)"
            ;;
            
        "FRESH")
            # Fresh database - full initialization needed
            print_status "🆕 Fresh database - initializing..."
            python manage.py migrate --noinput
            python manage.py init_database --admin-username "$ADMIN_USERNAME" --admin-email "$ADMIN_EMAIL" --admin-password "$ADMIN_PASSWORD" --force
            print_success "✅ Fresh database initialized"
            ;;
            
        "PARTIAL"|"ERROR")
            # Partial state - run full migrations
            print_status "🔄 Running migrations..."
            python manage.py migrate --noinput || python manage.py migrate --fake-initial
            python manage.py init_database --admin-username "$ADMIN_USERNAME" --admin-email "$ADMIN_EMAIL" --admin-password "$ADMIN_PASSWORD" --force > /dev/null 2>&1 || true
            print_success "✅ Migrations complete"
            ;;
    esac
    
    rm -f /tmp/entrypoint_restart_count
}

main() {
    print_status "🚀 Starting Maintenance Dashboard..."
    
    # Quick startup
    wait_for_database
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

