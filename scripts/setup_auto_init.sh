#!/bin/bash

# Setup Script for Automated Database Initialization System
# This script sets up the complete automated database initialization system

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${CYAN}${1}${NC}"
    echo "$(printf '=%.0s' {1..60})"
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

# Check if running as root
check_permissions() {
    if [[ $EUID -eq 0 ]]; then
        print_warning "This script should not be run as root. Please run as a regular user."
        exit 1
    fi
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed. Please install Python 3 first."
        exit 1
    fi
    
    # Check Docker daemon
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running. Please start Docker service."
        exit 1
    fi
    
    print_success "All prerequisites are met"
}

# Setup file permissions
setup_permissions() {
    print_status "Setting up file permissions..."
    
    # Make scripts executable
    chmod +x auto_init_database.py
    chmod +x docker-entrypoint.sh
    chmod +x init_database.sh
    
    # Create necessary directories
    mkdir -p logs
    mkdir -p backups
    mkdir -p monitoring
    
    print_success "File permissions configured"
}

# Create environment file
create_env_file() {
    if [[ ! -f .env ]]; then
        print_status "Creating .env file..."
        
        cat > .env << EOL
# Database Configuration
DB_NAME=maintenance_dashboard
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=db
DB_PORT=5432

# Admin User Configuration
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@maintenance.local
ADMIN_PASSWORD=temppass123

# Application Configuration
DEBUG=True
SECRET_KEY=django-insecure-docker-development-key-change-in-production
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0,maintenance.errorlog.app

# Automation Configuration
MAX_RETRIES=30
RETRY_DELAY=5
SKIP_DB_INIT=false
SKIP_COLLECTSTATIC=false

# Monitoring Configuration
HEALTHCHECK_INTERVAL=30
DB_READY_TIMEOUT=300
WEB_PORT=4405
REDIS_PORT=6379

# Container Configuration
COMPOSE_PROJECT_NAME=maintenance
EOL
        
        print_success ".env file created"
        print_warning "Please review and update the .env file with your specific configuration"
    else
        print_warning ".env file already exists, skipping creation"
    fi
}

# Create production environment file
create_prod_env() {
    if [[ ! -f .env.prod ]]; then
        print_status "Creating production .env file..."
        
        cat > .env.prod << EOL
# Production Database Configuration
DB_NAME=maintenance_dashboard
DB_USER=postgres
DB_PASSWORD=CHANGE_ME_IN_PRODUCTION
DB_HOST=db
DB_PORT=5432

# Production Admin User Configuration
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@yourcompany.com
ADMIN_PASSWORD=CHANGE_ME_IN_PRODUCTION

# Production Application Configuration
DEBUG=False
SECRET_KEY=CHANGE_ME_IN_PRODUCTION
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Automation Configuration
MAX_RETRIES=50
RETRY_DELAY=3
SKIP_DB_INIT=false
SKIP_COLLECTSTATIC=false

# Monitoring Configuration
HEALTHCHECK_INTERVAL=60
DB_READY_TIMEOUT=600
WEB_PORT=80
REDIS_PORT=6379

# Container Configuration
COMPOSE_PROJECT_NAME=maintenance_prod
EOL
        
        print_success ".env.prod file created"
        print_warning "IMPORTANT: Update .env.prod with secure production values!"
    else
        print_warning ".env.prod file already exists, skipping creation"
    fi
}

