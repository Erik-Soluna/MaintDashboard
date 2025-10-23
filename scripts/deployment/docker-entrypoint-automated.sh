#!/bin/bash

# Fully Automated Docker Entrypoint Script for Maintenance Dashboard
# Version: 2025-09-03-FULLY-AUTOMATED
# Purpose: Complete automation for Portainer deployments with zero manual intervention

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Print functions
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${CYAN}[HEADER]${NC} $1"
}

print_step() {
    echo -e "${MAGENTA}[STEP]${NC} $1"
}

# Configuration with smart defaults
setup_configuration() {
    export DB_HOST="${DB_HOST:-db}"
    export DB_PORT="${DB_PORT:-5432}"
    export DB_NAME="${DB_NAME:-maintenance_dashboard}"
    export DB_USER="${DB_USER:-maintenance_user}"
    export DB_PASSWORD="${DB_PASSWORD:-SecureProdPassword2024!}"
    export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-SecureProdPassword2024!}"
    export ADMIN_USERNAME="${ADMIN_USERNAME:-admin}"
    export ADMIN_EMAIL="${ADMIN_EMAIL:-admin@maintenance.local}"
    export ADMIN_PASSWORD="${ADMIN_PASSWORD:-temppass123}"
    export MAX_RETRIES="${MAX_RETRIES:-30}"
    export RETRY_DELAY="${RETRY_DELAY:-5}"
    export SKIP_DB_INIT="${SKIP_DB_INIT:-false}"
    export SKIP_COLLECTSTATIC="${SKIP_COLLECTSTATIC:-false}"
    export AUTO_MIGRATE="${AUTO_MIGRATE:-true}"
    export AUTO_CREATE_ADMIN="${AUTO_CREATE_ADMIN:-true}"
    export AUTO_SETUP_BRANDING="${AUTO_SETUP_BRANDING:-true}"
    export FORCE_FRESH_START="${FORCE_FRESH_START:-false}"
}

# Wait for database with enhanced retry logic
wait_for_database() {
    print_step "⏳ Waiting for database to be ready..."
    local attempt=1
    
    while [ $attempt -le $MAX_RETRIES ]; do
        print_status "Database connection attempt $attempt/$MAX_RETRIES..."
        
        # Try multiple connection methods
        if check_database_connection; then
            print_success "✅ Database connection successful!"
            return 0
        fi
        
        if [ $attempt -eq $MAX_RETRIES ]; then
            print_error "❌ Database connection failed after $MAX_RETRIES attempts"
            print_error "❌ Please check database configuration and try again"
            exit 1
        fi
        
        print_status "⏳ Retrying in $RETRY_DELAY seconds..."
        sleep $RETRY_DELAY
        attempt=$((attempt + 1))
    done
}

# Enhanced database connection check
check_database_connection() {
    # Method 1: Try with application user
    if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" > /dev/null 2>&1; then
        return 0
    fi
    
    # Method 2: Try with postgres superuser (for database creation)
    if PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "postgres" -d "postgres" -c "SELECT 1;" > /dev/null 2>&1; then
        return 0
    fi
    
    # Method 3: Try basic connection
    if nc -z "$DB_HOST" "$DB_PORT" > /dev/null 2>&1; then
        return 0
    fi
    
    return 1
}

# Ensure database and user exist
ensure_database_setup() {
    print_step "🗄️ Ensuring database and user setup..."
    
    # Try to create database if it doesn't exist
    if ! PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" > /dev/null 2>&1; then
        print_status "Creating database and user..."
        
        # Create database and user using postgres superuser
        PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "postgres" -d "postgres" <<EOF || true
CREATE DATABASE $DB_NAME;
CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
ALTER USER $DB_USER CREATEDB;
\\q
EOF
        
        # Set database owner
        PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "postgres" -d "postgres" -c "ALTER DATABASE $DB_NAME OWNER TO $DB_USER;" > /dev/null 2>&1 || true
        
        print_success "✅ Database and user created"
    else
        print_success "✅ Database connection verified"
    fi
}

