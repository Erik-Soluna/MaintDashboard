#!/bin/bash
# Permanent Database Initialization Script
# This script ensures the maintenance_dashboard database exists
# regardless of PostgreSQL container restart status

set -e

# Configuration
DB_NAME="maintenance_dashboard"
DB_USER="postgres"
DB_PASSWORD="postgres"
DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"
MAX_RETRIES=30
RETRY_DELAY=2

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

# Function to wait for PostgreSQL to be ready
wait_for_postgres() {
    local retry_count=0
    
    print_status "Waiting for PostgreSQL to be ready..."
    
    while [ $retry_count -lt $MAX_RETRIES ]; do
        if PGPASSWORD="$DB_PASSWORD" pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" > /dev/null 2>&1; then
            print_success "PostgreSQL is ready"
            return 0
        fi
        
        print_status "PostgreSQL not ready, waiting... (attempt $((retry_count + 1))/$MAX_RETRIES)"
        sleep $RETRY_DELAY
        retry_count=$((retry_count + 1))
    done
    
    print_error "PostgreSQL did not become ready within timeout"
    return 1
}

# Function to check if database exists
database_exists() {
    local result
    result=$(PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "postgres" -t -c "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" 2>/dev/null | xargs)
    [ "$result" = "1" ]
}

# Function to create database
create_database() {
    print_status "Creating database '$DB_NAME'..."
    
    if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "postgres" -c "CREATE DATABASE $DB_NAME" > /dev/null 2>&1; then
        print_success "Database '$DB_NAME' created successfully"
        return 0
    else
        print_error "Failed to create database '$DB_NAME'"
        return 1
    fi
}

# Function to list all databases (for debugging)
list_databases() {
    print_status "Current databases:"
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "postgres" -l 2>/dev/null || true
}

# Main function
main() {
    print_status "🚀 Starting database initialization check..."
    print_status "Database: $DB_NAME"
    print_status "Host: $DB_HOST:$DB_PORT"
    print_status "User: $DB_USER"
    
    # Wait for PostgreSQL to be ready
    if ! wait_for_postgres; then
        exit 1
    fi
    
    # Check if database exists
    if database_exists; then
        print_success "✅ Database '$DB_NAME' already exists - no action needed"
        return 0
    fi
    
    # Database doesn't exist, create it
    print_warning "⚠️  Database '$DB_NAME' does not exist"
    
    if create_database; then
        print_success "✅ Database initialization completed successfully!"
        
        # Verify creation
        if database_exists; then
            print_success "✅ Database creation verified"
        else
            print_error "❌ Database creation failed verification"
            list_databases
            exit 1
        fi
    else
        print_error "❌ Database creation failed"
        list_databases
        exit 1
    fi
}

# Run main function
main "$@"