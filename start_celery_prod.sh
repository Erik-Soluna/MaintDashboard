#!/bin/bash

# Production Celery startup script
set -e

echo "Starting Celery services in production mode..."

# Wait for database to be ready
echo "Waiting for database..."
until python manage.py check --database default 2>/dev/null; do
    echo "Database not ready, waiting..."
    sleep 2
done

# Wait for Redis to be ready
echo "Waiting for Redis..."
until python -c "import redis; redis.Redis(host='redis', port=6379, db=0).ping()"; do
    echo "Redis not ready, waiting..."
    sleep 2
done

# Wait for web service to be ready (simple check)
echo "Waiting for web service..."
until curl -f http://web:8000/core/health/simple/ > /dev/null 2>&1; do
    echo "Web service not ready, waiting..."
    sleep 5
done

# Start Celery worker with production settings
echo "Starting Celery worker..."
exec celery -A maintenance_dashboard worker --loglevel=info --concurrency=2 --max-tasks-per-child=1000 