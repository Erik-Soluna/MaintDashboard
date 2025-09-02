#!/bin/bash

# Production Environment Validation Script for Maintenance Dashboard
# This script validates that the production environment is properly configured
# Run this script to verify your production setup before deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Validation results
VALIDATION_PASSED=true
ISSUES_FOUND=0

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
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    VALIDATION_PASSED=false
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
}

# Function to validate file exists and is readable
validate_file() {
    local file_path="$1"
    local description="$2"
    
    if [ -f "$file_path" ]; then
        if [ -r "$file_path" ]; then
            print_success "$description: $file_path"
            return 0
        else
            print_error "$description: $file_path (not readable)"
            return 1
        fi
    else
        print_error "$description: $file_path (not found)"
        return 1
    fi
}

# Function to validate environment variables in file
validate_env_vars() {
    local file_path="$1"
    local description="$2"
    
    if [ ! -f "$file_path" ]; then
        print_error "$description: File not found"
        return 1
    fi
    
    print_status "Validating environment variables in $file_path"
    
    # Required environment variables
    local required_vars=(
        "GIT_COMMIT_COUNT"
        "GIT_COMMIT_HASH"
        "GIT_BRANCH"
        "GIT_COMMIT_DATE"
        "DB_NAME"
        "DB_USER"
        "DB_PASSWORD"
        "POSTGRES_PASSWORD"
        "SECRET_KEY"
        "ADMIN_USERNAME"
        "ADMIN_EMAIL"
        "ADMIN_PASSWORD"
    )
    
    local missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if ! grep -q "$var=" "$file_path"; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -eq 0 ]; then
        print_success "All required environment variables present"
    else
        print_error "Missing required environment variables: ${missing_vars[*]}"
        return 1
    fi
    
    # Validate specific values
    if grep -q "DEBUG=True" "$file_path"; then
        print_warning "Debug mode is enabled in production environment"
    fi
    
    if grep -q "SECURE_SSL_REDIRECT=False" "$file_path"; then
        print_warning "SSL redirect is disabled in production environment"
    fi
    
    # Check for default passwords
    if grep -q "temppass123\|password123\|admin123" "$file_path"; then
        print_error "Default/weak passwords detected in environment file"
    fi
    
    return 0
}

