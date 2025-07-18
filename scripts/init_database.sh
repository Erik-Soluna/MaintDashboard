#!/bin/bash

# Database Initialization Script for Maintenance Dashboard
# This script automates database setup and admin user creation

set -e  # Exit on any error

echo "🚀 Starting Maintenance Dashboard Database Initialization..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values (can be overridden by environment variables)
ADMIN_USERNAME=${ADMIN_USERNAME:-admin}
ADMIN_EMAIL=${ADMIN_EMAIL:-admin@maintenance.local}
ADMIN_PASSWORD=${ADMIN_PASSWORD:-temppass123}
SKIP_MIGRATIONS=${SKIP_MIGRATIONS:-false}
SKIP_ADMIN=${SKIP_ADMIN:-false}
SKIP_SAMPLE_DATA=${SKIP_SAMPLE_DATA:-false}

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

# Function to check if database is accessible
check_database() {
    print_status "Checking database connection..."
    
    # Try to connect to database
    python manage.py check --database default > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        print_success "Database connection successful"
        return 0
    else
        print_error "Database connection failed"
        return 1
    fi
}

# Function to wait for database to be ready
wait_for_database() {
    print_status "Waiting for database to be ready..."
    
    max_attempts=30
    attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if check_database; then
            print_success "Database is ready"
            return 0
        fi
        
        print_status "Database not ready, waiting... (attempt $attempt/$max_attempts)"
        sleep 2
        attempt=$((attempt + 1))
    done
    
    print_error "Database did not become ready within timeout"
    exit 1
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -u, --username USERNAME     Admin username (default: admin)"
    echo "  -e, --email EMAIL          Admin email (default: admin@maintenance.local)"
    echo "  -p, --password PASSWORD    Admin password (default: temppass123)"
    echo "  --skip-migrations          Skip running migrations"
    echo "  --skip-admin              Skip creating admin user"
    echo "  --skip-sample-data        Skip creating sample data"
    echo "  -h, --help                Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  ADMIN_USERNAME            Admin username"
    echo "  ADMIN_EMAIL              Admin email"
    echo "  ADMIN_PASSWORD           Admin password"
    echo "  SKIP_MIGRATIONS          Set to 'true' to skip migrations"
    echo "  SKIP_ADMIN               Set to 'true' to skip admin creation"
    echo "  SKIP_SAMPLE_DATA         Set to 'true' to skip sample data"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -u|--username)
            ADMIN_USERNAME="$2"
            shift 2
            ;;
        -e|--email)
            ADMIN_EMAIL="$2"
            shift 2
            ;;
        -p|--password)
            ADMIN_PASSWORD="$2"
            shift 2
            ;;
        --skip-migrations)
            SKIP_MIGRATIONS=true
            shift
            ;;
        --skip-admin)
            SKIP_ADMIN=true
            shift
            ;;
        --skip-sample-data)
            SKIP_SAMPLE_DATA=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Check if manage.py exists
if [ ! -f "manage.py" ]; then
    print_error "manage.py not found. Please run this script from the Django project root."
    exit 1
fi

# Wait for database to be ready
wait_for_database

# Build Django management command arguments
cmd_args=""
if [ "$SKIP_MIGRATIONS" = "true" ]; then
    cmd_args="$cmd_args --skip-migrations"
fi
if [ "$SKIP_ADMIN" = "true" ]; then
    cmd_args="$cmd_args --skip-admin"
fi
if [ "$SKIP_SAMPLE_DATA" = "true" ]; then
    cmd_args="$cmd_args --skip-sample-data"
fi

# Add admin user details
cmd_args="$cmd_args --admin-username '$ADMIN_USERNAME'"
cmd_args="$cmd_args --admin-email '$ADMIN_EMAIL'"
cmd_args="$cmd_args --admin-password '$ADMIN_PASSWORD'"

print_status "Running Django database initialization command..."
print_status "Command: python manage.py init_database $cmd_args"

# Run the Django management command
eval "python manage.py init_database $cmd_args"

if [ $? -eq 0 ]; then
    print_success "Database initialization completed successfully!"
    
    if [ "$SKIP_ADMIN" != "true" ]; then
        echo ""
        print_warning "📋 ADMIN USER DETAILS:"
        print_warning "   Username: $ADMIN_USERNAME"
        print_warning "   Email: $ADMIN_EMAIL"
        print_warning "   Password: $ADMIN_PASSWORD"
        echo ""
        print_warning "🔒 SECURITY NOTE:"
        print_warning "   The admin user will be required to change password on first login."
        print_warning "   Please log in and change the password immediately for security."
    fi
    
    echo ""
    print_success "✅ Maintenance Dashboard is ready to use!"
    
else
    print_error "Database initialization failed!"
    exit 1
fi