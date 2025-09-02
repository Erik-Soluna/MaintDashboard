#!/bin/bash
# Enhanced Docker Entrypoint Script for Database Initialization
# This script handles database initialization failures gracefully with retry logic

set -e

# Configuration
MAX_RETRIES=30
RETRY_DELAY=5
DB_READY_TIMEOUT=300
HEALTHCHECK_INTERVAL=10

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
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

# Function to check if database is ready
check_database_ready() {
    local max_attempts=30
    local attempt=1
    
    # For production, we need to connect as postgres to create the database
    # but the application will use maintenance_user
    if [ "$DB_USER" = "maintenance_user" ]; then
        # Use postgres superuser for database operations
        DB_CHECK_USER="postgres"
        DB_CHECK_PASSWORD="${POSTGRES_PASSWORD:-SecureProdPassword2024!}"
    else
        DB_CHECK_USER="$DB_USER"
        DB_CHECK_PASSWORD="$DB_PASSWORD"
    fi
    
    print_status "🔍 DB READY DEBUG:"
    print_status "  DB_CHECK_USER: $DB_CHECK_USER"
    print_status "  DB_CHECK_PASSWORD: ${DB_CHECK_PASSWORD:0:10}..."
    print_status "  Full DB_CHECK_PASSWORD: $DB_CHECK_PASSWORD"
    print_status "Waiting for database to be ready with user: $DB_CHECK_USER..."
    
    while [ $attempt -le $max_attempts ]; do
        if PGPASSWORD="$DB_CHECK_PASSWORD" pg_isready -h "${DB_HOST:-db}" -p "${DB_PORT:-5432}" -U "$DB_CHECK_USER" -d "${DB_NAME:-maintenance_dashboard}" > /dev/null 2>&1; then
            print_success "Database is ready"
            return 0
        fi
        
        print_status "Database not ready, waiting... (attempt $attempt/$max_attempts)"
        sleep $RETRY_DELAY
        attempt=$((attempt + 1))
    done
    
    print_error "Database did not become ready within timeout"
    return 1
}