# Function to validate Docker Compose file
validate_docker_compose() {
    local file_path="$1"
    local description="$2"
    
    if [ ! -f "$file_path" ]; then
        print_error "$description: File not found"
        return 1
    fi
    
    print_status "Validating Docker Compose file: $file_path"
    
    # Check for required services
    local required_services=("db" "redis" "web" "celery" "celery-beat")
    local missing_services=()
    
    for service in "${required_services[@]}"; do
        if ! grep -q "  $service:" "$file_path"; then
            missing_services+=("$service")
        fi
    done
    
    if [ ${#missing_services[@]} -eq 0 ]; then
        print_success "All required services present"
    else
        print_error "Missing required services: ${missing_services[*]}"
        return 1
    fi
    
    # Check for security settings
    if ! grep -q "SECURE_SSL_REDIRECT=True" "$file_path"; then
        print_warning "SSL redirect not enabled"
    fi
    
    if ! grep -q "DEBUG=False" "$file_path"; then
        print_warning "Debug mode not disabled"
    fi
    
    # Check for health checks
    if ! grep -q "healthcheck:" "$file_path"; then
        print_warning "Health checks not configured"
    fi
    
    # Check for resource limits
    if ! grep -q "deploy:" "$file_path"; then
        print_warning "Resource limits not configured"
    fi
    
    return 0
}

# Function to validate Dockerfile
validate_dockerfile() {
    local file_path="$1"
    
    if [ ! -f "$file_path" ]; then
        print_error "Dockerfile not found"
        return 1
    fi
    
    print_status "Validating Dockerfile: $file_path"
    
    # Check for required build args
    if ! grep -q "ARG GIT_COMMIT_COUNT" "$file_path"; then
        print_warning "GIT_COMMIT_COUNT build arg not found"
    fi
    
    if ! grep -q "ARG GIT_COMMIT_HASH" "$file_path"; then
        print_warning "GIT_COMMIT_HASH build arg not found"
    fi
    
    # Check for security best practices
    if ! grep -q "USER appuser" "$file_path"; then
        print_warning "Non-root user not configured (security best practice)"
    fi
    
    # Check for health check
    if ! grep -q "HEALTHCHECK" "$file_path"; then
        print_warning "Health check not configured in Dockerfile"
    fi
    
    return 0
}

# Function to validate entrypoint script
validate_entrypoint() {
    local file_path="$1"
    
    if [ ! -f "$file_path" ]; then
        print_error "Entrypoint script not found: $file_path"
        return 1
    fi
    
    print_status "Validating entrypoint script: $file_path"
    
    # Check if script is executable
    if [ ! -x "$file_path" ]; then
        print_warning "Entrypoint script is not executable"
    fi
    
    # Check for required functions
    local required_functions=("check_database_ready" "ensure_database_exists" "run_database_initialization")
    local missing_functions=()
    
    for func in "${required_functions[@]}"; do
        if ! grep -q "$func()" "$file_path"; then
            missing_functions+=("$func")
        fi
    done
    
    if [ ${#missing_functions[@]} -eq 0 ]; then
        print_success "All required functions present in entrypoint script"
    else
        print_error "Missing required functions: ${missing_functions[*]}"
        return 1
    fi
    
    return 0
}

# Function to validate version information
validate_version_info() {
    print_status "Validating version information"
    
    # Check version.json
    if [ -f "version.json" ]; then
        if command -v python3 &> /dev/null; then
            if python3 -c "import json; json.load(open('version.json'))" 2>/dev/null; then
                print_success "version.json is valid JSON"
            else
                print_error "version.json contains invalid JSON"
                return 1
            fi
        else
            print_warning "Python3 not available, cannot validate version.json"
        fi
    else
        print_warning "version.json not found"
    fi
    
    # Check if version information is up to date
    if [ -f "version.json" ] && command -v git &> /dev/null; then
        local current_commit=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
        local file_commit=$(grep -o '"commit_hash": "[^"]*"' version.json | cut -d'"' -f4 2>/dev/null || echo "unknown")
        
        if [ "$current_commit" != "unknown" ] && [ "$file_commit" != "unknown" ]; then
            if [ "$current_commit" = "$file_commit" ]; then
                print_success "Version information is up to date"
            else
                print_warning "Version information may be outdated (current: $current_commit, file: $file_commit)"
            fi
        fi
    fi
    
    return 0
}

# Function to validate security settings
validate_security() {
    print_status "Validating security settings"
    
    local security_issues=0
    
    # Check for default secrets (exclude development files)
    if grep -r "django-insecure\|temppass123\|password123\|admin123" . --include="*.yml" --include="*.yaml" --include="*.env" --include="*.template" 2>/dev/null | grep -v "docker-compose.yml"; then
        print_error "Default/weak secrets detected in configuration files"
        security_issues=$((security_issues + 1))
    fi
    
    # Check for exposed sensitive information
    if grep -r "password.*=" . --include="*.yml" --include="*.yaml" --include="*.env" --include="*.template" 2>/dev/null | grep -v "POSTGRES_PASSWORD\|DB_PASSWORD\|ADMIN_PASSWORD" | grep -v "SecureProdPassword\|DevPassword"; then
        print_warning "Potential password exposure in configuration files"
        security_issues=$((security_issues + 1))
    fi
    
    if [ $security_issues -eq 0 ]; then
        print_success "No obvious security issues detected"
    fi
    
    return 0
}

# Function to generate validation report
generate_report() {
    print_header "📊 Validation Report"
    
    if [ "$VALIDATION_PASSED" = true ]; then
        print_success "✅ Production environment validation PASSED"
        echo ""
        echo "Your production environment is properly configured and ready for deployment."
        echo ""
        echo "Next steps:"
        echo "1. Run the deployment script: ./scripts/portainer_deploy_production.sh"
        echo "2. Follow the deployment checklist"
        echo "3. Monitor the deployment process"
    else
        print_error "❌ Production environment validation FAILED"
        echo ""
        echo "Found $ISSUES_FOUND issue(s) that need to be addressed before deployment."
        echo ""
        echo "Please fix the issues above and run this validation script again."
        echo ""
        echo "Common fixes:"
        echo "- Update environment variables with proper values"
        echo "- Enable security settings (SSL, debug mode off)"
        echo "- Replace default passwords with secure ones"
        echo "- Ensure all required files are present"
    fi
    
    echo ""
    echo "Validation completed at: $(date)"
}

# Main execution
main() {
    print_header "🔍 Production Environment Validation"
    echo "This script will validate your production environment configuration"
    echo ""
    
    # Validate required files
    print_header "📁 File Validation"
    validate_file "portainer-stack.yml" "Production stack file"
    validate_file "portainer.env.template" "Environment template file"
    validate_file "Dockerfile" "Docker build file"
    validate_file "scripts/deployment/docker-entrypoint.sh" "Container entrypoint script"
    
    # Validate environment configuration
    print_header "🔧 Environment Configuration"
    validate_env_vars "portainer.env.template" "Environment template"
    
    # Validate Docker configuration
    print_header "🐳 Docker Configuration"
    validate_docker_compose "portainer-stack.yml" "Production stack"
    validate_dockerfile "Dockerfile"
    validate_entrypoint "scripts/deployment/docker-entrypoint.sh"
    
    # Validate version information
    print_header "📊 Version Information"
    validate_version_info
    
    # Validate security settings
    print_header "🔒 Security Validation"
    validate_security
    
    # Generate final report
    generate_report
    
    # Exit with appropriate code
    if [ "$VALIDATION_PASSED" = true ]; then
        exit 0
    else
        exit 1
    fi
}

# Run main function
main "$@"
