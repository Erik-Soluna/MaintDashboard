#!/bin/bash

# Clean Docker Entrypoint Script for Maintenance Dashboard
# Version: 2024-09-02-CLEAN-SLATE
# Purpose: Simple, reliable database initialization for fresh deployments

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

# Main initialization function
main() {
    print_status "🚀 Starting clean database initialization..."
    print_status "🔧 ENTRYPOINT VERSION: 2024-09-02-CLEAN-SLATE"
    
    # Configuration
    DB_HOST="${DB_HOST:-db}"
    DB_PORT="${DB_PORT:-5432}"
    DB_NAME="${DB_NAME:-maintenance_dashboard}"
    DB_USER="${DB_USER:-maintenance_user}"
    DB_PASSWORD="${DB_PASSWORD:-SecureProdPassword2024!}"
    POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-SecureProdPassword2024!}"
    ADMIN_USERNAME="${ADMIN_USERNAME:-admin}"
    ADMIN_EMAIL="${ADMIN_EMAIL:-admin@maintenance.local}"
    ADMIN_PASSWORD="${ADMIN_PASSWORD:-temppass123}"
    
    print_status "Configuration:"
    print_status "  Database Host: $DB_HOST"
    print_status "  Database Name: $DB_NAME"
    print_status "  Database User: $DB_USER"
    print_status "  Admin Username: $ADMIN_USERNAME"
    print_status "  Admin Email: $ADMIN_EMAIL"
    
    # Step 1: Wait for database to be ready
    print_status "⏳ Waiting for database to be ready..."
    wait_for_database
    
    # Step 2: Ensure database exists
    print_status "🗄️ Ensuring database exists..."
    ensure_database_exists
    
    # Step 3: Initialize database
    print_status "🔧 Initializing database..."
    initialize_database
    
    # Step 4: Start the application
    print_status "🚀 Starting application..."
    exec "$@"
}

# Wait for database to be ready
wait_for_database() {
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        print_status "Database connection attempt $attempt/$max_attempts..."
        
        if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" > /dev/null 2>&1; then
            print_success "✅ Database connection successful!"
            return 0
        fi
        
        print_warning "Database not ready, waiting 2 seconds..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    print_error "❌ Database connection failed after $max_attempts attempts"
    exit 1
}

# Ensure database exists
ensure_database_exists() {
    # Try to connect to the target database
    if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" > /dev/null 2>&1; then
        print_success "✅ Database '$DB_NAME' already exists"
        return 0
    fi
    
    print_status "Database '$DB_NAME' does not exist, creating it..."
    
    # Try to create database using postgres superuser
    if PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "postgres" -d "postgres" -c "CREATE DATABASE \"$DB_NAME\";" > /dev/null 2>&1; then
        print_success "✅ Database '$DB_NAME' created successfully"
        return 0
    fi
    
    # Try to create database using the application user
    if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "postgres" -c "CREATE DATABASE \"$DB_NAME\";" > /dev/null 2>&1; then
        print_success "✅ Database '$DB_NAME' created successfully"
        return 0
    fi
    
    print_error "❌ Failed to create database '$DB_NAME'"
    exit 1
}

# Initialize database
initialize_database() {
    # Check if this is a fresh database
    if ! echo "SELECT 1 FROM django_migrations LIMIT 1;" | python manage.py dbshell > /dev/null 2>&1; then
        print_status "🆕 Fresh database detected - using clean initialization"
        initialize_fresh_database
    else
        print_status "🔄 Existing database detected - running migrations"
        run_migrations
    fi
    
    # Create admin user and initial data
    print_status "👤 Creating admin user and initial data..."
    python manage.py init_database \
        --admin-username "$ADMIN_USERNAME" \
        --admin-email "$ADMIN_EMAIL" \
        --admin-password "$ADMIN_PASSWORD" \
        --force
    
    print_success "✅ Database initialization completed successfully!"
}

# Initialize fresh database
initialize_fresh_database() {
    print_status "🧹 Cleaning migration files for fresh start..."
    
    # Backup existing migrations
    mkdir -p /tmp/migration_backup
    cp -r */migrations /tmp/migration_backup/ 2>/dev/null || true
    
    # Remove all migration files except __init__.py
    find . -path "*/migrations/*.py" -not -name "__init__.py" -delete 2>/dev/null || true
    find . -path "*/migrations/*.pyc" -delete 2>/dev/null || true
    
    print_status "📝 Creating fresh initial migrations..."
    if python manage.py makemigrations --noinput; then
        print_success "✅ Fresh migrations created successfully"
    else
        print_error "❌ Failed to create fresh migrations"
        exit 1
    fi
    
    print_status "🚀 Applying fresh migrations..."
    if python manage.py migrate --noinput; then
        print_success "✅ Fresh database initialized successfully"
    else
        print_error "❌ Failed to apply fresh migrations"
        exit 1
    fi
}

# Run migrations for existing database
run_migrations() {
    print_status "🔄 Running database migrations..."
    if python manage.py migrate --noinput; then
        print_success "✅ Migrations completed successfully"
    else
        print_error "❌ Migrations failed"
        exit 1
    fi
}

# Run main function
main "$@"
