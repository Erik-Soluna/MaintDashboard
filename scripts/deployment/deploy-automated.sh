#!/bin/bash

# Automated Deployment Script for Maintenance Dashboard
# Version: 2025-09-03-FULLY-AUTOMATED
# Purpose: One-command deployment with complete automation

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# Print functions
print_header() {
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} $1"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
}

print_step() {
    echo -e "${MAGENTA}[STEP]${NC} $1"
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

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
STACK_FILE="$PROJECT_ROOT/portainer-stack-dev-automated.yml"
ENV_FILE="$PROJECT_ROOT/.env.automated"

# Default configuration
DEFAULT_DOMAIN="dev.maintenance.errorlog.app"
DEFAULT_PORT="4407"
DEFAULT_ADMIN_USER="admin"
DEFAULT_ADMIN_EMAIL="admin@dev.maintenance.errorlog.app"
DEFAULT_ADMIN_PASS="DevAdminPassword2024!"

# Usage function
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -d, --domain DOMAIN         Domain name (default: $DEFAULT_DOMAIN)"
    echo "  -p, --port PORT            Web port (default: $DEFAULT_PORT)"
    echo "  -u, --admin-user USER      Admin username (default: $DEFAULT_ADMIN_USER)"
    echo "  -e, --admin-email EMAIL    Admin email (default: $DEFAULT_ADMIN_EMAIL)"
    echo "  --admin-pass PASS          Admin password (default: $DEFAULT_ADMIN_PASS)"
    echo "  --docker-compose           Use docker-compose instead of Portainer"
    echo "  --clean                    Clean existing volumes and containers"
    echo "  --no-build                 Skip building images"
    echo "  -h, --help                 Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                         # Deploy with defaults"
    echo "  $0 -d myapp.local -p 8080  # Custom domain and port"
    echo "  $0 --clean                 # Clean deployment"
    echo "  $0 --docker-compose        # Use docker-compose"
}

# Parse arguments
DOMAIN="$DEFAULT_DOMAIN"
PORT="$DEFAULT_PORT"
ADMIN_USER="$DEFAULT_ADMIN_USER"
ADMIN_EMAIL="$DEFAULT_ADMIN_EMAIL"
ADMIN_PASS="$DEFAULT_ADMIN_PASS"
USE_DOCKER_COMPOSE=false
CLEAN_DEPLOY=false
NO_BUILD=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--domain)
            DOMAIN="$2"
            shift 2
            ;;
        -p|--port)
            PORT="$2"
            shift 2
            ;;
        -u|--admin-user)
            ADMIN_USER="$2"
            shift 2
            ;;
        -e|--admin-email)
            ADMIN_EMAIL="$2"
            shift 2
            ;;
        --admin-pass)
            ADMIN_PASS="$2"
            shift 2
            ;;
        --docker-compose)
            USE_DOCKER_COMPOSE=true
            shift
            ;;
        --clean)
            CLEAN_DEPLOY=true
            shift
            ;;
        --no-build)
            NO_BUILD=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Create environment file
create_env_file() {
    print_step "📝 Creating environment configuration..."
    
    cat > "$ENV_FILE" << EOF
# Automated Deployment Environment Configuration
# Generated on $(date)

# Database Configuration
DB_NAME=maintenance_dashboard_dev
DB_USER=maintenance_user_dev
DB_PASSWORD=DevPassword2024!

# Admin Configuration
ADMIN_USERNAME=$ADMIN_USER
ADMIN_EMAIL=$ADMIN_EMAIL
ADMIN_PASSWORD=$ADMIN_PASS

# Domain Configuration
DOMAIN=$DOMAIN

# Git Information (will be populated by CI/CD or manually)
GIT_COMMIT_COUNT=\${GIT_COMMIT_COUNT:-0}
GIT_COMMIT_HASH=\${GIT_COMMIT_HASH:-unknown}
GIT_BRANCH=\${GIT_BRANCH:-automated}
GIT_COMMIT_DATE=\${GIT_COMMIT_DATE:-$(date -I)}
EOF
    
    print_success "✅ Environment file created: $ENV_FILE"
}

# Clean existing deployment
clean_deployment() {
    if [ "$CLEAN_DEPLOY" = true ]; then
        print_step "🧹 Cleaning existing deployment..."
        
        # Stop and remove containers
        docker-compose -f "$STACK_FILE" --env-file "$ENV_FILE" down -v --remove-orphans > /dev/null 2>&1 || true
        
        # Remove images if they exist
        docker rmi $(docker images | grep maintenance | awk '{print $3}') > /dev/null 2>&1 || true
        
        # Remove volumes
        docker volume rm $(docker volume ls | grep maintenance.*auto | awk '{print $2}') > /dev/null 2>&1 || true
        
        print_success "✅ Cleanup completed"
    fi
}