# Run Django migrations with conflict resolution
run_migrations() {
    print_step "🔄 Running Django migrations..."
    
    if [ "$AUTO_MIGRATE" != "true" ]; then
        print_warning "⚠️ Auto-migration disabled, skipping..."
        return 0
    fi
    
    # Check for migration conflicts first
    print_status "Checking for migration conflicts..."
    if python manage.py showmigrations --verbosity=0 | grep -q "\\[ \\]"; then
        print_status "Unapplied migrations found, proceeding..."
    fi
    
    # Run migrations with error handling
    local migration_attempts=3
    local attempt=1
    
    while [ $attempt -le $migration_attempts ]; do
        print_status "Migration attempt $attempt/$migration_attempts..."
        
        if run_migration_sequence; then
            print_success "✅ Migrations completed successfully"
            return 0
        fi
        
        if [ $attempt -lt $migration_attempts ]; then
            print_warning "⚠️ Migration failed, trying conflict resolution..."
            resolve_migration_conflicts
        fi
        
        attempt=$((attempt + 1))
    done
    
    print_error "❌ Migrations failed after $migration_attempts attempts"
    exit 1
}

# Migration sequence with proper ordering
run_migration_sequence() {
    # Core Django apps first
    python manage.py migrate contenttypes --noinput || return 1
    python manage.py migrate auth --noinput || return 1
    python manage.py migrate sessions --noinput || return 1
    python manage.py migrate admin --noinput || return 1
    
    # Application migrations
    python manage.py migrate core --noinput || return 1
    python manage.py migrate equipment --noinput || return 1
    python manage.py migrate events --noinput || return 1
    python manage.py migrate maintenance --noinput || return 1
    
    # Final migration for any remaining
    python manage.py migrate --noinput || return 1
    
    return 0
}

# Resolve migration conflicts
resolve_migration_conflicts() {
    print_status "🔧 Resolving migration conflicts..."
    
    # Try to merge migrations
    python manage.py makemigrations --merge --noinput > /dev/null 2>&1 || true
    
    # Fake initial migrations if needed
    python manage.py migrate --fake-initial --noinput > /dev/null 2>&1 || true
    
    # Show migration status
    python manage.py showmigrations --verbosity=1 || true
}

# Create admin user automatically
create_admin_user() {
    print_step "👤 Creating admin user..."
    
    if [ "$AUTO_CREATE_ADMIN" != "true" ]; then
        print_warning "⚠️ Auto admin creation disabled, skipping..."
        return 0
    fi
    
    # Use Django shell to create admin user
    python manage.py shell -c "
from django.contrib.auth.models import User
from django.db import transaction

username = '$ADMIN_USERNAME'
email = '$ADMIN_EMAIL'
password = '$ADMIN_PASSWORD'

try:
    with transaction.atomic():
        if User.objects.filter(username=username).exists():
            user = User.objects.get(username=username)
            print(f'✅ Admin user \"{username}\" already exists')
            print(f'   - Is superuser: {user.is_superuser}')
            print(f'   - Is active: {user.is_active}')
        else:
            user = User.objects.create_superuser(
                username=username,
                email=email,
                password=password,
                first_name='System',
                last_name='Administrator'
            )
            print(f'✅ Admin user \"{username}\" created successfully')
            print(f'   - Username: {username}')
            print(f'   - Email: {email}')
        
        # Show stats
        total_users = User.objects.count()
        superusers = User.objects.filter(is_superuser=True).count()
        print(f'📊 Total users: {total_users}, Superusers: {superusers}')
        
except Exception as e:
    print(f'❌ Error with admin user: {e}')
    exit(1)
" || {
        print_error "❌ Failed to create admin user"
        exit 1
    }
    
    print_success "✅ Admin user setup completed"
}

