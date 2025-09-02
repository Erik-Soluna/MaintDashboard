#!/bin/bash

# Production Portainer Deployment Script for Maintenance Dashboard
# This script automates the complete production deployment process
# Run this script to prepare and deploy to Portainer production environment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Function to print colored output
print_header() {
    echo -e "${PURPLE}================================================${NC}"
    echo -e "${PURPLE}$1${NC}"
    echo -e "${PURPLE}================================================${NC}"
}

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

# Function to check prerequisites
check_prerequisites() {
    print_header "🔍 Checking Prerequisites"
    
    # Check if we're in a git repository
    if [ ! -d ".git" ]; then
        print_error "Not in a git repository"
        print_error "Please run this script from the root of your MaintDashboard repository"
        exit 1
    fi
    
    # Check if required files exist
    local required_files=(
        "portainer-stack.yml"
        "portainer.env.template"
        "Dockerfile"
        "scripts/deployment/docker-entrypoint.sh"
    )
    
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            print_error "Required file missing: $file"
            exit 1
        fi
    done
    
    # Check if Python is available
    if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
        print_warning "Python not found - version information may not be updated"
    fi
    
    print_success "All prerequisites met"
}

# Function to update version information
update_version_info() {
    print_header "📊 Updating Version Information"
    
    # Get git information
    print_status "Capturing git version information..."
    GIT_COMMIT_COUNT=$(git rev-list --count HEAD)
    GIT_COMMIT_HASH=$(git rev-parse --short HEAD)
    GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
    GIT_COMMIT_DATE=$(git log -1 --format=%cd --date=short)
    
    print_success "Git information captured:"
    echo "   Commit Count: $GIT_COMMIT_COUNT"
    echo "   Commit Hash: $GIT_COMMIT_HASH"
    echo "   Branch: $GIT_BRANCH"
    echo "   Date: $GIT_COMMIT_DATE"
    
    # Update version files using the unified system
    print_status "Updating version files automatically..."
    if command -v python3 &> /dev/null; then
        python3 version.py --update
    elif command -v python &> /dev/null; then
        python version.py --update
    else
        print_warning "Python not found, skipping automatic version file update"
    fi
    
    # Update portainer.env.template with current version
    print_status "Updating portainer.env.template with current version..."
    sed -i.bak "s/GIT_COMMIT_COUNT=.*/GIT_COMMIT_COUNT=$GIT_COMMIT_COUNT/" portainer.env.template
    sed -i.bak "s/GIT_COMMIT_HASH=.*/GIT_COMMIT_HASH=$GIT_COMMIT_HASH/" portainer.env.template
    sed -i.bak "s/GIT_BRANCH=.*/GIT_BRANCH=$GIT_BRANCH/" portainer.env.template
    sed -i.bak "s/GIT_COMMIT_DATE=.*/GIT_COMMIT_DATE=$GIT_COMMIT_DATE/" portainer.env.template
    sed -i.bak "s/Current Version: .*/Current Version: v$GIT_COMMIT_COUNT.$GIT_COMMIT_HASH/" portainer.env.template
    sed -i.bak "s/Generated on .*/Generated on $(date '+%Y-%m-%d %H:%M:%S')/" portainer.env.template
    rm -f portainer.env.template.bak
    
    print_success "Version information updated successfully"
}

# Function to validate production configuration
validate_production_config() {
    print_header "🔧 Validating Production Configuration"
    
    # Check if production stack file exists and is valid
    if [ ! -f "portainer-stack.yml" ]; then
        print_error "Production stack file not found: portainer-stack.yml"
        exit 1
    fi
    
    # Basic validation of stack file
    if ! grep -q "services:" portainer-stack.yml; then
        print_error "Invalid portainer-stack.yml - missing services section"
        exit 1
    fi
    
    # Check for required services
    local required_services=("db" "redis" "web" "celery" "celery-beat")
    for service in "${required_services[@]}"; do
        if ! grep -q "  $service:" portainer-stack.yml; then
            print_error "Required service missing from stack: $service"
            exit 1
        fi
    done
    
    # Check for security settings
    if ! grep -q "SECURE_SSL_REDIRECT=True" portainer-stack.yml; then
        print_warning "SSL redirect not enabled in production stack"
    fi
    
    if ! grep -q "DEBUG=False" portainer-stack.yml; then
        print_warning "Debug mode not disabled in production stack"
    fi
    
    print_success "Production configuration validation completed"
}

