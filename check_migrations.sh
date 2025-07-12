#!/bin/bash

# Migration Status Checker Script
# This script checks for migration issues without requiring Django setup

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SCRIPT_DIR/migration_check.log"
ERRORS_FOUND=0
WARNINGS_FOUND=0

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "$1" | tee -a "$LOG_FILE"
}

# Check if we're in a Django project
check_django_project() {
    if [ ! -f "manage.py" ]; then
        log "${RED}Error: manage.py not found. Are you in a Django project directory?${NC}"
        exit 1
    fi
    log "${GREEN}✓ Django project detected${NC}"
}

# Check for duplicate migration numbers
check_duplicate_migrations() {
    log "\n${BLUE}Checking for duplicate migration numbers...${NC}"
    
    for app_dir in */; do
        if [ -d "$app_dir/migrations" ]; then
            app_name=$(basename "$app_dir")
            migration_dir="$app_dir/migrations"
            
            # Skip if no migration files
            if [ ! "$(ls -A "$migration_dir"/*.py 2>/dev/null | grep -v __init__.py)" ]; then
                continue
            fi
            
            log "\n${YELLOW}Checking $app_name migrations:${NC}"
            
            # Get all migration files and extract numbers
            declare -A migration_numbers
            
            for migration_file in "$migration_dir"/*.py; do
                if [ -f "$migration_file" ] && [[ "$(basename "$migration_file")" != "__init__.py" ]]; then
                    filename=$(basename "$migration_file" .py)
                    
                    # Extract migration number (assuming format: 0001_migration_name)
                    if [[ $filename =~ ^([0-9]+)_ ]]; then
                        number="${BASH_REMATCH[1]}"
                        
                        if [[ -n "${migration_numbers[$number]}" ]]; then
                            log "${RED}  ✗ DUPLICATE MIGRATION NUMBER: $number${NC}"
                            log "${RED}    - ${migration_numbers[$number]}${NC}"
                            log "${RED}    - $filename${NC}"
                            ((ERRORS_FOUND++))
                        else
                            migration_numbers[$number]="$filename"
                            log "${GREEN}  ✓ $filename${NC}"
                        fi
                    else
                        log "${YELLOW}  ? $filename (non-standard naming)${NC}"
                        ((WARNINGS_FOUND++))
                    fi
                fi
            done
            
            # Clean up array for next iteration
            unset migration_numbers
        fi
    done
}

# Check for missing __init__.py files
check_init_files() {
    log "\n${BLUE}Checking for missing __init__.py files...${NC}"
    
    for app_dir in */; do
        if [ -d "$app_dir/migrations" ]; then
            app_name=$(basename "$app_dir")
            init_file="$app_dir/migrations/__init__.py"
            
            if [ ! -f "$init_file" ]; then
                log "${RED}  ✗ Missing __init__.py in $app_name/migrations/${NC}"
                ((ERRORS_FOUND++))
                
                # Create missing __init__.py
                touch "$init_file"
                log "${GREEN}  ✓ Created missing __init__.py${NC}"
            else
                log "${GREEN}  ✓ $app_name/migrations/__init__.py${NC}"
            fi
        fi
    done
}