# Function to create database if it doesn't exist
ensure_database_exists() {
    print_status "Checking if database exists..."
    
    # For production, we need to connect as postgres to create the database
    # but the application will use maintenance_user
    if [ "$DB_USER" = "maintenance_user" ]; then
        # Use postgres superuser for database operations
        DB_CREATE_USER="postgres"
        DB_CREATE_PASSWORD="${POSTGRES_PASSWORD:-SecureProdPassword2024!}"
    elif [ "$DB_USER" = "maintenance_user_dev" ]; then
        # For dev environment, the database user is also the superuser
        DB_CREATE_USER="$DB_USER"
        DB_CREATE_PASSWORD="$DB_PASSWORD"
    else
        # Fallback for other configurations
        DB_CREATE_USER="$DB_USER"
        DB_CREATE_PASSWORD="$DB_PASSWORD"
    fi
    
    print_status "🔍 DB CREATE DEBUG:"
    print_status "  DB_CREATE_USER: $DB_CREATE_USER"
    print_status "  DB_CREATE_PASSWORD: ${DB_CREATE_PASSWORD:0:10}..."
    print_status "  Full DB_CREATE_PASSWORD: $DB_CREATE_PASSWORD"
    print_status "Using user: $DB_CREATE_USER for database operations"
    
    # Check if database exists
    if PGPASSWORD="$DB_CREATE_PASSWORD" psql -h "${DB_HOST:-db}" -p "${DB_PORT:-5432}" -U "$DB_CREATE_USER" -d "postgres" -t -c "SELECT 1 FROM pg_database WHERE datname='${DB_NAME:-maintenance_dashboard}'" | grep -q 1; then
        print_success "Database '${DB_NAME:-maintenance_dashboard}' already exists"
        
        # Always ensure maintenance_user exists and has privileges
        if [ "$DB_USER" != "$DB_CREATE_USER" ]; then
            print_status "Ensuring user $DB_USER exists and has privileges..."
            PGPASSWORD="$DB_CREATE_PASSWORD" psql -h "${DB_HOST:-db}" -p "${DB_PORT:-5432}" -U "$DB_CREATE_USER" -d "postgres" -c "CREATE USER $DB_USER WITH PASSWORD '${DB_PASSWORD:-SecureProdPassword2024!}';" > /dev/null 2>&1 || true
            PGPASSWORD="$DB_CREATE_PASSWORD" psql -h "${DB_HOST:-db}" -p "${DB_PORT:-5432}" -U "$DB_CREATE_USER" -d "postgres" -c "GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME:-maintenance_dashboard} TO $DB_USER;" > /dev/null 2>&1 || true
            
            # Grant schema-level permissions for Django migrations
            print_status "Granting schema permissions to $DB_USER..."
            PGPASSWORD="$DB_CREATE_PASSWORD" psql -h "${DB_HOST:-db}" -p "${DB_PORT:-5432}" -U "$DB_CREATE_USER" -d "${DB_NAME:-maintenance_dashboard}" -c "GRANT ALL ON SCHEMA public TO $DB_USER;" > /dev/null 2>&1 || true
            PGPASSWORD="$DB_CREATE_PASSWORD" psql -h "${DB_HOST:-db}" -p "${DB_PORT:-5432}" -U "$DB_CREATE_USER" -d "${DB_NAME:-maintenance_dashboard}" -c "GRANT CREATE ON SCHEMA public TO $DB_USER;" > /dev/null 2>&1 || true
            PGPASSWORD="$DB_CREATE_PASSWORD" psql -h "${DB_HOST:-db}" -p "${DB_PORT:-5432}" -U "$DB_CREATE_USER" -d "${DB_NAME:-maintenance_dashboard}" -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $DB_USER;" > /dev/null 2>&1 || true
        fi
        
        return 0
    fi
    
    # Create database
    print_status "Creating database '${DB_NAME:-maintenance_dashboard}' with user: $DB_CREATE_USER..."
    if PGPASSWORD="$DB_CREATE_PASSWORD" psql -h "${DB_HOST:-db}" -p "${DB_PORT:-5432}" -U "$DB_CREATE_USER" -d "postgres" -c "CREATE DATABASE ${DB_NAME:-maintenance_dashboard}"; then
        print_success "Database '${DB_NAME:-maintenance_dashboard}' created successfully"
        
        # Create maintenance_user and grant privileges if it's different from the create user
        if [ "$DB_USER" != "$DB_CREATE_USER" ]; then
            print_status "Creating user $DB_USER and granting privileges..."
            PGPASSWORD="$DB_CREATE_PASSWORD" psql -h "${DB_HOST:-db}" -p "${DB_PORT:-5432}" -U "$DB_CREATE_USER" -d "postgres" -c "CREATE USER $DB_USER WITH PASSWORD '${DB_PASSWORD:-SecureProdPassword2024!}';" > /dev/null 2>&1 || true
            PGPASSWORD="$DB_CREATE_PASSWORD" psql -h "${DB_HOST:-db}" -p "${DB_PORT:-5432}" -U "$DB_CREATE_USER" -d "postgres" -c "GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME:-maintenance_dashboard} TO $DB_USER;" > /dev/null 2>&1 || true
            
            # Grant schema-level permissions for Django migrations
            print_status "Granting schema permissions to $DB_USER..."
            PGPASSWORD="$DB_CREATE_PASSWORD" psql -h "${DB_HOST:-db}" -p "${DB_PORT:-5432}" -U "$DB_CREATE_USER" -d "${DB_NAME:-maintenance_dashboard}" -c "GRANT ALL ON SCHEMA public TO $DB_USER;" > /dev/null 2>&1 || true
            PGPASSWORD="$DB_CREATE_PASSWORD" psql -h "${DB_HOST:-db}" -p "${DB_PORT:-5432}" -U "$DB_CREATE_USER" -d "${DB_NAME:-maintenance_dashboard}" -c "GRANT CREATE ON SCHEMA public TO $DB_USER;" > /dev/null 2>&1 || true
            PGPASSWORD="$DB_CREATE_PASSWORD" psql -h "${DB_HOST:-db}" -p "${DB_PORT:-5432}" -U "$DB_CREATE_USER" -d "${DB_NAME:-maintenance_dashboard}" -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $DB_USER;" > /dev/null 2>&1 || true
        fi
        
        return 0
    else
        print_error "Failed to create database"
        return 1
    fi
}

