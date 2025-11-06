#!/bin/bash
# Quick Database Diagnostic Script
# Run this in your application container to diagnose the connection issue

echo "ðŸ” QUICK DATABASE DIAGNOSTIC"
echo "============================"

# Show environment variables
echo "Environment variables:"
echo "DB_HOST: "
echo "DB_PORT: " 
echo "DB_NAME: "
echo "DB_USER: "
echo "DB_PASSWORD: [HIDDEN]"
echo "POSTGRES_PASSWORD: [HIDDEN]"
echo ""

# Test PostgreSQL connection as postgres user
echo "Testing PostgreSQL connection as postgres user..."
if PGPASSWORD="" psql -h "" -p "" -U "postgres" -d "postgres" -c "SELECT version();" > /dev/null 2>&1; then
    echo "âœ… PostgreSQL connection successful"
else
    echo "âŒ PostgreSQL connection failed"
fi

# List databases
echo ""
echo "Available databases:"
PGPASSWORD="" psql -h "" -p "" -U "postgres" -d "postgres" -c "\l"

# List users
echo ""
echo "Available users:"
PGPASSWORD="" psql -h "" -p "" -U "postgres" -d "postgres" -c "\du"

# Test connection as configured user
echo ""
echo "Testing connection as configured user ''..."
if PGPASSWORD="" psql -h "" -p "" -U "" -d "" -c "SELECT current_user;" > /dev/null 2>&1; then
    echo "âœ… Connection as  successful"
else
    echo "âŒ Connection as  failed"
fi

echo ""
echo "Diagnostic complete!"