# Create monitoring script
create_monitoring_script() {
    print_status "Creating monitoring script..."
    
    cat > monitor_database.sh << 'EOL'
#!/bin/bash
# Continuous monitoring script for database initialization
# This script monitors the containers and automatically fixes issues

LOG_FILE="logs/monitor.log"
ALERT_EMAIL=""  # Set this to receive email alerts

log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

send_alert() {
    local message="$1"
    log_message "ALERT: $message"
    
    if [[ -n "$ALERT_EMAIL" ]]; then
        echo "$message" | mail -s "Database Monitor Alert" "$ALERT_EMAIL"
    fi
}

check_container_health() {
    local container_name="$1"
    local health_status
    
    health_status=$(docker inspect --format='{{.State.Health.Status}}' "$container_name" 2>/dev/null || echo "none")
    
    if [[ "$health_status" == "healthy" ]]; then
        return 0
    else
        return 1
    fi
}

main_monitor_loop() {
    log_message "Starting database monitoring..."
    
    while true; do
        # Check web container
        if docker ps --filter name=maintenance_web --format "table {{.Names}}" | grep -q maintenance_web; then
            if check_container_health maintenance_web; then
                log_message "Web container is healthy"
            else
                log_message "Web container is unhealthy, triggering recovery..."
                send_alert "Web container is unhealthy"
                python3 auto_init_database.py --log-level WARNING
            fi
        else
            log_message "Web container not running, starting auto-recovery..."
            send_alert "Web container not running"
            python3 auto_init_database.py --log-level WARNING
        fi
        
        # Check database connection
        if docker exec maintenance_db pg_isready -U postgres -d maintenance_dashboard > /dev/null 2>&1; then
            log_message "Database connection is healthy"
        else
            log_message "Database connection failed, starting auto-recovery..."
            send_alert "Database connection failed"
            python3 auto_init_database.py --log-level WARNING
        fi
        
        # Check Redis connection
        if docker exec maintenance_redis redis-cli ping > /dev/null 2>&1; then
            log_message "Redis connection is healthy"
        else
            log_message "Redis connection failed"
            send_alert "Redis connection failed"
        fi
        
        # Wait before next check
        sleep 30
    done
}

# Create log directory
mkdir -p logs

# Start monitoring
main_monitor_loop
EOL
    
    chmod +x monitor_database.sh
    print_success "Monitoring script created"
}

# Create backup script
create_backup_script() {
    print_status "Creating backup script..."
    
    cat > backup_database.sh << 'EOL'
#!/bin/bash
# Database backup script

BACKUP_DIR="backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DB_NAME="maintenance_dashboard"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Database backup
echo "Creating database backup..."
docker exec maintenance_db pg_dump -U postgres "$DB_NAME" > "$BACKUP_DIR/db_backup_$TIMESTAMP.sql"

# Volume backup
echo "Creating volume backup..."
docker run --rm -v maintenance_postgres_data:/data -v $(pwd):/backup alpine tar czf "/backup/$BACKUP_DIR/volume_backup_$TIMESTAMP.tar.gz" /data

# Cleanup old backups (keep last 7 days)
find "$BACKUP_DIR" -name "*.sql" -mtime +7 -delete
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_DIR/db_backup_$TIMESTAMP.sql"
EOL
    
    chmod +x backup_database.sh
    print_success "Backup script created"
}

# Test the setup
test_setup() {
    print_status "Testing the setup..."
    
    # Test auto_init_database.py
    if python3 auto_init_database.py --help > /dev/null 2>&1; then
        print_success "Auto-init script is working"
    else
        print_error "Auto-init script has issues"
        return 1
    fi
    
    # Test docker-compose file
    if docker-compose -f docker-compose.enhanced.yml config > /dev/null 2>&1; then
        print_success "Docker Compose configuration is valid"
    else
        print_error "Docker Compose configuration has issues"
        return 1
    fi
    
    print_success "Setup test completed successfully"
}

# Create systemd service (optional)
create_systemd_service() {
    if [[ "$1" == "--systemd" ]]; then
        print_status "Creating systemd service..."
        
        cat > maintenance-monitor.service << EOL
[Unit]
Description=Maintenance Dashboard Database Monitor
After=docker.service
Requires=docker.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
ExecStart=/bin/bash $(pwd)/monitor_database.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOL
        
        print_success "Systemd service file created: maintenance-monitor.service"
        print_status "To install: sudo cp maintenance-monitor.service /etc/systemd/system/"
        print_status "To enable: sudo systemctl enable maintenance-monitor.service"
        print_status "To start: sudo systemctl start maintenance-monitor.service"
    fi
}

