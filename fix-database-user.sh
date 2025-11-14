#!/bin/bash
# Database User Fix Script for Portainer
# Run this script to manually create the maintenance_user in PostgreSQL

set -e

# Configuration
DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-maintenance_dashboard_prod}"
DB_USER="${DB_USER:-maintenance_user}"
DB_PASSWORD="${DB_PASSWORD:-SecureProdPassword2024!}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-SecureProdPassword2024!}"

echo "🔧 Fixing database user authentication issue..."

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
for i in {1..30}; do
    if PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "postgres" -d "postgres" -c "SELECT 1;" > /dev/null 2>&1; then
        echo "✅ PostgreSQL ready"
        break
    fi
    sleep 1
done

# Check if user exists
echo "🔍 Checking if user '$DB_USER' exists..."
user_exists=$(PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "postgres" -d "postgres" -t -c "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER';" 2>/dev/null | xargs)

if [ "$user_exists" = "1" ]; then
    echo "✅ User '$DB_USER' already exists"
else
    echo "👤 Creating user '$DB_USER'..."
    
    # Create user
    PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "postgres" -d "postgres" -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"
    
    # Grant privileges
    PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "postgres" -d "postgres" -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"
    PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "postgres" -d "$DB_NAME" -c "GRANT ALL PRIVILEGES ON SCHEMA public TO $DB_USER;"
    PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "postgres" -d "$DB_NAME" -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $DB_USER;"
    PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "postgres" -d "$DB_NAME" -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $DB_USER;"
    
    echo "✅ User '$DB_USER' created successfully"
fi

# Test connection
echo "🧪 Testing connection as '$DB_USER'..."
if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" > /dev/null 2>&1; then
    echo "✅ Connection test successful!"
    echo "🎉 Database user fix completed successfully!"
else
    echo "❌ Connection test failed"
    exit 1
fi
