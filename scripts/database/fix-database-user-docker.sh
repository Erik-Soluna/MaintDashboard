#!/bin/bash
# Fix Database User Authentication Issue (Docker Version)
# This script creates the maintenance_user in PostgreSQL and grants necessary permissions
# Designed to be run inside the database container

set -e

# Configuration - Use environment variables with fallbacks
DB_NAME="${DB_NAME:-maintenance_dashboard_prod}"
DB_USER="${DB_USER:-maintenance_user}"
DB_PASSWORD="${DB_PASSWORD:-SecureProdPassword2024!}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-postgres}"

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

# Function to check if maintenance_user exists
user_exists() {
    local result
    result=$(PGPASSWORD="$POSTGRES_PASSWORD" psql -U "$POSTGRES_USER" -d "postgres" -t -c "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" 2>/dev/null | xargs)
    [ "$result" = "1" ]
}

# Function to create maintenance_user
create_user() {
    print_status "Creating user '$DB_USER'..."
    
    # Create user with password
    if PGPASSWORD="$POSTGRES_PASSWORD" psql -U "$POSTGRES_USER" -d "postgres" -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" > /dev/null 2>&1; then
        print_success "User '$DB_USER' created successfully"
        return 0
    else
        print_error "Failed to create user '$DB_USER'"
        return 1
    fi
}

# Function to grant privileges to maintenance_user
grant_privileges() {
    print_status "Granting privileges to '$DB_USER'..."
    
    # Grant database privileges
    if PGPASSWORD="$POSTGRES_PASSWORD" psql -U "$POSTGRES_USER" -d "postgres" -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;" > /dev/null 2>&1; then
        print_success "Database privileges granted"
    else
        print_warning "Failed to grant database privileges"
    fi
    
    # Grant schema privileges
    if PGPASSWORD="$POSTGRES_PASSWORD" psql -U "$POSTGRES_USER" -d "$DB_NAME" -c "GRANT ALL PRIVILEGES ON SCHEMA public TO $DB_USER;" > /dev/null 2>&1; then
        print_success "Schema privileges granted"
    else
        print_warning "Failed to grant schema privileges"
    fi
    
    # Grant table privileges (for existing tables)
    if PGPASSWORD="$POSTGRES_PASSWORD" psql -U "$POSTGRES_USER" -d "$DB_NAME" -c "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $DB_USER;" > /dev/null 2>&1; then
        print_success "Table privileges granted"
    else
        print_warning "Failed to grant table privileges"
    fi
    
    # Grant sequence privileges
    if PGPASSWORD="$POSTGRES_PASSWORD" psql -U "$POSTGRES_USER" -d "$DB_NAME" -c "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO $DB_USER;" > /dev/null 2>&1; then
        print_success "Sequence privileges granted"
    else
        print_warning "Failed to grant sequence privileges"
    fi
    
    # Grant future table privileges
    if PGPASSWORD="$POSTGRES_PASSWORD" psql -U "$POSTGRES_USER" -d "$DB_NAME" -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $DB_USER;" > /dev/null 2>&1; then
        print_success "Future table privileges granted"
    else
        print_warning "Failed to grant future table privileges"
    fi
    
    # Grant future sequence privileges
    if PGPASSWORD="$POSTGRES_PASSWORD" psql -U "$POSTGRES_USER" -d "$DB_NAME" -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $DB_USER;" > /dev/null 2>&1; then
        print_success "Future sequence privileges granted"
    else
        print_warning "Failed to grant future sequence privileges"
    fi
}

# Function to test maintenance_user connection
test_user_connection() {
    print_status "Testing connection with '$DB_USER'..."
    
    if PGPASSWORD="$DB_PASSWORD" psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" > /dev/null 2>&1; then
        print_success "Connection test successful for '$DB_USER'"
        return 0
    else
        print_error "Connection test failed for '$DB_USER'"
        return 1
    fi
}

# Function to create database if it doesn't exist
create_database_if_missing() {
    print_status "Checking if database '$DB_NAME' exists..."
    
    # Check if database exists
    if PGPASSWORD="$POSTGRES_PASSWORD" psql -U "$POSTGRES_USER" -d "postgres" -t -c "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" | grep -q 1; then
        print_success "Database '$DB_NAME' already exists"
        return 0
    fi
    
    # Create database
    print_status "Creating database '$DB_NAME'..."
    if PGPASSWORD="$POSTGRES_PASSWORD" psql -U "$POSTGRES_USER" -d "postgres" -c "CREATE DATABASE $DB_NAME;" > /dev/null 2>&1; then
        print_success "Database '$DB_NAME' created successfully"
        return 0
    else
        print_error "Failed to create database '$DB_NAME'"
        return 1
    fi
}

# Main function
main() {
    print_status "🔧 Starting database user fix (Docker version)..."
    print_status "Database: $DB_NAME"
    print_status "User: $DB_USER"
    
    # Create database if it doesn't exist
    if ! create_database_if_missing; then
        exit 1
    fi
    
    # Check if maintenance_user exists
    if user_exists; then
        print_success "User '$DB_USER' already exists"
    else
        # Create maintenance_user
        if ! create_user; then
            exit 1
        fi
    fi
    
    # Grant privileges
    grant_privileges
    
    # Test connection
    if test_user_connection; then
        print_success "✅ Database user fix completed successfully!"
        print_status "The maintenance_user is now ready for use."
    else
        print_error "❌ Database user fix failed"
        exit 1
    fi
}

# Run main function
main "$@"