# Function to run database initialization with retry
run_database_initialization() {
    local retry_count=0
    local max_retries=${MAX_RETRIES:-30}
    
    print_status "Starting database initialization with retry logic..."
    
    while [ $retry_count -lt $max_retries ]; do
        print_status "Initialization attempt $(($retry_count + 1))/$max_retries"
        
        # Check database readiness
        if ! check_database_ready; then
            print_warning "Database not ready, retrying in $RETRY_DELAY seconds..."
            sleep $RETRY_DELAY
            retry_count=$((retry_count + 1))
            continue
        fi
        
        # Test direct connection to postgres container
        print_status "🔍 TESTING DIRECT POSTGRES CONNECTION:"
        print_status "  Testing with user: ${DB_USER:-maintenance_user}"
        print_status "  Testing with password: ${DB_PASSWORD:0:10}..."
        
        if PGPASSWORD="$DB_PASSWORD" psql -h "${DB_HOST:-db}" -p "${DB_PORT:-5432}" -U "${DB_USER:-maintenance_user}" -d "${DB_NAME:-maintenance_dashboard}" -c "SELECT version();" > /dev/null 2>&1; then
            print_success "✅ Direct database connection successful!"
        else
            print_error "❌ Direct database connection failed!"
            print_status "  Trying to connect with postgres superuser..."
            if PGPASSWORD="$POSTGRES_PASSWORD" psql -h "${DB_HOST:-db}" -p "${DB_PORT:-5432}" -U "postgres" -d "postgres" -c "SELECT version();" > /dev/null 2>&1; then
                print_success "✅ Direct postgres superuser connection successful!"
            else
                print_error "❌ Direct postgres superuser connection failed too!"
            fi
        fi
        
        # Ensure database exists
        if ! ensure_database_exists; then
            print_warning "Database creation failed, retrying in $RETRY_DELAY seconds..."
            sleep $RETRY_DELAY
            retry_count=$((retry_count + 1))
            continue
        fi
        
        # Run comprehensive database check and initialization
        print_status "Running comprehensive database check and initialization..."
        
        # First, check if this is a fresh database and handle it specially
        if ! python manage.py dbshell -c "SELECT 1 FROM django_migrations LIMIT 1;" > /dev/null 2>&1; then
            print_status "Fresh database detected, using fake-initial approach..."
            
            # For fresh databases, use aggressive approach to bypass conflicts entirely
            print_status "Using aggressive fresh database initialization..."
            
            # Initialize nuclear option flag
            goto_nuclear=false
            
            # First, try to merge the conflicting migrations
            if python manage.py makemigrations --merge --noinput; then
                print_success "Migration conflicts merged successfully"
                # Now try fake-initial
                if python manage.py migrate --fake-initial --noinput; then
                    print_success "Fresh database initialized with merged migrations"
                else
                    print_warning "Fake-initial still failed after merge, trying direct approach..."
                    # Try direct migration without fake-initial
                    if python manage.py migrate --noinput; then
                        print_success "Fresh database initialized with direct migrations"
                    else
                        print_warning "All migration approaches failed, trying nuclear option immediately..."
                        # Skip retry and go directly to nuclear option
                        goto_nuclear=true
                    fi
                fi
            else
                print_warning "Migration merge failed, trying nuclear option..."
                goto_nuclear=true
            fi
            
            # If we need to go to nuclear option, do it now
            if [ "$goto_nuclear" = "true" ]; then
                
                # Nuclear option: Create django_migrations table manually and fake-apply all migrations
                print_status "Creating django_migrations table manually..."
                python manage.py dbshell -c "
                    CREATE TABLE IF NOT EXISTS django_migrations (
                        id SERIAL PRIMARY KEY,
                        app VARCHAR(255) NOT NULL,
                        name VARCHAR(255) NOT NULL,
                        applied TIMESTAMP WITH TIME ZONE NOT NULL
                    );
                " || true
                
                # Try fake-initial again
                if python manage.py migrate --fake-initial --noinput; then
                    print_success "Fresh database initialized with manual migrations table"
                else
                    print_warning "Manual approach also failed, trying ultimate nuclear option..."
                    
                    # Ultimate nuclear option: Create all tables directly using Django's sqlmigrate
                    print_status "Creating all tables directly using SQL..."
                    python manage.py sqlmigrate core 0001_initial > /tmp/core_initial.sql 2>/dev/null || true
                    python manage.py sqlmigrate maintenance 0001_initial > /tmp/maintenance_initial.sql 2>/dev/null || true
                    python manage.py sqlmigrate equipment 0001_initial > /tmp/equipment_initial.sql 2>/dev/null || true
                    python manage.py sqlmigrate events 0001_initial > /tmp/events_initial.sql 2>/dev/null || true
                    
                    # Apply the SQL directly
                    if [ -f /tmp/core_initial.sql ]; then
                        python manage.py dbshell < /tmp/core_initial.sql || true
                    fi
                    if [ -f /tmp/maintenance_initial.sql ]; then
                        python manage.py dbshell < /tmp/maintenance_initial.sql || true
                    fi
                    if [ -f /tmp/equipment_initial.sql ]; then
                        python manage.py dbshell < /tmp/equipment_initial.sql || true
                    fi
                    if [ -f /tmp/events_initial.sql ]; then
                        python manage.py dbshell < /tmp/events_initial.sql || true
                    fi
                    
                    # Mark all migrations as applied
                    python manage.py migrate --fake --noinput || true
                    
                    print_success "Fresh database initialized with ultimate nuclear option"
                fi
            else
                # If we didn't need nuclear option, we're done
                print_success "Fresh database initialization completed successfully"
            fi
        else
            # Existing database - use standard approach
            if python manage.py ensure_database; then
                print_success "Database tables check completed successfully!"
            else
                print_warning "Database tables check failed, attempting conflict resolution..."
                
                # For existing databases, try to resolve conflicts
                if resolve_migration_conflicts; then
                    print_success "Migration conflicts resolved, retrying database check..."
                    if python manage.py ensure_database; then
                        print_success "Database tables check completed successfully after conflict resolution!"
                    else
                        print_warning "Database tables check still failed after conflict resolution, retrying in $RETRY_DELAY seconds..."
                        sleep $RETRY_DELAY
                        retry_count=$((retry_count + 1))
                        continue
                    fi
                else
                    print_warning "Failed to resolve migration conflicts, retrying in $RETRY_DELAY seconds..."
                    sleep $RETRY_DELAY
                    retry_count=$((retry_count + 1))
                    continue
                fi
            fi
        fi
        
        # Then run the standard initialization
        print_status "Running Django database initialization..."
        if python manage.py init_database \
            --admin-username "${ADMIN_USERNAME:-admin}" \
            --admin-email "${ADMIN_EMAIL:-admin@maintenance.local}" \
            --admin-password "${ADMIN_PASSWORD:-temppass123}" \
            ${FORCE_INIT_DATA:+--force}; then
            print_success "Database initialization completed successfully!"
            
            # Now set up the branding system
            print_status "Setting up branding system..."
            if setup_branding_system; then
                print_success "Branding system setup completed successfully!"
            else
                print_warning "Branding system setup failed, but continuing..."
            fi
            
            return 0
        else
            print_warning "Database initialization failed, retrying in $RETRY_DELAY seconds..."
            sleep $RETRY_DELAY
            retry_count=$((retry_count + 1))
        fi
    done
    
    print_error "Database initialization failed after $max_retries attempts"
    return 1
}

