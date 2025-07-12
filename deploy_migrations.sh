#!/bin/bash

# Migration Deployment Script
# This script ensures all migrations are properly applied during deployment

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SCRIPT_DIR/deployment_migrations.log"
BACKUP_ENABLED=false
DATABASE_BACKUP_FILE=""
ENVIRONMENT="${ENVIRONMENT:-production}"

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

# Error handling
handle_error() {
    log "${RED}Error occurred on line $1${NC}"
    log "${RED}Command: $2${NC}"
    log "${RED}Exit code: $3${NC}"
    
    if [ "$BACKUP_ENABLED" = true ] && [ -n "$DATABASE_BACKUP_FILE" ]; then
        log "${YELLOW}Database backup available at: $DATABASE_BACKUP_FILE${NC}"
        log "${YELLOW}Consider restoring from backup if needed${NC}"
    fi
    
    exit 1
}

# Set up error handling
trap 'handle_error ${LINENO} "$BASH_COMMAND" $?' ERR

# Show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --backup          Create database backup before applying migrations"
    echo "  --dry-run         Show what would be done without applying changes"
    echo "  --force           Force apply migrations even if issues are detected"
    echo "  --check-only      Only check migration status, don't apply"
    echo "  --environment ENV Set environment (default: production)"
    echo "  --help            Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  DJANGO_SETTINGS_MODULE  Django settings module"
    echo "  DATABASE_URL           Database connection string"
    echo "  BACKUP_DIR             Directory for database backups"
    echo ""
}

# Parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --backup)
                BACKUP_ENABLED=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --force)
                FORCE_APPLY=true
                shift
                ;;
            --check-only)
                CHECK_ONLY=true
                shift
                ;;
            --environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
}

# Check prerequisites
check_prerequisites() {
    log "${BLUE}Checking prerequisites...${NC}"
    
    # Check if we're in a Django project
    if [ ! -f "manage.py" ]; then
        log "${RED}Error: manage.py not found. Are you in a Django project directory?${NC}"
        exit 1
    fi
    
    # Check if Django is available
    if ! command -v python3 >/dev/null 2>&1; then
        log "${RED}Error: Python3 not found${NC}"
        exit 1
    fi
    
    # Test Django installation
    if ! python3 -c "import django" 2>/dev/null; then
        log "${RED}Error: Django not installed or not in PYTHONPATH${NC}"
        exit 1
    fi
    
    # Check database connection
    if ! python3 manage.py check --database default 2>/dev/null; then
        log "${RED}Error: Database connection failed${NC}"
        exit 1
    fi
    
    log "${GREEN}✓ All prerequisites met${NC}"
}

# Create database backup
create_backup() {
    if [ "$BACKUP_ENABLED" = true ]; then
        log "${BLUE}Creating database backup...${NC}"
        
        BACKUP_DIR="${BACKUP_DIR:-$SCRIPT_DIR/backups}"
        mkdir -p "$BACKUP_DIR"
        
        TIMESTAMP=$(date +%Y%m%d_%H%M%S)
        DATABASE_BACKUP_FILE="$BACKUP_DIR/db_backup_${TIMESTAMP}.sql"
        
        # Create backup using Django's dumpdata command
        python3 manage.py dumpdata --output "$DATABASE_BACKUP_FILE.json" --indent 2
        
        # Also create PostgreSQL dump if available
        if command -v pg_dump >/dev/null 2>&1; then
            DB_NAME=$(python3 manage.py shell -c "from django.conf import settings; print(settings.DATABASES['default']['NAME'])")
            DB_USER=$(python3 manage.py shell -c "from django.conf import settings; print(settings.DATABASES['default']['USER'])")
            DB_HOST=$(python3 manage.py shell -c "from django.conf import settings; print(settings.DATABASES['default']['HOST'])")
            
            if [ -n "$DB_NAME" ] && [ -n "$DB_USER" ] && [ -n "$DB_HOST" ]; then
                pg_dump -h "$DB_HOST" -U "$DB_USER" "$DB_NAME" > "$DATABASE_BACKUP_FILE"
                log "${GREEN}✓ PostgreSQL backup created: $DATABASE_BACKUP_FILE${NC}"
            fi
        fi
        
        log "${GREEN}✓ Django backup created: $DATABASE_BACKUP_FILE.json${NC}"
    fi
}

# Check migration status
check_migration_status() {
    log "${BLUE}Checking migration status...${NC}"
    
    # Run our custom migration checker
    if [ -f "./check_migrations.sh" ]; then
        log "${BLUE}Running migration status check...${NC}"
        if ./check_migrations.sh; then
            log "${GREEN}✓ Migration check passed${NC}"
            return 0
        else
            log "${YELLOW}⚠ Migration check found issues${NC}"
            return 1
        fi
    else
        log "${YELLOW}⚠ Custom migration checker not found${NC}"
        return 1
    fi
}