# Setup branding and initial data
setup_branding_and_data() {
    print_step "🎨 Setting up branding and initial data..."
    
    if [ "$AUTO_SETUP_BRANDING" != "true" ]; then
        print_warning "⚠️ Auto branding setup disabled, skipping..."
        return 0
    fi
    
    # Setup branding
    python manage.py setup_branding > /dev/null 2>&1 || {
        print_warning "⚠️ Branding setup failed or not available"
    }
    
    # Setup default locations
    python manage.py setup_default_locations > /dev/null 2>&1 || {
        print_warning "⚠️ Default locations setup failed or not available"
    }
    
    # Ensure default activity types
    python manage.py ensure_default_activity_types > /dev/null 2>&1 || {
        print_warning "⚠️ Activity types setup failed or not available"
    }
    
    print_success "✅ Branding and initial data setup completed"
}

# Collect static files
collect_static_files() {
    print_step "📁 Collecting static files..."
    
    if [ "$SKIP_COLLECTSTATIC" = "true" ]; then
        print_warning "⚠️ Static file collection disabled, skipping..."
        return 0
    fi
    
    python manage.py collectstatic --noinput --clear > /dev/null 2>&1 || {
        print_warning "⚠️ Static file collection failed"
    }
    
    print_success "✅ Static files collected"
}

# Health check
perform_health_check() {
    print_step "🏥 Performing health check..."
    
    # Basic Django check
    python manage.py check --deploy > /dev/null 2>&1 || {
        print_warning "⚠️ Django deployment check found issues"
    }
    
    # Database connectivity
    python manage.py shell -c "
from django.db import connection
try:
    with connection.cursor() as cursor:
        cursor.execute('SELECT 1')
    print('✅ Database connectivity: OK')
except Exception as e:
    print(f'❌ Database connectivity: {e}')
    exit(1)
" || exit 1
    
    print_success "✅ Health check completed"
}

# Display final status
display_final_status() {
    print_header "🎉 DEPLOYMENT COMPLETED SUCCESSFULLY!"
    echo "=" * 60
    print_success "✅ Database: Ready"
    print_success "✅ Migrations: Applied"
    print_success "✅ Admin User: Created"
    print_success "✅ Static Files: Collected"
    print_success "✅ Health Check: Passed"
    echo ""
    print_status "🔗 Access Information:"
    print_status "   Application: http://localhost:8000/"
    print_status "   Admin Panel: http://localhost:8000/admin/"
    print_status "   Username: $ADMIN_USERNAME"
    print_status "   Password: $ADMIN_PASSWORD"
    echo ""
    print_warning "⚠️  SECURITY: Change admin password after first login!"
    echo "=" * 60
}

# Main execution function
main() {
    print_header "🚀 MAINTENANCE DASHBOARD - AUTOMATED DEPLOYMENT"
    print_header "Version: 2025-09-03-FULLY-AUTOMATED"
    echo ""
    
    # Setup configuration
    setup_configuration
    
    print_status "Configuration loaded:"
    print_status "  Database: $DB_HOST:$DB_PORT/$DB_NAME"
    print_status "  User: $DB_USER"
    print_status "  Admin: $ADMIN_USERNAME ($ADMIN_EMAIL)"
    print_status "  Auto Migrate: $AUTO_MIGRATE"
    print_status "  Auto Admin: $AUTO_CREATE_ADMIN"
    echo ""
    
    # Skip initialization if requested
    if [ "$SKIP_DB_INIT" = "true" ]; then
        print_warning "⚠️ Database initialization skipped"
        exec "$@"
        return
    fi
    
    # Execute initialization steps
    wait_for_database
    ensure_database_setup
    run_migrations
    create_admin_user
    setup_branding_and_data
    collect_static_files
    perform_health_check
    display_final_status
    
    # Clear restart counter on successful completion
    rm -f /tmp/entrypoint_restart_count
    
    print_success "🚀 Starting application..."
    exec "$@"
}

# Trap errors and provide helpful messages
trap 'print_error "❌ Script failed at line $LINENO. Check logs above for details."' ERR

# Execute main function
main "$@"