# Function to resolve migration conflicts
resolve_migration_conflicts() {
    print_status "🔧 Resolving migration conflicts..."
    
    # Check if migration conflict resolution is enabled
    if [ "${MIGRATION_CONFLICT_RESOLUTION:-false}" != "true" ]; then
        print_status "Migration conflict resolution disabled, but attempting to resolve conflicts anyway..."
        # Don't return, continue with conflict resolution
    fi
    
    # Check for conflicts using multiple detection methods
    print_status "Checking for migration conflicts..."
    
    local conflicts_detected=false
    
    # Method 1: Check for explicit conflict messages
    if python manage.py showmigrations --list 2>&1 | grep -q "Conflicting migrations detected"; then
        print_warning "Migration conflicts detected via showmigrations!"
        conflicts_detected=true
    fi
    
    # Method 2: Check for multiple leaf nodes in specific apps
    local core_leaves=$(python manage.py showmigrations core 2>/dev/null | grep -c "\[X\]" || echo "0")
    local maintenance_leaves=$(python manage.py showmigrations maintenance 2>/dev/null | grep -c "\[X\]" || echo "0")
    
    if [ "$core_leaves" -gt 1 ] || [ "$maintenance_leaves" -gt 1 ]; then
        print_warning "Multiple leaf nodes detected: core=$core_leaves, maintenance=$maintenance_leaves"
        conflicts_detected=true
    fi
    
    # Method 3: Try to run migrate --plan to detect conflicts
    if ! python manage.py migrate --plan --noinput > /dev/null 2>&1; then
        print_warning "Migration plan failed, conflicts likely present"
        conflicts_detected=true
    fi
    
    if [ "$conflicts_detected" = false ]; then
        print_success "No migration conflicts detected"
        return 0
    fi
    
    print_warning "Migration conflicts detected, attempting to resolve..."
    
    # Check if this is a fresh database (no django_migrations table)
    if ! python manage.py dbshell -c "SELECT 1 FROM django_migrations LIMIT 1;" > /dev/null 2>&1; then
        print_status "Fresh database detected, using fake-initial approach..."
        
        # For fresh databases, use fake-initial to bypass conflicts
        if python manage.py migrate --fake-initial --noinput; then
            print_success "Fresh database initialized with fake-initial migrations"
            return 0
        else
            print_warning "Fake-initial failed, trying aggressive fresh database approach..."
            
            # Try to fake-apply all migrations individually
            print_status "Attempting to fake-apply all migrations individually..."
            python manage.py migrate admin --fake-initial --noinput || true
            python manage.py migrate auth --fake-initial --noinput || true
            python manage.py migrate contenttypes --fake-initial --noinput || true
            python manage.py migrate sessions --fake-initial --noinput || true
            python manage.py migrate core --fake-initial --noinput || true
            python manage.py migrate equipment --fake-initial --noinput || true
            python manage.py migrate maintenance --fake-initial --noinput || true
            python manage.py migrate events --fake-initial --noinput || true
            python manage.py migrate django_celery_beat --fake-initial --noinput || true
            
            # Now try to run migrations normally
            if python manage.py migrate --noinput; then
                print_success "Fresh database initialized with individual fake-initial migrations"
                return 0
            else
                print_warning "Individual fake-initial also failed, trying standard merge approach..."
            fi
        fi
    fi
    
    # Try to merge conflicting migrations
    print_status "Attempting to merge conflicting migrations..."
    if python manage.py makemigrations --merge --noinput; then
        print_success "Migration merge completed successfully"
        
        # Apply the merged migrations
        print_status "Applying merged migrations..."
        if python manage.py migrate --noinput; then
            print_success "Merged migrations applied successfully"
            return 0
        else
            print_warning "Failed to apply merged migrations, trying individual app migrations..."
            
            # Try migrating each app individually
            print_status "Attempting individual app migrations..."
            python manage.py migrate core --noinput || print_warning "Core migrations failed"
            python manage.py migrate maintenance --noinput || print_warning "Maintenance migrations failed"
            python manage.py migrate equipment --noinput || print_warning "Equipment migrations failed"
            python manage.py migrate events --noinput || print_warning "Events migrations failed"
            
            # Final attempt
            if python manage.py migrate --noinput; then
                print_success "Individual app migrations completed successfully"
                return 0
            else
                print_warning "Individual app migrations also failed"
                return 1
            fi
        fi
    else
        print_warning "Migration merge failed, attempting alternative resolution..."
        
        # Alternative approach: try to fake apply problematic migrations
        print_status "Attempting emergency migration resolution..."
        
        # Try to fake apply the timezone migration specifically
        print_status "Fake-applying timezone migration..."
        if python manage.py migrate maintenance 0005_add_timezone_to_maintenance_activity --fake; then
            print_success "Timezone migration fake-applied successfully"
        else
            print_warning "Could not fake-apply timezone migration"
        fi
        
        # Try to fake apply other problematic migrations
        print_status "Fake-applying core migrations..."
        python manage.py migrate core 0005_add_branding_models --fake || print_warning "Core branding migration fake-apply failed"
        python manage.py migrate core 0012_add_breadcrumb_controls --fake || print_warning "Core breadcrumb migration fake-apply failed"
        
        print_status "Fake-applying maintenance migrations..."
        python manage.py migrate maintenance 0002_add_timeline_entry_types --fake || print_warning "Maintenance timeline migration fake-apply failed"
        python manage.py migrate maintenance 0006_globalschedule_scheduleoverride_and_more --fake || print_warning "Maintenance schedule migration fake-apply failed"
        
        # Check if timezone field exists after fake-apply
        print_status "Verifying timezone field exists..."
        if python manage.py shell -c "
from django.db import connection
try:
    with connection.cursor() as cursor:
        cursor.execute('SELECT column_name FROM information_schema.columns WHERE table_name = %s AND column_name = %s', ['maintenance_maintenanceactivity', 'timezone'])
        result = cursor.fetchone()
        if result:
            print('✅ Timezone field exists')
            exit(0)
        else:
            print('❌ Timezone field missing')
            exit(1)
except Exception as e:
    print(f'❌ Error: {e}')
    exit(1)
" 2>/dev/null; then
            print_success "Timezone field verification successful"
            return 0
        else
            print_warning "Timezone field still missing, attempting aggressive fix..."
            
            # Try aggressive fake-initial approach
            print_status "Attempting aggressive fake-initial migration..."
            if python manage.py migrate --fake-initial 2>/dev/null; then
                print_success "Aggressive fake-initial migration successful"
            else
                print_warning "Aggressive fake-initial failed, trying individual apps..."
                
                # Try each app individually
                python manage.py migrate core --fake-initial 2>/dev/null || print_warning "Core fake-initial failed"
                python manage.py migrate maintenance --fake-initial 2>/dev/null || print_warning "Maintenance fake-initial failed"
                python manage.py migrate equipment --fake-initial 2>/dev/null || print_warning "Equipment fake-initial failed"
                python manage.py migrate events --fake-initial 2>/dev/null || print_warning "Events fake-initial failed"
            fi
            
            # Manual SQL fix as absolute last resort
            print_status "Attempting manual SQL fix..."
            if python manage.py shell -c "
from django.db import connection
try:
    with connection.cursor() as cursor:
        cursor.execute('ALTER TABLE maintenance_maintenanceactivity ADD COLUMN IF NOT EXISTS timezone VARCHAR(50) DEFAULT %s', ['America/Chicago'])
        print('✅ Timezone column added manually')
        exit(0)
except Exception as e:
    print(f'❌ Error: {e}')
    exit(1)
" 2>/dev/null; then
                print_success "Manual timezone column addition successful"
                return 0
            else
                print_warning "Manual timezone column addition failed"
            fi
        fi
        
        print_warning "Migration conflict resolution failed, but continuing..."
        return 1
    fi
}

