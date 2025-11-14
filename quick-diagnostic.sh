#!/bin/bash
# Quick Database Diagnostic Script
# Run this in your application container to diagnose the connection issue

echo "🔍 QUICK DATABASE DIAGNOSTIC"
echo "============================"

# Show environment variables
echo "Environment variables:"
echo "DB_HOST: $DB_HOST"
echo "DB_PORT: $DB_PORT" 
echo "DB_NAME: $DB_NAME"
echo "DB_USER: $DB_USER"
echo "DB_PASSWORD: [HIDDEN]"
echo "POSTGRES_PASSWORD: [HIDDEN]"
echo ""

# Test PostgreSQL connection as postgres user
echo "Testing PostgreSQL connection as postgres user..."
if PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "postgres" -d "postgres" -c "SELECT version();" > /dev/null 2>&1; then
    echo "✅ PostgreSQL connection successful"
else
    echo "❌ PostgreSQL connection failed"
fi

# List databases
echo ""
echo "Available databases:"
PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "postgres" -d "postgres" -c "\l"

# List users
echo ""
echo "Available users:"
PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "postgres" -d "postgres" -c "\du"

# Test connection as configured user
echo ""
echo "Testing connection as configured user '$DB_USER'..."
if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT current_user;" > /dev/null 2>&1; then
    echo "✅ Connection as $DB_USER successful"
else
    echo "❌ Connection as $DB_USER failed"
fi

echo ""
echo "Diagnostic complete!"