# Function to generate deployment summary
generate_deployment_summary() {
    print_header "📋 Deployment Summary"
    
    echo "🚀 Production Deployment Ready!"
    echo ""
    echo "📊 Version Information:"
    echo "   Version: v$GIT_COMMIT_COUNT.$GIT_COMMIT_HASH"
    echo "   Commit: $GIT_COMMIT_HASH"
    echo "   Branch: $GIT_BRANCH"
    echo "   Date: $GIT_COMMIT_DATE"
    echo ""
    echo "🔧 Required Environment Variables for Portainer:"
    echo "   GIT_COMMIT_COUNT=$GIT_COMMIT_COUNT"
    echo "   GIT_COMMIT_HASH=$GIT_COMMIT_HASH"
    echo "   GIT_BRANCH=$GIT_BRANCH"
    echo "   GIT_COMMIT_DATE=$GIT_COMMIT_DATE"
    echo ""
    echo "📁 Files Ready for Deployment:"
    echo "   ✅ portainer-stack.yml (Production stack configuration)"
    echo "   ✅ portainer.env.template (Environment variables template)"
    echo "   ✅ Dockerfile (Container build configuration)"
    echo "   ✅ scripts/deployment/docker-entrypoint.sh (Container entrypoint)"
    echo ""
    echo "🌐 Post-Deployment Verification:"
    echo "   • Health Check: https://your-domain/health/simple/"
    echo "   • Version Info: https://your-domain/version/"
    echo "   • Admin Panel: https://your-domain/admin/"
    echo ""
    echo "📝 Next Steps:"
    echo "   1. Copy the environment variables above into your Portainer stack"
    echo "   2. Upload portainer-stack.yml to Portainer"
    echo "   3. Deploy the stack"
    echo "   4. Monitor container health and logs"
    echo "   5. Verify application accessibility"
    echo ""
    echo "💡 Pro Tips:"
    echo "   • Use the 'latest' branch for development deployments"
    echo "   • Use the 'main' branch for production deployments"
    echo "   • Monitor the application logs for any issues"
    echo "   • Test the health endpoints after deployment"
    echo ""
    print_success "Deployment preparation completed successfully!"
}

# Function to create deployment checklist
create_deployment_checklist() {
    print_header "✅ Creating Deployment Checklist"
    
    cat > DEPLOYMENT_CHECKLIST.md << EOF
# Production Deployment Checklist

## Pre-Deployment
- [ ] Version information updated (v$GIT_COMMIT_COUNT.$GIT_COMMIT_HASH)
- [ ] All tests passing
- [ ] Database migrations reviewed
- [ ] Security settings verified
- [ ] Environment variables configured

## Portainer Configuration
- [ ] Stack file uploaded (portainer-stack.yml)
- [ ] Environment variables set:
  - [ ] GIT_COMMIT_COUNT=$GIT_COMMIT_COUNT
  - [ ] GIT_COMMIT_HASH=$GIT_COMMIT_HASH
  - [ ] GIT_BRANCH=$GIT_BRANCH
  - [ ] GIT_COMMIT_DATE=$GIT_COMMIT_DATE
  - [ ] Database credentials configured
  - [ ] Admin credentials configured
  - [ ] Domain settings configured

## Deployment
- [ ] Stack deployed successfully
- [ ] All containers showing as healthy
- [ ] No error messages in logs

## Post-Deployment Verification
- [ ] Health endpoint responding: /health/simple/
- [ ] Version endpoint working: /version/
- [ ] Admin panel accessible: /admin/
- [ ] Application fully functional
- [ ] SSL certificate working (if applicable)
- [ ] Database connectivity verified
- [ ] Redis connectivity verified
- [ ] Celery workers running
- [ ] Celery beat scheduler running

## Monitoring
- [ ] Container resource usage normal
- [ ] Application logs clean
- [ ] Error rates within acceptable limits
- [ ] Performance metrics satisfactory

---
**Deployment Date**: $(date)
**Version**: v$GIT_COMMIT_COUNT.$GIT_COMMIT_HASH
**Branch**: $GIT_BRANCH
EOF

    print_success "Deployment checklist created: DEPLOYMENT_CHECKLIST.md"
}

# Main execution
main() {
    print_header "🚀 Maintenance Dashboard - Production Portainer Deployment"
    echo "This script will prepare your application for production deployment to Portainer"
    echo ""
    
    # Check prerequisites
    check_prerequisites
    
    # Update version information
    update_version_info
    
    # Validate production configuration
    validate_production_config
    
    # Generate deployment summary
    generate_deployment_summary
    
    # Create deployment checklist
    create_deployment_checklist
    
    print_header "🎉 Deployment Preparation Complete!"
    echo "Your application is ready for production deployment to Portainer."
    echo "Follow the checklist in DEPLOYMENT_CHECKLIST.md for the deployment process."
    echo ""
    echo "Happy deploying! 🚀"
}

# Run main function
main "$@"
