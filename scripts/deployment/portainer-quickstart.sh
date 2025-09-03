#!/bin/bash

# Portainer Quick Start Script for Maintenance Dashboard
# Version: 2025-09-03-FULLY-AUTOMATED
# Purpose: Generate Portainer stack configuration and instructions

set -e

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

print_header() {
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║ $1${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
}

print_step() {
    echo -e "${BLUE}[STEP $1]${NC} $2"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STACK_FILE="$PROJECT_ROOT/portainer-stack-dev-automated.yml"

# Main execution
main() {
    print_header "PORTAINER AUTOMATED DEPLOYMENT GUIDE"
    echo ""
    
    print_step "1" "Copy the stack configuration"
    print_info "Stack file location: $STACK_FILE"
    echo ""
    
    print_step "2" "Environment Variables to set in Portainer"
    echo ""
    echo "# Database Configuration"
    echo "DB_NAME=maintenance_dashboard_dev"
    echo "DB_USER=maintenance_user_dev"
    echo "DB_PASSWORD=DevPassword2024!"
    echo ""
    echo "# Admin Configuration"
    echo "ADMIN_USERNAME=admin"
    echo "ADMIN_EMAIL=admin@dev.maintenance.errorlog.app"
    echo "ADMIN_PASSWORD=DevAdminPassword2024!"
    echo ""
    echo "# Domain Configuration"
    echo "DOMAIN=dev.maintenance.errorlog.app"
    echo ""
    echo "# Git Information (optional)"
    echo "GIT_COMMIT_COUNT=0"
    echo "GIT_COMMIT_HASH=automated"
    echo "GIT_BRANCH=main"
    echo "GIT_COMMIT_DATE=$(date -I)"
    echo ""
    
    print_step "3" "Portainer Deployment Steps"
    echo ""
    print_info "1. Open Portainer Web UI"
    print_info "2. Go to 'Stacks' section"
    print_info "3. Click 'Add Stack'"
    print_info "4. Name: 'maintenance-dashboard-auto'"
    print_info "5. Build method: 'Repository' (recommended) or 'Web editor'"
    print_info "6. If using Repository:"
    print_info "   - Repository URL: <your-git-repo>"
    print_info "   - Compose path: portainer-stack-dev-automated.yml"
    print_info "7. If using Web editor:"
    print_info "   - Copy contents from: $STACK_FILE"
    print_info "8. Add environment variables (from Step 2 above)"
    print_info "9. Click 'Deploy the stack'"
    print_info "10. Wait 2-3 minutes for complete initialization"
    echo ""
    
    print_step "4" "Access Information"
    echo ""
    print_info "After deployment completes:"
    print_info "- Application: http://localhost:4407/ (or your configured domain)"
    print_info "- Admin Panel: http://localhost:4407/admin/"
    print_info "- Username: admin"
    print_info "- Password: DevAdminPassword2024!"
    echo ""
    
    print_step "5" "Automation Features"
    echo ""
    print_success "✅ Automatic database creation and migration"
    print_success "✅ Automatic admin user creation"
    print_success "✅ Automatic static file collection"
    print_success "✅ Automatic branding setup"
    print_success "✅ Health checks and error recovery"
    print_success "✅ Migration conflict resolution"
    echo ""
    
    print_step "6" "Monitoring and Troubleshooting"
    echo ""
    print_info "View container logs in Portainer:"
    print_info "1. Go to 'Containers' section"
    print_info "2. Click on container name (e.g., maintenance_web_dev_auto)"
    print_info "3. Click 'Logs' tab"
    print_info "4. Look for initialization messages and any errors"
    echo ""
    print_info "Expected log messages during startup:"
    print_info "- '🚀 MAINTENANCE DASHBOARD - AUTOMATED DEPLOYMENT'"
    print_info "- '✅ Database connection successful!'"
    print_info "- '✅ Migrations completed successfully'"
    print_info "- '✅ Admin user created successfully'"
    print_info "- '🎉 DEPLOYMENT COMPLETED SUCCESSFULLY!'"
    echo ""
    
    print_step "7" "Customization Options"
    echo ""
    print_info "You can customize the deployment by modifying environment variables:"
    print_info "- Change ADMIN_USERNAME, ADMIN_EMAIL, ADMIN_PASSWORD"
    print_info "- Modify DOMAIN for your specific domain"
    print_info "- Adjust port mappings in the stack file"
    print_info "- Set BRANDING_* variables for custom branding"
    echo ""
    
    print_header "READY TO DEPLOY!"
    print_success "Copy the stack file and environment variables to Portainer"
    print_success "The system will handle everything else automatically"
    echo ""
}

# Execute main function
main "$@"