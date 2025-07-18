#!/bin/bash
# IMMEDIATE FIX - Run this script right now to fix the database issue
# This script will create the missing database and restart your web container

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Configuration
DB_NAME="maintenance_dashboard"
DB_USER="postgres"

# Auto-detect container names
print_status "Auto-detecting container names..."
DB_CONTAINER_NAME=$(docker ps --filter name="db" --format "{{.Names}}" | head -1)
WEB_CONTAINER_NAME=$(docker ps --filter name="web" --format "{{.Names}}" | head -1)

# Fallback names if auto-detection fails
if [ -z "$DB_CONTAINER_NAME" ]; then
    DB_CONTAINER_NAME="slnh-maintenance-db-1"
    print_warning "Using fallback DB container name: $DB_CONTAINER_NAME"
else
    print_success "Detected DB container: $DB_CONTAINER_NAME"
fi

if [ -z "$WEB_CONTAINER_NAME" ]; then
    WEB_CONTAINER_NAME="slnh-maintenance-web-1"
    print_warning "Using fallback web container name: $WEB_CONTAINER_NAME"
else
    print_success "Detected web container: $WEB_CONTAINER_NAME"
fi

print_status "🚀 IMMEDIATE DATABASE FIX"
print_status "This will fix your database issue right now!"
echo

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed or not in PATH"
    exit 1
fi

# Check if database container exists and is running
print_status "Checking database container status..."
if ! docker ps --filter name="$DB_CONTAINER_NAME" --format "table {{.Names}}" | grep -q "$DB_CONTAINER_NAME"; then
    print_warning "Database container '$DB_CONTAINER_NAME' not found or not running"
    print_status "Checking for containers with 'db' in the name..."
    docker ps --filter name="db" --format "table {{.Names}}\t{{.Status}}"
    echo
    print_error "Please update the DB_CONTAINER_NAME variable in this script with the correct container name"
    exit 1
fi

print_success "Database container '$DB_CONTAINER_NAME' is running"

# Check if database exists
print_status "Checking if database '$DB_NAME' exists..."
if docker exec "$DB_CONTAINER_NAME" psql -U "$DB_USER" -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
    print_success "Database '$DB_NAME' already exists!"
    print_status "The issue might be with the web container. Let's restart it..."
else
    print_warning "Database '$DB_NAME' does not exist. Creating it now..."
    
    # Create the database
    if docker exec "$DB_CONTAINER_NAME" psql -U "$DB_USER" -c "CREATE DATABASE $DB_NAME"; then
        print_success "✅ Database '$DB_NAME' created successfully!"
    else
        print_error "❌ Failed to create database. Check PostgreSQL logs:"
        docker logs "$DB_CONTAINER_NAME" --tail 20
        exit 1
    fi
fi

# Restart web container if it exists
print_status "Checking web container status..."
if docker ps -a --filter name="$WEB_CONTAINER_NAME" --format "table {{.Names}}" | grep -q "$WEB_CONTAINER_NAME"; then
    print_status "Restarting web container '$WEB_CONTAINER_NAME'..."
    if docker restart "$WEB_CONTAINER_NAME"; then
        print_success "✅ Web container restarted successfully!"
    else
        print_error "❌ Failed to restart web container"
        exit 1
    fi
else
    print_warning "Web container '$WEB_CONTAINER_NAME' not found"
    print_status "Available containers:"
    docker ps -a --format "table {{.Names}}\t{{.Status}}"
fi

echo
print_success "🎉 IMMEDIATE FIX COMPLETED!"
print_status "Your application should now be working."
print_status "Check the web container logs:"
print_status "  docker logs $WEB_CONTAINER_NAME -f"
echo
print_status "If you want to prevent this issue in the future, redeploy with the updated stack configuration."