# Automated Database Initialization System for Docker

## Overview

This automated database initialization system provides robust, self-healing database setup for your Django Maintenance Dashboard when running in Docker containers. It handles common Docker deployment issues like database connection failures, missing databases, and timing problems.

## 🎯 Problem Solved

The system addresses these common Docker deployment issues:

1. **Database Connection Failures**: Automatic retry logic with exponential backoff
2. **Missing Database**: Automatic database creation if it doesn't exist
3. **Container Timing Issues**: Proper dependency management and health checks
4. **Failed Initialization**: Automatic container restart and recovery
5. **Monitoring**: Continuous health monitoring and alerting

## 🔧 Components

### 1. Auto Database Initialization Script (`auto_init_database.py`)

**Purpose**: External monitoring and recovery script that can be run independently

**Features**:
- Container health monitoring
- Database connection testing
- Automatic database creation
- Container restart automation
- Comprehensive logging and reporting

**Usage**:
```bash
# Basic usage
python3 auto_init_database.py

# With custom parameters
python3 auto_init_database.py --max-retries 50 --retry-delay 3

# With production compose file
python3 auto_init_database.py --compose-file docker-compose.prod.yml

# With debug logging
python3 auto_init_database.py --log-level DEBUG
```

### 2. Docker Entrypoint Script (`docker-entrypoint.sh`)

**Purpose**: Internal container initialization with built-in retry logic

**Features**:
- Database readiness checking
- Automatic database creation
- Django initialization with retry
- Graceful error handling
- Health checks

**Environment Variables**:
- `SKIP_DB_INIT`: Skip database initialization (default: false)
- `SKIP_COLLECTSTATIC`: Skip static file collection (default: false)
- `MAX_RETRIES`: Maximum retry attempts (default: 30)
- `RETRY_DELAY`: Delay between retries in seconds (default: 5)

### 3. Enhanced Docker Compose (`docker-compose.enhanced.yml`)

**Purpose**: Production-ready container orchestration with monitoring

**Features**:
- Enhanced health checks
- Resource limits
- Automatic restart policies
- Built-in monitoring containers
- Proper dependency management

## 🚀 Quick Start

### 1. Basic Setup

```bash
# Make scripts executable
chmod +x auto_init_database.py
chmod +x docker-entrypoint.sh
chmod +x init_database.sh

# Use the enhanced Docker Compose
docker-compose -f docker-compose.enhanced.yml up -d
```

### 2. Monitor the Initialization

```bash
# Watch logs
docker-compose -f docker-compose.enhanced.yml logs -f web

# Check container health
docker-compose -f docker-compose.enhanced.yml ps

# Check system status
python3 auto_init_database.py --log-level INFO
```

### 3. In Case of Failure

```bash
# Run auto-recovery
python3 auto_init_database.py

# Check status report
cat auto_init_status.json

# Manual container restart
docker-compose -f docker-compose.enhanced.yml restart web
```

## 📋 Configuration Options

### Environment Variables

Create a `.env` file in your project root:

```env
# Database Configuration
DB_NAME=maintenance_dashboard
DB_USER=postgres
DB_PASSWORD=your_secure_password
DB_HOST=db
DB_PORT=5432

# Admin User Configuration
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@yourcompany.com
ADMIN_PASSWORD=your_secure_password

# Application Configuration
DEBUG=False
SECRET_KEY=your-production-secret-key
ALLOWED_HOSTS=localhost,127.0.0.1,yourdomain.com

# Automation Configuration
MAX_RETRIES=30
RETRY_DELAY=5
SKIP_DB_INIT=false
SKIP_COLLECTSTATIC=false

# Monitoring Configuration
HEALTHCHECK_INTERVAL=30
DB_READY_TIMEOUT=300
```

### Docker Compose Profiles

The enhanced Docker Compose supports different profiles:

```bash
# Development with monitoring
docker-compose -f docker-compose.enhanced.yml --profile dev up -d

# Production without monitoring
docker-compose -f docker-compose.enhanced.yml --profile prod up -d

# Full monitoring suite
docker-compose -f docker-compose.enhanced.yml --profile monitoring up -d
```

## 🔍 Monitoring and Troubleshooting

### 1. Health Check Endpoints

The system provides several health check endpoints:

- **Database Health**: `http://localhost:4405/health/db/`
- **Application Health**: `http://localhost:4405/health/`
- **Admin Interface**: `http://localhost:4405/admin/`

### 2. Log Files

- **Container Logs**: `docker-compose logs -f web`
- **Auto-Init Logs**: `auto_init_db.log`
- **Health Check Logs**: Check container logs for monitoring services

### 3. Status Reports

```bash
# Generate status report
python3 auto_init_database.py

# View detailed status
cat auto_init_status.json | jq .

# Check container resources
docker stats
```

### 4. Common Issues and Solutions

#### Issue: Database Connection Timeout
```bash
# Check database container
docker logs maintenance_db

# Verify database is ready
docker exec maintenance_db pg_isready -U postgres -d maintenance_dashboard

# Run auto-recovery
python3 auto_init_database.py
```

#### Issue: Web Container Failing to Start
```bash
# Check web container logs
docker logs maintenance_web

# Restart with debug
docker-compose -f docker-compose.enhanced.yml restart web
docker-compose -f docker-compose.enhanced.yml logs -f web

# Manual initialization
docker exec maintenance_web python manage.py init_database
```

#### Issue: Static Files Not Collecting
```bash
# Run collectstatic manually
docker exec maintenance_web python manage.py collectstatic --noinput

# Check file permissions
docker exec maintenance_web ls -la /app/staticfiles/

# Restart without collectstatic
docker-compose -f docker-compose.enhanced.yml up -d -e SKIP_COLLECTSTATIC=true
```

