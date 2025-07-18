#!/bin/bash

# Enhanced database initialization script
# Checks and creates all required tables including cache table

set -e

echo "🔧 Starting comprehensive database initialization..."

# Function to check if PostgreSQL is ready
wait_for_postgres() {
    echo "⏳ Waiting for PostgreSQL to be ready..."
    while ! pg_isready -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME; do
        echo "PostgreSQL is not ready yet. Waiting..."
        sleep 2
    done
    echo "✅ PostgreSQL is ready!"
}

# Function to check if Redis is ready
wait_for_redis() {
    echo "⏳ Waiting for Redis to be ready..."
    while ! redis-cli -h $REDIS_HOST -p $REDIS_PORT ping > /dev/null 2>&1; do
        echo "Redis is not ready yet. Waiting..."
        sleep 2
    done
    echo "✅ Redis is ready!"
}

# Function to run Django management commands with error handling
run_django_command() {
    local command="$1"
    local description="$2"
    local max_retries=3
    local retry_count=0
    
    echo "🔄 Running: $description"
    
    while [ $retry_count -lt $max_retries ]; do
        if python manage.py $command; then
            echo "✅ $description completed successfully"
            return 0
        else
            retry_count=$((retry_count + 1))
            echo "⚠️  $description failed (attempt $retry_count/$max_retries)"
            if [ $retry_count -lt $max_retries ]; then
                echo "🔄 Retrying in 5 seconds..."
                sleep 5
            fi
        fi
    done
    
    echo "❌ $description failed after $max_retries attempts"
    return 1
}

# Function to check if a table exists in PostgreSQL
check_table_exists() {
    local table_name="$1"
    local query="SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '$table_name');"
    local result=$(psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "$query" 2>/dev/null | tr -d ' ')
    echo $result
}

# Function to check required tables
check_required_tables() {
    echo "🔍 Checking required database tables..."
    
    local required_tables=(
        "django_migrations"
        "django_content_type"
        "django_admin_log"
        "django_session"
        "auth_user"
        "auth_group"
        "auth_permission"
        "core_customer"
        "core_equipmentcategory"
        "core_location"
        "core_permission"
        "core_role"
        "core_userprofile"
        "core_modeldocument"
        "equipment_equipment"
        "equipment_equipmentcomponent"
        "equipment_equipmentdocument"
        "maintenance_maintenanceactivity"
        "maintenance_maintenanceactivitytype"
        "maintenance_maintenanceactivitytypecategory"
        "maintenance_maintenanceschedule"
        "maintenance_maintenancereport"
        "events_calendarevent"
        "events_eventcomment"
        "events_eventattachment"
        "events_eventreminder"
        "django_celery_beat_periodictask"
        "django_celery_beat_periodictasks"
        "django_celery_beat_intervalschedule"
        "django_celery_beat_crontabschedule"
        "django_celery_beat_solarschedule"
        "django_celery_beat_clockedschedule"
    )
    
    local missing_tables=()
    
    for table in "${required_tables[@]}"; do
        if [ "$(check_table_exists $table)" = "t" ]; then
            echo "✅ Table $table exists"
        else
            echo "❌ Table $table is missing"
            missing_tables+=("$table")
        fi
    done
    
    # Check cache table specifically
    if [ "$(check_table_exists cache_table)" = "t" ]; then
        echo "✅ Cache table exists"
    else
        echo "❌ Cache table is missing"
        missing_tables+=("cache_table")
    fi
    
    if [ ${#missing_tables[@]} -eq 0 ]; then
        echo "✅ All required tables exist"
        return 0
    else
        echo "⚠️  Missing tables: ${missing_tables[*]}"
        return 1
    fi
}

# Function to create cache table
create_cache_table() {
    echo "🔧 Creating cache table..."
    if run_django_command "createcachetable" "Create cache table"; then
        echo "✅ Cache table created successfully"
        return 0
    else
        echo "⚠️  Failed to create cache table, trying alternative approach..."
        
        # Try to create cache table manually
        local create_cache_sql="
        CREATE TABLE IF NOT EXISTS cache_table (
            cache_key varchar(255) NOT NULL PRIMARY KEY,
            value text NOT NULL,
            expires timestamp(6) NOT NULL
        );
        CREATE INDEX IF NOT EXISTS cache_table_expires_idx ON cache_table (expires);
        "
        
        if psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "$create_cache_sql" > /dev/null 2>&1; then
            echo "✅ Cache table created manually"
            return 0
        else
            echo "❌ Failed to create cache table manually"
            return 1
        fi
    fi
}

# Function to test cache functionality
test_cache() {
    echo "🧪 Testing cache functionality..."
    
    # Create a test script
    cat > /tmp/test_cache.py << 'EOF'
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maintenance_dashboard.settings')
django.setup()

from django.core.cache import cache

try:
    # Test cache
    test_key = 'test_cache_key'
    test_value = 'test_cache_value'
    
    # Set value
    cache.set(test_key, test_value, 60)
    print("✅ Cache set successful")
    
    # Get value
    retrieved_value = cache.get(test_key)
    if retrieved_value == test_value:
        print("✅ Cache get successful")
    else:
        print(f"❌ Cache get failed: expected '{test_value}', got '{retrieved_value}'")
        sys.exit(1)
    
    # Delete value
    cache.delete(test_key)
    print("✅ Cache delete successful")
    
    # Verify deletion
    if cache.get(test_key) is None:
        print("✅ Cache deletion verified")
    else:
        print("❌ Cache deletion failed")
        sys.exit(1)
        
    print("🎉 Cache test completed successfully!")
    
except Exception as e:
    print(f"❌ Cache test failed: {str(e)}")
    sys.exit(1)
EOF

    if python /tmp/test_cache.py; then
        echo "✅ Cache functionality test passed"
        rm -f /tmp/test_cache.py
        return 0
    else
        echo "❌ Cache functionality test failed"
        rm -f /tmp/test_cache.py
        return 1
    fi
}

# Main execution
main() {
    echo "🚀 Starting enhanced database initialization..."
    
    # Wait for services
    wait_for_postgres
    wait_for_redis
    
    # Check if database needs initialization
    if check_required_tables; then
        echo "✅ All required tables exist, running migrations to ensure consistency..."
    else
        echo "🔄 Some tables are missing, running full initialization..."
    fi
    
    # Run Django commands in order
    echo "📋 Running Django initialization commands..."
    
    # 1. Make migrations
    run_django_command "makemigrations" "Make migrations"
    
    # 2. Run migrations
    run_django_command "migrate" "Run migrations"
    
    # 3. Create cache table
    create_cache_table
    
    # 4. Collect static files
    run_django_command "collectstatic --noinput" "Collect static files"
    
    # 5. Initialize database (custom command)
    run_django_command "init_database" "Initialize database"
    
    # 6. Test cache functionality
    test_cache
    
    # 7. Final table check
    echo "🔍 Final verification of required tables..."
    if check_required_tables; then
        echo "🎉 Database initialization completed successfully!"
        echo "✅ All required tables exist"
        echo "✅ Cache functionality working"
        echo "✅ Static files collected"
        echo "✅ Database initialized"
    else
        echo "❌ Database initialization completed with warnings"
        echo "⚠️  Some tables may still be missing"
        exit 1
    fi
}

# Run main function
main "$@" 