# Show migration plan
show_migration_plan() {
    log "${BLUE}Migration plan:${NC}"
    
    # Show unapplied migrations
    if python3 manage.py showmigrations --list 2>/dev/null | grep -q "\[ \]"; then
        log "${YELLOW}Unapplied migrations:${NC}"
        python3 manage.py showmigrations --list 2>/dev/null | grep "\[ \]" | while read -r line; do
            log "  $line"
        done
    else
        log "${GREEN}✓ All migrations are already applied${NC}"
    fi
}

# Apply migrations
apply_migrations() {
    log "${BLUE}Applying migrations...${NC}"
    
    if [ "$DRY_RUN" = true ]; then
        log "${YELLOW}DRY RUN: Would apply migrations with: python3 manage.py migrate${NC}"
        return 0
    fi
    
    # Apply migrations with verbose output
    python3 manage.py migrate --verbosity=2 2>&1 | tee -a "$LOG_FILE"
    
    if [ $? -eq 0 ]; then
        log "${GREEN}✓ All migrations applied successfully${NC}"
        return 0
    else
        log "${RED}✗ Migration application failed${NC}"
        return 1
    fi
}

# Verify migration application
verify_migrations() {
    log "${BLUE}Verifying migration application...${NC}"
    
    # Check if there are any unapplied migrations
    if python3 manage.py showmigrations --list 2>/dev/null | grep -q "\[ \]"; then
        log "${RED}✗ Some migrations are still unapplied${NC}"
        python3 manage.py showmigrations --list 2>/dev/null | grep "\[ \]"
        return 1
    else
        log "${GREEN}✓ All migrations verified as applied${NC}"
        return 0
    fi
}

# Run Django checks
run_django_checks() {
    log "${BLUE}Running Django system checks...${NC}"
    
    if python3 manage.py check --deploy 2>&1 | tee -a "$LOG_FILE"; then
        log "${GREEN}✓ Django checks passed${NC}"
        return 0
    else
        log "${YELLOW}⚠ Django checks found issues${NC}"
        return 1
    fi
}

# Create missing initial data
create_initial_data() {
    log "${BLUE}Creating initial data...${NC}"
    
    # Run custom management commands for initial data
    INIT_COMMANDS=(
        "init_rbac"
        "ensure_permissions"
        "setup_default_locations"
    )
    
    for cmd in "${INIT_COMMANDS[@]}"; do
        if python3 manage.py help "$cmd" >/dev/null 2>&1; then
            log "${BLUE}Running: python3 manage.py $cmd${NC}"
            if python3 manage.py "$cmd" 2>&1 | tee -a "$LOG_FILE"; then
                log "${GREEN}✓ $cmd completed successfully${NC}"
            else
                log "${YELLOW}⚠ $cmd had issues (non-fatal)${NC}"
            fi
        else
            log "${YELLOW}⚠ Command $cmd not found${NC}"
        fi
    done
}

# Generate report
generate_report() {
    log "\n${BLUE}=== MIGRATION DEPLOYMENT REPORT ===${NC}"
    log "Timestamp: $(date)"
    log "Environment: $ENVIRONMENT"
    log "Directory: $SCRIPT_DIR"
    
    if [ "$BACKUP_ENABLED" = true ] && [ -n "$DATABASE_BACKUP_FILE" ]; then
        log "Backup file: $DATABASE_BACKUP_FILE"
    fi
    
    # Show final migration status
    log "\n${BLUE}Final migration status:${NC}"
    python3 manage.py showmigrations --list 2>/dev/null || true
    
    log "\nFull log saved to: $LOG_FILE"
}

# Main execution
main() {
    log "${GREEN}=== Migration Deployment Script ===${NC}"
    log "Starting deployment at $(date)"
    log "Environment: $ENVIRONMENT"
    
    # Clear previous log
    > "$LOG_FILE"
    
    # Parse arguments
    parse_arguments "$@"
    
    # Check prerequisites
    check_prerequisites
    
    # Create backup if requested
    create_backup
    
    # Check migration status
    migration_check_passed=true
    if ! check_migration_status; then
        migration_check_passed=false
        if [ "$FORCE_APPLY" != true ]; then
            log "${RED}Migration check failed. Use --force to apply anyway.${NC}"
            exit 1
        fi
    fi
    
    # Show migration plan
    show_migration_plan
    
    # Exit if check-only mode
    if [ "$CHECK_ONLY" = true ]; then
        log "${BLUE}Check-only mode: exiting without applying migrations${NC}"
        generate_report
        exit 0
    fi
    
    # Apply migrations
    if ! apply_migrations; then
        log "${RED}Migration application failed${NC}"
        generate_report
        exit 1
    fi
    
    # Verify migrations
    if ! verify_migrations; then
        log "${RED}Migration verification failed${NC}"
        generate_report
        exit 1
    fi
    
    # Run Django checks
    run_django_checks
    
    # Create initial data
    create_initial_data
    
    # Generate final report
    generate_report
    
    log "${GREEN}✓ Migration deployment completed successfully!${NC}"
}

# Run main function with all arguments
main "$@"