## 🔄 Automatic Recovery

### 1. Container Level Recovery

The system automatically handles:
- Database connection retries
- Database creation
- Django migrations
- Static file collection
- Container restarts

### 2. System Level Recovery

The monitoring script (`monitor_database.sh`) continuously:
- Checks container health
- Monitors database connectivity
- Triggers auto-recovery when needed
- Logs all events

### 3. Manual Recovery

If automatic recovery fails:

```bash
# Stop all containers
docker-compose -f docker-compose.enhanced.yml down

# Remove volumes (nuclear option)
docker volume prune

# Start with fresh state
docker-compose -f docker-compose.enhanced.yml up -d

# Run initialization
python3 auto_init_database.py
```

## 📊 Performance Monitoring

### 1. Resource Usage

```bash
# Check container resource usage
docker stats

# Check database performance
docker exec maintenance_db psql -U postgres -d maintenance_dashboard -c "SELECT * FROM pg_stat_activity;"

# Check application performance
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:4405/health/
```

### 2. Database Metrics

```bash
# Database size
docker exec maintenance_db psql -U postgres -d maintenance_dashboard -c "SELECT pg_size_pretty(pg_database_size('maintenance_dashboard'));"

# Active connections
docker exec maintenance_db psql -U postgres -d maintenance_dashboard -c "SELECT count(*) FROM pg_stat_activity;"

# Table statistics
docker exec maintenance_db psql -U postgres -d maintenance_dashboard -c "SELECT schemaname,tablename,n_live_tup FROM pg_stat_user_tables;"
```

## 🔧 Customization

### 1. Custom Initialization Script

Create `custom_init.py`:

```python
#!/usr/bin/env python3
"""Custom initialization script."""

from auto_init_database import AutoInitDB

# Custom configuration
config = {
    'MAX_RETRIES': 50,
    'RETRY_DELAY': 3,
    'LOG_LEVEL': 'DEBUG'
}

# Run with custom config
auto_init = AutoInitDB(config)
auto_init.run()
```

### 2. Custom Health Checks

Add to Django `urls.py`:

```python
from django.urls import path
from django.http import JsonResponse
from django.db import connection

def health_check(request):
    """Custom health check endpoint."""
    try:
        # Check database
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        return JsonResponse({
            'status': 'healthy',
            'database': 'connected',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return JsonResponse({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }, status=503)

urlpatterns = [
    # ... other patterns
    path('health/', health_check, name='health_check'),
]
```

## 🚨 Production Deployment

### 1. Security Considerations

- Use strong passwords for database and admin users
- Set `DEBUG=False` in production
- Use proper SSL certificates
- Configure firewall rules
- Regular security updates

### 2. Backup Strategy

```bash
# Database backup
docker exec maintenance_db pg_dump -U postgres maintenance_dashboard > backup.sql

# Volume backup
docker run --rm -v maintenance_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz /data

# Automated backups
# Add to crontab:
0 2 * * * /path/to/backup_script.sh
```

### 3. Scaling Considerations

- Use separate database server for production
- Implement load balancing for web containers
- Use Redis cluster for high availability
- Configure monitoring and alerting

## 📚 API Reference

### Auto Init Database Class

```python
class AutoInitDB:
    def __init__(self, config_override=None):
        """Initialize with optional configuration override."""
        pass
    
    def run(self):
        """Main execution method."""
        pass
    
    def monitor_and_recover(self):
        """Monitor containers and recover from failures."""
        pass
    
    def check_container_status(self, service):
        """Check the status of a Docker container."""
        pass
    
    def create_database_if_missing(self):
        """Create database if it doesn't exist."""
        pass
    
    def restart_container(self, service):
        """Restart a Docker container."""
        pass
```

### Command Line Options

```bash
python3 auto_init_database.py [OPTIONS]

Options:
  --max-retries INTEGER     Maximum retry attempts (default: 30)
  --retry-delay INTEGER     Delay between retries in seconds (default: 5)
  --compose-file TEXT       Docker Compose file (default: docker-compose.yml)
  --log-level [DEBUG|INFO|WARNING|ERROR]  Log level (default: INFO)
  --help                    Show this message and exit
```

## 🆘 Support and Troubleshooting

### Common Error Messages

1. **"Database connection failed"**
   - Check if database container is running
   - Verify database credentials
   - Run auto-recovery script

2. **"Container not found"**
   - Check container naming in Docker Compose
   - Verify containers are running
   - Update container names in configuration

3. **"Timeout waiting for database"**
   - Increase timeout values
   - Check database resource limits
   - Verify network connectivity

### Getting Help

1. Check the logs: `docker-compose logs -f`
2. Run diagnostics: `python3 auto_init_database.py --log-level DEBUG`
3. Generate status report: Review `auto_init_status.json`
4. Manual recovery: Follow the recovery procedures above

## 🔄 Updates and Maintenance

### Regular Maintenance

```bash
# Update containers
docker-compose pull

# Clean up unused resources
docker system prune -f

# Update database statistics
docker exec maintenance_db psql -U postgres -d maintenance_dashboard -c "ANALYZE;"

# Check for security updates
docker scan maintenance_web
```

### Monitoring Setup

Set up monitoring with your preferred tools:
- **Prometheus**: For metrics collection
- **Grafana**: For visualization
- **AlertManager**: For notifications
- **ELK Stack**: For log analysis

This automated system ensures your Django Maintenance Dashboard runs reliably in Docker with minimal manual intervention, providing robust error recovery and continuous monitoring capabilities.