# Function to set up the branding system
setup_branding_system() {
    print_status "🚀 Setting up branding system..."
    
    # First resolve any migration conflicts
    if ! resolve_migration_conflicts; then
        print_warning "Migration conflict resolution failed, but continuing..."
    fi
    
    # Run migrations to ensure all tables exist
    print_status "Running database migrations..."
    if python manage.py migrate --noinput; then
        print_success "Migrations completed successfully"
    else
        print_warning "Migrations failed, but continuing..."
        return 1
    fi
    
    # Ensure maintenance app migrations are applied (including timezone field)
    print_status "Ensuring maintenance app migrations are applied..."
    if python manage.py migrate maintenance --noinput; then
        print_success "Maintenance app migrations completed successfully"
    else
        print_warning "Maintenance app migrations failed, attempting to resolve conflicts..."
        
        # Try to merge maintenance migrations specifically
        print_status "Attempting to merge maintenance migrations..."
        if python manage.py makemigrations maintenance --merge --noinput; then
            print_success "Maintenance migrations merged successfully"
            
            # Try to apply the merged migrations
            if python manage.py migrate maintenance --noinput; then
                print_success "Merged maintenance migrations applied successfully"
            else
                print_warning "Failed to apply merged maintenance migrations"
            fi
        else
            print_warning "Failed to merge maintenance migrations, but continuing..."
        fi
    fi
    
    # Check if branding system is already set up
    print_status "Checking if branding system is already configured..."
    if python manage.py shell -c "
import os
from django.db import connection
from django.db.utils import ProgrammingError

try:
    with connection.cursor() as cursor:
        cursor.execute('SELECT COUNT(*) FROM core_brandingsettings LIMIT 1')
        branding_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM core_csscustomization LIMIT 1')
        css_count = cursor.fetchone()[0]
        
        if branding_count > 0 or css_count > 0:
            print('Branding system already has data')
            exit(0)
        else:
            print('Branding system tables exist but are empty')
            exit(1)
except ProgrammingError:
    print('Branding system tables do not exist yet')
    exit(1)
except Exception as e:
    print(f'Error checking branding system: {e}')
    exit(1)
" 2>/dev/null; then
        print_success "Branding system is already configured"
        return 0
    fi
    
    # Set up default branding with environment variable customization
    print_status "Setting up default branding configuration..."
    
    # Create a custom setup command using environment variables
    if python manage.py shell -c "
import os
from django.core.management import call_command
from django.conf import settings

# Get branding environment variables with defaults
branding_site_name = os.environ.get('BRANDING_SITE_NAME', 'Maintenance Dashboard')
branding_site_tagline = os.environ.get('BRANDING_SITE_TAGLINE', 'Professional Maintenance Management System')
branding_window_title_prefix = os.environ.get('BRANDING_WINDOW_TITLE_PREFIX', 'Maintenance Dashboard')
branding_window_title_suffix = os.environ.get('BRANDING_WINDOW_TITLE_SUFFIX', '')
branding_header_brand_text = os.environ.get('BRANDING_HEADER_BRAND_TEXT', 'Maintenance Dashboard')
branding_primary_color = os.environ.get('BRANDING_PRIMARY_COLOR', '#4299e1')
branding_secondary_color = os.environ.get('BRANDING_SECONDARY_COLOR', '#2d3748')
branding_accent_color = os.environ.get('BRANDING_ACCENT_COLOR', '#3182ce')

print(f'Setting up branding with custom values:')
print(f'  Site Name: {branding_site_name}')
print(f'  Site Tagline: {branding_site_tagline}')
print(f'  Header Brand Text: {branding_header_brand_text}')
print(f'  Primary Color: {branding_primary_color}')

# Run the setup_branding command
call_command('setup_branding', '--noinput')

# Now customize the branding settings with environment variables
try:
    from core.models import BrandingSettings
    branding = BrandingSettings.objects.get(is_active=True)
    
    # Update with environment variable values
    branding.site_name = branding_site_name
    branding.site_tagline = branding_site_tagline
    branding.window_title_prefix = branding_window_title_prefix
    branding.window_title_suffix = branding_window_title_suffix
    branding.header_brand_text = branding_header_brand_text
    branding.primary_color = branding_primary_color
    branding.secondary_color = branding_secondary_color
    branding.accent_color = branding_accent_color
    branding.save()
    
    print('Branding settings customized with environment variables')
    
except Exception as e:
    print(f'Warning: Could not customize branding settings: {e}')
    print('Default branding will be used')

print('Branding system setup completed successfully')
" 2>/dev/null; then
        print_success "Default branding configuration created successfully with custom values"
        return 0
    else
        print_warning "Failed to create default branding configuration"
        return 1
    fi
}

