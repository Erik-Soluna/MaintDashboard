#!/bin/bash
# Migration Conflict Resolver Script
# This script handles Django migration conflicts automatically

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

# Function to check for migration conflicts
check_migration_conflicts() {
    print_status "🔍 Checking for migration conflicts..."
    
    # Check if there are conflicting migrations
    if python manage.py showmigrations --list 2>&1 | grep -q "Conflicting migrations detected"; then
        print_warning "Migration conflicts detected!"
        return 0
    fi
    
    # Alternative check - look for multiple leaf nodes
    local app_names=("core" "maintenance" "equipment" "events")
    local conflict_found=false
    
    for app in "${app_names[@]}"; do
        if [ -d "core/migrations" ] || [ -d "$app/migrations" ]; then
            local leaf_count=$(python manage.py showmigrations "$app" 2>/dev/null | grep -c "\[X\]" || echo "0")
            if [ "$leaf_count" -gt 1 ]; then
                print_warning "Multiple leaf nodes detected in $app app"
                conflict_found=true
            fi
        fi
    done
    
    if [ "$conflict_found" = true ]; then
        return 0
    fi
    
    print_success "No migration conflicts detected"
    return 1
}

# Function to resolve migration conflicts
resolve_migration_conflicts() {
    print_status "🔧 Resolving migration conflicts..."
    
    # Check if we should force merge
    if [ "${FORCE_MIGRATION_MERGE:-false}" = "true" ]; then
        print_warning "Force migration merge enabled"
    fi
    
    # First, try to detect the specific conflicts
    print_status "Analyzing migration conflicts..."
    
    # Check core app conflicts
    if [ -d "core/migrations" ]; then
        print_status "Checking core app migrations..."
        python manage.py showmigrations core 2>&1 || true
    fi
    
    # Check maintenance app conflicts
    if [ -d "maintenance/migrations" ]; then
        print_status "Checking maintenance app migrations..."
        python manage.py showmigrations maintenance 2>&1 || true
    fi
    
    # Try to run makemigrations --merge
    print_status "Attempting to merge conflicting migrations..."
    if python manage.py makemigrations --merge --noinput; then
        print_success "Migration merge completed successfully"
        
        # Now apply the merged migrations
        print_status "Applying merged migrations..."
        if python manage.py migrate --noinput; then
            print_success "Merged migrations applied successfully"
            return 0
        else
            print_error "Failed to apply merged migrations"
            return 1
        fi
    else
        print_warning "Migration merge failed, attempting alternative resolution..."
        
        # Alternative approach: try to fake apply problematic migrations
        if [ "${FORCE_MIGRATION_MERGE:-false}" = "true" ]; then
            print_status "Attempting forced migration resolution..."
            
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
                if python manage.py migrate --noinput; then
                    print_success "Final migration completed successfully"
                    return 0
                else
                    print_error "Final migration failed"
                    return 1
                fi
            fi
        fi
        
        return 1
    fi
}

# Function to verify migration resolution
verify_migration_resolution() {
    print_status "🔍 Verifying migration resolution..."
    
    # Check if migrations can run without conflicts
    if python manage.py migrate --plan --noinput > /dev/null 2>&1; then
        print_success "Migration conflicts resolved successfully"
        return 0
    else
        print_error "Migration conflicts still exist"
        return 1
    fi
}

# Main function
main() {
    print_status "🚀 Starting migration conflict resolution..."
    
    # Change to app directory
    cd /app || exit 1
    
    # Set Django environment
    export DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE:-maintenance_dashboard.settings}
    export PYTHONPATH=/app:$PYTHONPATH
    
    # Check if migration conflict resolution is enabled
    if [ "${MIGRATION_CONFLICT_RESOLUTION:-false}" != "true" ]; then
        print_status "Migration conflict resolution disabled, skipping..."
        return 0
    fi
    
    # Check for conflicts
    if ! check_migration_conflicts; then
        print_success "No migration conflicts to resolve"
        return 0
    fi
    
    # Resolve conflicts
    if resolve_migration_conflicts; then
        # Verify resolution
        if verify_migration_resolution; then
            print_success "✅ Migration conflicts resolved successfully!"
            return 0
        else
            print_error "❌ Migration conflicts still exist after resolution attempt"
            return 1
        fi
    else
        print_error "❌ Failed to resolve migration conflicts"
        return 1
    fi
}

# Run main function
main "$@"
