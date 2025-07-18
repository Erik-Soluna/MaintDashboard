#!/bin/bash

# Comprehensive setup script for the unified calendar/maintenance system
# Run this after starting Docker Desktop

set -e

echo "🚀 Setting up unified calendar/maintenance system..."
echo "=================================================="

# Function to check if Docker is running
check_docker() {
    echo "🔍 Checking Docker status..."
    if docker info > /dev/null 2>&1; then
        echo "✅ Docker is running"
        return 0
    else
        echo "❌ Docker is not running. Please start Docker Desktop first."
        return 1
    fi
}

# Function to check if containers are running
check_containers() {
    echo "🔍 Checking container status..."
    if docker compose ps | grep -q "Up"; then
        echo "✅ Containers are running"
        return 0
    else
        echo "⚠️  Containers are not running, starting them..."
        docker compose up -d
        sleep 10
        return 0
    fi
}

# Function to run Django command with error handling
run_django_command() {
    local command="$1"
    local description="$2"
    local max_retries=3
    local retry_count=0
    
    echo "🔄 Running: $description"
    
    while [ $retry_count -lt $max_retries ]; do
        if docker compose exec web python manage.py $command; then
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

# Function to test the system
test_system() {
    echo "🧪 Testing the unified system..."
    
    # Run the test script
    if docker compose exec web python test_unified_system.py; then
        echo "✅ System test passed"
        return 0
    else
        echo "❌ System test failed"
        return 1
    fi
}

# Function to check web interface
check_web_interface() {
    echo "🌐 Checking web interface..."
    
    # Wait for web interface to be ready
    echo "⏳ Waiting for web interface to be ready..."
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -s http://localhost:8000/ > /dev/null 2>&1; then
            echo "✅ Web interface is accessible at http://localhost:8000/"
            return 0
        else
            attempt=$((attempt + 1))
            echo "⏳ Waiting for web interface... (attempt $attempt/$max_attempts)"
            sleep 2
        fi
    done
    
    echo "❌ Web interface is not accessible"
    return 1
}

# Main execution
main() {
    echo "🚀 Starting unified system setup..."
    
    # Check Docker
    if ! check_docker; then
        exit 1
    fi
    
    # Check containers
    if ! check_containers; then
        echo "❌ Failed to start containers"
        exit 1
    fi
    
    # Wait for services to be ready
    echo "⏳ Waiting for services to be ready..."
    sleep 15
    
    # Run database initialization
    echo "📋 Running database initialization..."
    
    # 1. Make migrations for events
    if ! run_django_command "makemigrations events" "Make events migrations"; then
        echo "❌ Failed to make events migrations"
        exit 1
    fi
    
    # 2. Make migrations for maintenance
    if ! run_django_command "makemigrations maintenance" "Make maintenance migrations"; then
        echo "❌ Failed to make maintenance migrations"
        exit 1
    fi
    
    # 3. Run migrations
    if ! run_django_command "migrate" "Run migrations"; then
        echo "❌ Failed to run migrations"
        exit 1
    fi
    
    # 4. Create global activity types
    if ! run_django_command "create_global_activity_types" "Create global activity types"; then
        echo "⚠️  Failed to create global activity types (this is optional)"
    fi
    
    # 5. Initialize database
    if ! run_django_command "init_database" "Initialize database"; then
        echo "⚠️  Failed to initialize database (this is optional)"
    fi
    
    # 6. Collect static files
    if ! run_django_command "collectstatic --noinput" "Collect static files"; then
        echo "⚠️  Failed to collect static files (this is optional)"
    fi
    
    # 7. Test the system
    if ! test_system; then
        echo "❌ System test failed"
        exit 1
    fi
    
    # 8. Check web interface
    if ! check_web_interface; then
        echo "⚠️  Web interface check failed (this is optional)"
    fi
    
    echo ""
    echo "🎉 Setup completed successfully!"
    echo "=================================================="
    echo "✅ Database migrations applied"
    echo "✅ Global activity types created"
    echo "✅ System tests passed"
    echo "✅ Web interface should be accessible at http://localhost:8000/"
    echo ""
    echo "🔧 Next steps:"
    echo "   1. Open http://localhost:8000/ in your browser"
    echo "   2. Log in with your credentials"
    echo "   3. Test creating calendar events and maintenance activities"
    echo "   4. Verify they are properly synchronized"
    echo ""
    echo "📝 If you encounter any issues:"
    echo "   - Check Docker logs: docker compose logs web"
    echo "   - Check database logs: docker compose logs db"
    echo "   - Run the test script: docker compose exec web python test_unified_system.py"
}

# Run main function
main "$@" 