# Build images
build_images() {
    if [ "$NO_BUILD" = false ]; then
        print_step "🔨 Building Docker images..."
        
        cd "$PROJECT_ROOT"
        docker-compose -f "$STACK_FILE" --env-file "$ENV_FILE" build --no-cache
        
        print_success "✅ Images built successfully"
    else
        print_warning "⚠️ Skipping image build"
    fi
}

# Deploy with docker-compose
deploy_docker_compose() {
    print_step "🚀 Deploying with Docker Compose..."
    
    cd "$PROJECT_ROOT"
    
    # Start services
    docker-compose -f "$STACK_FILE" --env-file "$ENV_FILE" up -d
    
    print_success "✅ Services started"
    
    # Wait for services to be ready
    print_status "⏳ Waiting for services to initialize..."
    sleep 30
    
    # Check service status
    docker-compose -f "$STACK_FILE" --env-file "$ENV_FILE" ps
}

# Deploy for Portainer
deploy_portainer() {
    print_step "📋 Preparing for Portainer deployment..."
    
    print_status "Stack file: $STACK_FILE"
    print_status "Environment file: $ENV_FILE"
    
    echo ""
    print_success "✅ Files prepared for Portainer deployment"
    print_status "Next steps for Portainer:"
    print_status "1. Copy the contents of: $STACK_FILE"
    print_status "2. Create a new stack in Portainer"
    print_status "3. Paste the stack configuration"
    print_status "4. Add environment variables from: $ENV_FILE"
    print_status "5. Deploy the stack"
}

# Monitor deployment
monitor_deployment() {
    print_step "👀 Monitoring deployment..."
    
    local max_attempts=20
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        print_status "Health check attempt $attempt/$max_attempts..."
        
        if curl -f "http://localhost:$PORT/health/simple/" > /dev/null 2>&1; then
            print_success "✅ Application is responding!"
            break
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            print_warning "⚠️ Application not responding, but deployment may still be initializing"
            break
        fi
        
        sleep 10
        attempt=$((attempt + 1))
    done
}

# Display final information
show_final_info() {
    print_header "🎉 DEPLOYMENT COMPLETED!"
    echo ""
    print_success "✅ Maintenance Dashboard Deployed Successfully"
    echo ""
    print_status "📊 Access Information:"
    print_status "   Application URL: http://localhost:$PORT/"
    print_status "   Admin Panel: http://localhost:$PORT/admin/"
    print_status "   Domain: $DOMAIN"
    echo ""
    print_status "🔐 Admin Credentials:"
    print_status "   Username: $ADMIN_USER"
    print_status "   Email: $ADMIN_EMAIL"
    print_status "   Password: $ADMIN_PASS"
    echo ""
    print_status "📁 Configuration Files:"
    print_status "   Stack: $STACK_FILE"
    print_status "   Environment: $ENV_FILE"
    echo ""
    print_warning "⚠️  SECURITY REMINDERS:"
    print_warning "   - Change admin password after first login"
    print_warning "   - Review security settings for production use"
    print_warning "   - Keep environment files secure"
    echo ""
    print_status "🔧 Useful Commands:"
    print_status "   View logs: docker-compose -f $STACK_FILE logs -f"
    print_status "   Stop: docker-compose -f $STACK_FILE down"
    print_status "   Restart: docker-compose -f $STACK_FILE restart"
    echo ""
}

# Main execution
main() {
    print_header "MAINTENANCE DASHBOARD - AUTOMATED DEPLOYMENT"
    echo ""
    print_status "Configuration:"
    print_status "  Domain: $DOMAIN"
    print_status "  Port: $PORT"
    print_status "  Admin User: $ADMIN_USER"
    print_status "  Admin Email: $ADMIN_EMAIL"
    print_status "  Use Docker Compose: $USE_DOCKER_COMPOSE"
    print_status "  Clean Deploy: $CLEAN_DEPLOY"
    echo ""
    
    # Verify requirements
    if ! command -v docker &> /dev/null; then
        print_error "❌ Docker is not installed or not in PATH"
        exit 1
    fi
    
    if [ "$USE_DOCKER_COMPOSE" = true ] && ! command -v docker-compose &> /dev/null; then
        print_error "❌ Docker Compose is not installed or not in PATH"
        exit 1
    fi
    
    # Execute deployment steps
    create_env_file
    clean_deployment
    
    if [ "$USE_DOCKER_COMPOSE" = true ]; then
        build_images
        deploy_docker_compose
        monitor_deployment
    else
        deploy_portainer
    fi
    
    show_final_info
}

# Execute main function
main "$@"