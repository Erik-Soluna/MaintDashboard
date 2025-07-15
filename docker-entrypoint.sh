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
    else
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
        print_status "  Testing with user: postgres"
        print_status "  Testing with password: ${POSTGRES_PASSWORD:0:10}..."
        
        if PGPASSWORD="$POSTGRES_PASSWORD" psql -h "${DB_HOST:-db}" -p "${DB_PORT:-5432}" -U "postgres" -d "postgres" -c "SELECT version();" > /dev/null 2>&1; then
            print_success "✅ Direct postgres connection successful!"
        else
            print_error "❌ Direct postgres connection failed!"
            print_status "  Trying to connect with default password..."
            if PGPASSWORD="SecureProdPassword2024!" psql -h "${DB_HOST:-db}" -p "${DB_PORT:-5432}" -U "postgres" -d "postgres" -c "SELECT version();" > /dev/null 2>&1; then
                print_success "✅ Direct postgres connection successful with default password!"
            else
                print_error "❌ Direct postgres connection failed with default password too!"
            fi
        fi
        
        # Ensure database exists
        if ! ensure_database_exists; then
            print_warning "Database creation failed, retrying in $RETRY_DELAY seconds..."
            sleep $RETRY_DELAY
            retry_count=$((retry_count + 1))
            continue
        fi
        
        # Run database initialization
        print_status "Running Django database initialization..."
        if python manage.py init_database \
            --admin-username "${ADMIN_USERNAME:-admin}" \
            --admin-email "${ADMIN_EMAIL:-admin@maintenance.local}" \
            --admin-password "${ADMIN_PASSWORD:-temppass123}"; then
            print_success "Database initialization completed successfully!"
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