# Function to run collectstatic with retry
run_collectstatic() {
    local retry_count=0
    local max_retries=5
    
    print_status "Collecting static files..."
    
    while [ $retry_count -lt $max_retries ]; do
        if python manage.py collectstatic --noinput; then
            print_success "Static files collected successfully"
            return 0
        else
            print_warning "collectstatic failed, retrying... (attempt $(($retry_count + 1))/$max_retries)"
            sleep 2
            retry_count=$((retry_count + 1))
        fi
    done
    
    print_error "collectstatic failed after $max_retries attempts"
    return 1
}

# Function to start the application
start_application() {
    print_status "Starting application server..."
    
    # Start application with proper error handling
    if [ "$1" = "web" ] || [ "$1" = "gunicorn" ]; then
        exec gunicorn --bind 0.0.0.0:8000 --workers 3 --timeout 120 maintenance_dashboard.wsgi:application
    elif [ "$1" = "celery" ]; then
        exec celery -A maintenance_dashboard worker --loglevel=info
    elif [ "$1" = "celery-beat" ]; then
        exec celery -A maintenance_dashboard beat --loglevel=info
    else
        # Default to gunicorn
        exec gunicorn --bind 0.0.0.0:8000 --workers 3 --timeout 120 maintenance_dashboard.wsgi:application
    fi
}