# Create quick start script
create_quick_start() {
    print_status "Creating quick start script..."
    
    cat > quick_start.sh << 'EOL'
#!/bin/bash
# Quick start script for the maintenance dashboard

echo "🚀 Starting Maintenance Dashboard..."

# Stop any existing containers
docker-compose -f docker-compose.enhanced.yml down

# Start the containers
docker-compose -f docker-compose.enhanced.yml up -d

# Wait a moment for containers to start
sleep 10

# Check status
echo "📊 Container Status:"
docker-compose -f docker-compose.enhanced.yml ps

# Run auto-init if needed
echo "🔧 Running auto-initialization..."
python3 auto_init_database.py

echo "✅ Maintenance Dashboard is ready!"
echo "   Web Interface: http://localhost:4405"
echo "   Admin Panel: http://localhost:4405/admin"
echo "   Default Login: admin / temppass123"
EOL
    
    chmod +x quick_start.sh
    print_success "Quick start script created"
}

# Create status check script
create_status_script() {
    print_status "Creating status check script..."
    
    cat > check_status.sh << 'EOL'
#!/bin/bash
# System status check script

echo "=== MAINTENANCE DASHBOARD STATUS ==="
echo

# Container status
echo "📦 Container Status:"
docker-compose -f docker-compose.enhanced.yml ps
echo

# Health checks
echo "🏥 Health Checks:"
for container in maintenance_web maintenance_db maintenance_redis; do
    health=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "no health check")
    echo "  $container: $health"
done
echo

# Database connection
echo "🗄️  Database Status:"
if docker exec maintenance_db pg_isready -U postgres -d maintenance_dashboard > /dev/null 2>&1; then
    echo "  Database: Connected ✅"
else
    echo "  Database: Disconnected ❌"
fi

# Web service
echo "🌐 Web Service:"
if curl -f http://localhost:4405/health/ > /dev/null 2>&1; then
    echo "  Web Service: Running ✅"
else
    echo "  Web Service: Not responding ❌"
fi

# Resources
echo "💻 Resource Usage:"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" | head -5

echo
echo "=== END STATUS ==="
EOL
    
    chmod +x check_status.sh
    print_success "Status check script created"
}

# Main setup function
main() {
    print_header "🚀 AUTOMATED DATABASE INITIALIZATION SETUP"
    
    # Check if we're in the right directory
    if [[ ! -f "manage.py" ]]; then
        print_error "This script should be run from the Django project root directory"
        exit 1
    fi
    
    # Parse arguments
    CREATE_SYSTEMD=false
    if [[ "$1" == "--systemd" ]]; then
        CREATE_SYSTEMD=true
    fi
    
    print_status "Setting up automated database initialization system..."
    
    # Run setup steps
    check_permissions
    check_prerequisites
    setup_permissions
    create_env_file
    create_prod_env
    create_monitoring_script
    create_backup_script
    create_quick_start
    create_status_script
    
    if [[ "$CREATE_SYSTEMD" == true ]]; then
        create_systemd_service --systemd
    fi
    
    test_setup
    
    print_header "✅ SETUP COMPLETED SUCCESSFULLY"
    
    echo
    print_success "Automated database initialization system is ready!"
    echo
    print_status "Quick Start Commands:"
    echo "  Start system:     ./quick_start.sh"
    echo "  Check status:     ./check_status.sh"
    echo "  Run auto-init:    python3 auto_init_database.py"
    echo "  Start monitoring: ./monitor_database.sh"
    echo "  Backup database:  ./backup_database.sh"
    echo
    print_status "Configuration Files:"
    echo "  Development:      .env"
    echo "  Production:       .env.prod"
    echo "  Docker Compose:   docker-compose.enhanced.yml"
    echo
    print_warning "Next Steps:"
    echo "  1. Review and update .env file with your configuration"
    echo "  2. For production, update .env.prod with secure values"
    echo "  3. Run ./quick_start.sh to start the system"
    echo "  4. Access the dashboard at http://localhost:4405"
    echo
    print_status "Documentation:"
    echo "  Complete Guide:   AUTOMATED_DB_INIT_GUIDE.md"
    echo "  Original Guide:   DATABASE_INITIALIZATION_GUIDE.md"
    echo
    print_success "🎉 Setup complete! Your database initialization is now automated."
}

# Run main function
main "$@"