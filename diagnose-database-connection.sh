#!/bin/bash
# Database Connection Diagnostic Script
# This script will help diagnose why the authentication is still failing

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

echo "🔍 DATABASE CONNECTION DIAGNOSTIC SCRIPT"
echo "========================================"

# Configuration
DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-maintenance_dashboard_prod}"
DB_USER="${DB_USER:-postgres}"
DB_PASSWORD="${DB_PASSWORD:-SecureProdPassword2024!}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-SecureProdPassword2024!}"

print_status "Configuration being used:"
echo "  DB_HOST: $DB_HOST"
echo "  DB_PORT: $DB_PORT"
echo "  DB_NAME: $DB_NAME"
echo "  DB_USER: $DB_USER"
echo "  DB_PASSWORD: [HIDDEN]"
echo "  POSTGRES_PASSWORD: [HIDDEN]"
echo ""

# Step 1: Check if PostgreSQL is running
print_status "Step 1: Checking PostgreSQL connectivity..."
if PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "postgres" -d "postgres" -c "SELECT version();" > /dev/null 2>&1; then
    print_success "✅ PostgreSQL is running and accessible"
else
    print_error "❌ Cannot connect to PostgreSQL"
    exit 1
fi

# Step 2: List all databases
print_status "Step 2: Listing all databases..."
PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "postgres" -d "postgres" -c "\l"

# Step 3: List all users/roles
print_status "Step 3: Listing all database users/roles..."
PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "postgres" -d "postgres" -c "\du"

# Step 4: Check if target database exists
print_status "Step 4: Checking if target database '$DB_NAME' exists..."
if PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "postgres" -d "postgres" -c "SELECT 1 FROM pg_database WHERE datname='$DB_NAME';" | grep -q "1"; then
    print_success "✅ Database '$DB_NAME' exists"
else
    print_warning "⚠️  Database '$DB_NAME' does not exist"
    print_status "Creating database '$DB_NAME'..."
    PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "postgres" -d "postgres" -c "CREATE DATABASE $DB_NAME;"
    print_success "✅ Database '$DB_NAME' created"
fi

# Step 5: Test connection as postgres user
print_status "Step 5: Testing connection as postgres user..."
if PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "postgres" -d "$DB_NAME" -c "SELECT current_user, current_database();" > /dev/null 2>&1; then
    print_success "✅ Connection as postgres user successful"
else
    print_error "❌ Connection as postgres user failed"
fi

# Step 6: Test connection as configured DB_USER
print_status "Step 6: Testing connection as configured DB_USER '$DB_USER'..."
if [ "$DB_USER" = "postgres" ]; then
    if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT current_user, current_database();" > /dev/null 2>&1; then
        print_success "✅ Connection as $DB_USER user successful"
    else
        print_error "❌ Connection as $DB_USER user failed"
    fi
else
    # Check if user exists
    if PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "postgres" -d "postgres" -c "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER';" | grep -q "1"; then
        print_success "✅ User '$DB_USER' exists"
        if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT current_user, current_database();" > /dev/null 2>&1; then
            print_success "✅ Connection as $DB_USER user successful"
        else
            print_error "❌ Connection as $DB_USER user failed"
        fi
    else
        print_warning "⚠️  User '$DB_USER' does not exist"
    fi
fi

# Step 7: Check environment variables in container
print_status "Step 7: Checking environment variables..."
echo "Environment variables related to database:"
env | grep -E "(DB_|POSTGRES_)" | sort

# Step 8: Check Django settings
print_status "Step 8: Checking Django database settings..."
if command -v python > /dev/null 2>&1; then
    python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maintenance_dashboard.settings')
try:
    import django
    django.setup()
    from django.conf import settings
    print(f'DATABASES setting:')
    for db_name, db_config in settings.DATABASES.items():
        print(f'  {db_name}:')
        for key, value in db_config.items():
            if 'PASSWORD' in key:
                print(f'    {key}: [HIDDEN]')
            else:
                print(f'    {key}: {value}')
except Exception as e:
    print(f'Error checking Django settings: {e}')
"
else
    print_warning "⚠️  Python not available for Django settings check"
fi

print_status "Diagnostic complete!"