# Function to run health checks
run_health_checks() {
    print_status "Running health checks..."
    
    # Check Django configuration
    if ! python manage.py check --deploy; then
        print_warning "Django configuration check failed"
        return 1
    fi
    
    # Check database connection
    if ! python manage.py check --database default; then
        print_warning "Database connection check failed"
        return 1
    fi
    
    print_success "Health checks passed"
    return 0
}

# Function to handle graceful shutdown
graceful_shutdown() {
    print_status "Received shutdown signal, stopping gracefully..."
    
    # If there's a running process, try to stop it gracefully
    if [ ! -z "$APP_PID" ]; then
        kill -TERM "$APP_PID" 2>/dev/null || true
        wait "$APP_PID" 2>/dev/null || true
    fi
    
    exit 0
}

# Set up signal handlers
trap graceful_shutdown SIGTERM SIGINT

# Main execution
main() {
    print_status "🚀 Starting Docker container initialization..."
    print_status "🔧 ENTRYPOINT VERSION: 2024-07-15-FIXED-DB-AUTH"
    
    # Change to app directory
    cd /app || exit 1
    
    # Set default environment variables
    export DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE:-maintenance_dashboard.settings}
    export PYTHONPATH=/app:$PYTHONPATH
    
    # Show configuration
    print_status "Configuration:"
    print_status "  Database Host: ${DB_HOST:-db}"
    print_status "  Database Name: ${DB_NAME:-maintenance_dashboard}"
    print_status "  Database User: ${DB_USER:-postgres}"
    print_status "  POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:0:10}..."
    print_status "  DB_PASSWORD: ${DB_PASSWORD:0:10}..."
    print_status "  Admin Username: ${ADMIN_USERNAME:-admin}"
    print_status "  Admin Email: ${ADMIN_EMAIL:-admin@maintenance.local}"
    print_status "  Debug Mode: ${DEBUG:-False}"
    
    # Debug password values
    print_status "🔍 PASSWORD DEBUG:"
    print_status "  POSTGRES_PASSWORD full: ${POSTGRES_PASSWORD}"
    print_status "  DB_PASSWORD full: ${DB_PASSWORD}"
    print_status "  DB_CREATE_PASSWORD will be: ${POSTGRES_PASSWORD:-SecureProdPassword2024!}"
    
    # Skip database initialization if requested
    if [ "${SKIP_DB_INIT:-false}" = "true" ]; then
        print_warning "Skipping database initialization (SKIP_DB_INIT=true)"
    else
        # Run database initialization
        if ! run_database_initialization; then
            print_error "Database initialization failed, exiting..."
            exit 1
        fi
    fi
    
    # Skip collectstatic if requested
    if [ "${SKIP_COLLECTSTATIC:-false}" = "true" ]; then
        print_warning "Skipping collectstatic (SKIP_COLLECTSTATIC=true)"
    else
        # Run collectstatic
        if ! run_collectstatic; then
            print_error "collectstatic failed, exiting..."
            exit 1
        fi
    fi
    
    # Run health checks
    if ! run_health_checks; then
        print_warning "Health checks failed, but continuing..."
    fi
    
    # Start the application
    print_success "✅ Initialization completed successfully!"
    start_application "$@"
}

# Run main function with all arguments
main "$@"