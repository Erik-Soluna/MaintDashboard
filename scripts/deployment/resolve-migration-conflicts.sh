#!/bin/bash
# Comprehensive Migration Conflict Resolution Script
# This script can be run manually to resolve Django migration conflicts

set -e

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

# Function to check current migration status
check_migration_status() {
    print_status "🔍 Checking current migration status..."
    
    echo "=== Core App Migrations ==="
    python manage.py showmigrations core 2>&1 || echo "Failed to show core migrations"
    
    echo -e "\n=== Maintenance App Migrations ==="
    python manage.py showmigrations maintenance 2>&1 || echo "Failed to show maintenance migrations"
    
    echo -e "\n=== Equipment App Migrations ==="
    python manage.py showmigrations equipment 2>&1 || echo "Failed to show equipment migrations"
    
    echo -e "\n=== Events App Migrations ==="
    python manage.py showmigrations events 2>&1 || echo "Failed to show events migrations"
    
    echo -e "\n=== Overall Migration Status ==="
    python manage.py showmigrations --list 2>&1 || echo "Failed to show overall migration status"
}

# Function to detect migration conflicts
detect_conflicts() {
    print_status "🔍 Detecting migration conflicts..."
    
    local conflicts_found=false
    
    # Check for explicit conflict messages
    if python manage.py showmigrations --list 2>&1 | grep -q "Conflicting migrations detected"; then
        print_warning "Explicit migration conflicts detected!"
        conflicts_found=true
    fi
    
    # Check for multiple leaf nodes in each app
    local apps=("core" "maintenance" "equipment" "events")
    
    for app in "${apps[@]}"; do
        if [ -d "$app/migrations" ]; then
            local leaf_count=$(python manage.py showmigrations "$app" 2>/dev/null | grep -c "\[X\]" || echo "0")
            if [ "$leaf_count" -gt 1 ]; then
                print_warning "Multiple leaf nodes detected in $app app: $leaf_count"
                conflicts_found=true
            fi
        fi
    done
    
    # Try to run migrate --plan
    if ! python manage.py migrate --plan --noinput > /dev/null 2>&1; then
        print_warning "Migration plan failed, conflicts likely present"
        conflicts_found=true
    fi
    
    if [ "$conflicts_found" = false ]; then
        print_success "No migration conflicts detected"
        return 1
    else
        print_warning "Migration conflicts detected"
        return 0
    fi
}

# Function to attempt automatic conflict resolution
resolve_conflicts_automatic() {
    print_status "🔧 Attempting automatic conflict resolution..."
    
    # Strategy 1: Try makemigrations --merge
    print_status "Strategy 1: Attempting makemigrations --merge..."
    if python manage.py makemigrations --merge --noinput; then
        print_success "Migration merge completed successfully"
        
        # Apply the merged migrations
        print_status "Applying merged migrations..."
        if python manage.py migrate --noinput; then
            print_success "Merged migrations applied successfully"
            return 0
        else
            print_warning "Failed to apply merged migrations"
            return 1
        fi
    else
        print_warning "makemigrations --merge failed"
        return 1
    fi
}

# Function to attempt manual conflict resolution
resolve_conflicts_manual() {
    print_status "🔧 Attempting manual conflict resolution..."
    
    # Strategy 2: Try to fake apply problematic migrations
    print_status "Strategy 2: Attempting to fake apply problematic migrations..."
    
    # Get list of unapplied migrations
    local unapplied=$(python manage.py showmigrations --list 2>/dev/null | grep "\[ \]" | awk '{print $2}' || echo "")
    
    if [ -n "$unapplied" ]; then
        print_status "Found unapplied migrations: $unapplied"
        
        # Try to fake apply them one by one
        for migration in $unapplied; do
            print_status "Attempting to fake apply: $migration"
            if python manage.py migrate --fake "$migration"; then
                print_success "Successfully fake applied: $migration"
            else
                print_warning "Failed to fake apply: $migration"
            fi
        done
        
        # Final migration attempt
        print_status "Attempting final migration..."
        if python manage.py migrate --noinput; then
            print_success "Final migration completed successfully"
            return 0
        else
            print_warning "Final migration failed"
            return 1
        fi
    else
        print_warning "No unapplied migrations found for fake application"
        return 1
    fi
}

# Function to attempt forced resolution
resolve_conflicts_forced() {
    print_status "🔧 Attempting forced conflict resolution..."
    
    # Strategy 3: Reset migration state and recreate
    print_status "Strategy 3: Attempting forced resolution..."
    
    # This is a more aggressive approach - use with caution
    print_warning "This is a destructive operation. Are you sure? (y/N)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        print_status "Proceeding with forced resolution..."
        
        # Try to reset the migration state for problematic apps
        local apps=("core" "maintenance")
        
        for app in "${apps[@]}"; do
            if [ -d "$app/migrations" ]; then
                print_status "Attempting to reset migration state for $app..."
                
                # Get the latest migration file
                local latest_migration=$(ls "$app/migrations"/*.py 2>/dev/null | grep -v __init__.py | sort -V | tail -1)
                
                if [ -n "$latest_migration" ]; then
                    local migration_name=$(basename "$latest_migration" .py)
                    print_status "Fake applying latest migration: $migration_name"
                    
                    if python manage.py migrate --fake "$app" "$migration_name"; then
                        print_success "Successfully fake applied $migration_name for $app"
                    else
                        print_warning "Failed to fake apply $migration_name for $app"
                    fi
                fi
            fi
        done
        
        # Final migration attempt
        if python manage.py migrate --noinput; then
            print_success "Forced resolution completed successfully"
            return 0
        else
            print_warning "Forced resolution failed"
            return 1
        fi
    else
        print_status "Forced resolution cancelled by user"
        return 1
    fi
}

# Function to verify resolution
verify_resolution() {
    print_status "🔍 Verifying migration conflict resolution..."
    
    # Check if migrations can run without conflicts
    if python manage.py migrate --plan --noinput > /dev/null 2>&1; then
        print_success "Migration conflicts resolved successfully"
        return 0
    else
        print_error "Migration conflicts still exist"
        return 1
    fi
}

# Function to show final status
show_final_status() {
    print_status "📊 Final migration status:"
    echo "=== Final Migration Status ==="
    python manage.py showmigrations --list 2>&1 || echo "Failed to show final migration status"
}

# Main function
main() {
    print_status "🚀 Starting comprehensive migration conflict resolution..."
    
    # Change to app directory
    cd /app || exit 1
    
    # Set Django environment
    export DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE:-maintenance_dashboard.settings}
    export PYTHONPATH=/app:$PYTHONPATH
    
    # Show initial status
    check_migration_status
    
    # Detect conflicts
    if ! detect_conflicts; then
        print_success "No conflicts to resolve"
        show_final_status
        return 0
    fi
    
    # Try automatic resolution first
    print_status "Attempting automatic resolution..."
    if resolve_conflicts_automatic; then
        print_success "Automatic resolution successful!"
    else
        print_warning "Automatic resolution failed, trying manual resolution..."
        
        if resolve_conflicts_manual; then
            print_success "Manual resolution successful!"
        else
            print_warning "Manual resolution failed, offering forced resolution..."
            
            if resolve_conflicts_forced; then
                print_success "Forced resolution successful!"
            else
                print_error "All resolution strategies failed"
                return 1
            fi
        fi
    fi
    
    # Verify resolution
    if verify_resolution; then
        print_success "✅ Migration conflicts resolved successfully!"
        show_final_status
        return 0
    else
        print_error "❌ Migration conflicts still exist after resolution attempts"
        return 1
    fi
}

# Check if script is being run directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