# Check migration file syntax
check_migration_syntax() {
    log "\n${BLUE}Checking migration file syntax...${NC}"
    
    for app_dir in */; do
        if [ -d "$app_dir/migrations" ]; then
            app_name=$(basename "$app_dir")
            
            for migration_file in "$app_dir/migrations"/*.py; do
                if [ -f "$migration_file" ] && [[ "$(basename "$migration_file")" != "__init__.py" ]]; then
                    filename=$(basename "$migration_file")
                    
                    # Basic syntax check
                    if python3 -m py_compile "$migration_file" 2>/dev/null; then
                        log "${GREEN}  ✓ $app_name/$filename syntax OK${NC}"
                    else
                        log "${RED}  ✗ $app_name/$filename syntax ERROR${NC}"
                        ((ERRORS_FOUND++))
                    fi
                fi
            done
        fi
    done
}

# Check for common migration issues
check_common_issues() {
    log "\n${BLUE}Checking for common migration issues...${NC}"
    
    # Check for RunPython without reverse_code
    grep -r "RunPython" */migrations/*.py 2>/dev/null | while read -r line; do
        file=$(echo "$line" | cut -d: -f1)
        if ! grep -q "reverse_code" "$file"; then
            log "${YELLOW}  ? $file: RunPython without reverse_code${NC}"
            ((WARNINGS_FOUND++))
        fi
    done
    
    # Check for potential unsafe operations
    grep -r "RemoveField\|DeleteModel\|DropTable" */migrations/*.py 2>/dev/null | while read -r line; do
        file=$(echo "$line" | cut -d: -f1)
        log "${YELLOW}  ? $file: Potentially unsafe operation detected${NC}"
        ((WARNINGS_FOUND++))
    done
}

# Fix duplicate migration numbers
fix_duplicate_migrations() {
    log "\n${BLUE}Fixing duplicate migration numbers...${NC}"
    
    for app_dir in */; do
        if [ -d "$app_dir/migrations" ]; then
            app_name=$(basename "$app_dir")
            migration_dir="$app_dir/migrations"
            
            # Get highest migration number
            highest_num=0
            for migration_file in "$migration_dir"/*.py; do
                if [ -f "$migration_file" ] && [[ "$(basename "$migration_file")" != "__init__.py" ]]; then
                    filename=$(basename "$migration_file" .py)
                    if [[ $filename =~ ^([0-9]+)_ ]]; then
                        num="${BASH_REMATCH[1]}"
                        if [ "$num" -gt "$highest_num" ]; then
                            highest_num="$num"
                        fi
                    fi
                fi
            done
            
            # Check for duplicates and rename
            declare -A seen_numbers
            for migration_file in "$migration_dir"/*.py; do
                if [ -f "$migration_file" ] && [[ "$(basename "$migration_file")" != "__init__.py" ]]; then
                    filename=$(basename "$migration_file" .py)
                    if [[ $filename =~ ^([0-9]+)_(.*)$ ]]; then
                        num="${BASH_REMATCH[1]}"
                        name="${BASH_REMATCH[2]}"
                        
                        if [[ -n "${seen_numbers[$num]}" ]]; then
                            # Duplicate found, rename it
                            ((highest_num++))
                            new_num=$(printf "%04d" "$highest_num")
                            new_filename="${new_num}_${name}.py"
                            new_path="$migration_dir/$new_filename"
                            
                            log "${YELLOW}  Renaming $filename.py to $new_filename${NC}"
                            mv "$migration_file" "$new_path"
                            
                            # Update dependencies in the file
                            sed -i "s/('$app_name', '$filename')/('$app_name', '${new_num}_${name}')/g" "$new_path"
                            
                        else
                            seen_numbers[$num]="$filename"
                        fi
                    fi
                fi
            done
            
            unset seen_numbers
        fi
    done
}

# Try to run Django migrations check if environment is available
try_django_check() {
    log "\n${BLUE}Attempting Django migration check...${NC}"
    
    # Check if we can run Django commands
    if command -v python3 >/dev/null 2>&1; then
        # Try to run showmigrations
        if python3 manage.py showmigrations --list 2>/dev/null; then
            log "${GREEN}✓ Django migration status retrieved${NC}"
            
            # Check for unapplied migrations
            if python3 manage.py showmigrations --list 2>/dev/null | grep -q "\[ \]"; then
                log "${YELLOW}⚠ Unapplied migrations detected${NC}"
                python3 manage.py showmigrations --list 2>/dev/null | grep "\[ \]" || true
                ((WARNINGS_FOUND++))
            fi
            
            # Try to run the custom management command if it exists
            if python3 manage.py check_migrations 2>/dev/null; then
                log "${GREEN}✓ Custom migration check completed${NC}"
            fi
            
        else
            log "${YELLOW}⚠ Could not run Django commands (environment not set up)${NC}"
            ((WARNINGS_FOUND++))
        fi
    else
        log "${YELLOW}⚠ Python3 not available${NC}"
        ((WARNINGS_FOUND++))
    fi
}

# Generate report
generate_report() {
    log "\n${BLUE}=== MIGRATION CHECK REPORT ===${NC}"
    log "Timestamp: $(date)"
    log "Directory: $SCRIPT_DIR"
    log "Errors found: $ERRORS_FOUND"
    log "Warnings found: $WARNINGS_FOUND"
    
    if [ "$ERRORS_FOUND" -eq 0 ] && [ "$WARNINGS_FOUND" -eq 0 ]; then
        log "${GREEN}✓ No migration issues detected!${NC}"
        return 0
    elif [ "$ERRORS_FOUND" -eq 0 ]; then
        log "${YELLOW}⚠ Some warnings found, but no critical errors${NC}"
        return 1
    else
        log "${RED}✗ Critical migration errors found that need attention${NC}"
        return 2
    fi
}

# Main execution
main() {
    log "${GREEN}=== Migration Status Checker ===${NC}"
    log "Starting migration check at $(date)"
    
    # Clear previous log
    > "$LOG_FILE"
    
    # Run checks
    check_django_project
    check_duplicate_migrations
    check_init_files
    check_migration_syntax
    check_common_issues
    
    # Try Django-specific checks
    try_django_check
    
    # Generate final report
    generate_report
    exit_code=$?
    
    log "\nFull log saved to: $LOG_FILE"
    
    if [ "$1" = "--fix" ]; then
        log "\n${BLUE}Applying fixes...${NC}"
        fix_duplicate_migrations
        log "${GREEN}✓ Fixes applied${NC}"
    fi
    
    exit $exit_code
}

# Show usage
show_usage() {
    echo "Usage: $0 [--fix]"
    echo "  --fix  : Automatically fix issues where possible"
    echo ""
    echo "This script checks for migration issues including:"
    echo "- Duplicate migration numbers"
    echo "- Missing __init__.py files"
    echo "- Syntax errors in migration files"
    echo "- Common migration issues"
    echo ""
}

# Handle command line arguments
case "${1:-}" in
    -h|--help)
        show_usage
        exit 0
        ;;
    --fix)
        main "$1"
        ;;
    "")
        main
        ;;
    *)
        echo "Unknown option: $1"
        show_usage
        exit 1
        ;;
esac