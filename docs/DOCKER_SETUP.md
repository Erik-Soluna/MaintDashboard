# Docker Setup Guide

This project now uses two main Docker configuration files:

## Files

1. **`docker-compose.yml`** - Development/Testing environment with monitoring
2. **`portainer-stack.yml`** - Production-ready deployment for Portainer

## Quick Start

### Development/Testing
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Production (Portainer)
1. Upload `portainer-stack.yml` to Portainer
2. Deploy the stack
3. Configure environment variables as needed

## Environment Variables

The project includes environment templates for easy setup:

### Quick Setup
```bash
# Run the setup script
chmod +x setup-env.sh
./setup-env.sh
```

### Manual Setup
Choose one of the provided templates and rename it to `.env`:

**For Development:**
```bash
cp env.development .env
```

**For Production:**
```bash
cp env.production .env
```

### Environment File Contents

```bash
# Database Configuration
DB_NAME=maintenance_dashboard
DB_USER=postgres
DB_PASSWORD=postgres
DB_PORT=5432

# Redis Configuration
REDIS_PORT=6379

# Web Application
WEB_PORT=4405
DEBUG=True
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0,maintenance.errorlog.app,10.0.0.28

# Admin User Setup
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@maintenance.local
ADMIN_PASSWORD=your-secure-password

# Domain for Traefik
DOMAIN=your-domain.com

# Optional: Skip database initialization and static collection
SKIP_DB_INIT=false
SKIP_COLLECTSTATIC=false

# Optional: Retry settings for database connection
MAX_RETRIES=30
RETRY_DELAY=5

# Additional settings available in templates:
# - Email configuration
# - Backup settings
# - Monitoring configuration
# - Security settings

## Services

### Core Services
- **db**: PostgreSQL 15 database
- **redis**: Redis 7 cache/message broker
- **web**: Django web application
- **celery**: Background task worker
- **celery-beat**: Scheduled task scheduler

### Monitoring Services (Development only)
- **db-monitor**: Database health monitoring
- **web-monitor**: Web service health checking

## Features

### Development (`docker-compose.yml`)
- ✅ Environment variable support
- ✅ Health checks for all services
- ✅ Resource limits and reservations
- ✅ Monitoring services
- ✅ Auto-recovery capabilities
- ✅ Development-friendly settings

### Production (`portainer-stack.yml`)
- ✅ Production-optimized settings
- ✅ Gunicorn with optimized workers
- ✅ Database scheduler for Celery Beat
- ✅ Resource limits for production
- ✅ Health checks
- ✅ Traefik integration ready

## Networks

- **maintenance_network**: Internal communication
- **proxy-network**: External (for Traefik integration)

## Volumes

- **postgres_data**: Database persistence
- **static_volume**: Static files
- **media_volume**: User uploads

## Health Checks

All services include health checks:
- Database: `pg_isready`
- Redis: `redis-cli ping`
- Web: HTTP health endpoint
- Celery: Worker ping
- Celery Beat: Process check

## Troubleshooting

### Common Issues

1. **Database connection failed**
   - Check if PostgreSQL is running: `docker-compose ps db`
   - View logs: `docker-compose logs db`

2. **Web service not responding**
   - Check health: `docker-compose exec web curl http://localhost:8000/health/`
   - View logs: `docker-compose logs web`

3. **Celery tasks not processing**
   - Check worker status: `docker-compose exec celery celery -A maintenance_dashboard inspect active`
   - View logs: `docker-compose logs celery`

### Useful Commands

```bash
# Rebuild images
docker-compose build

# Restart specific service
docker-compose restart web

# View service status
docker-compose ps

# Execute commands in containers
docker-compose exec web python manage.py shell
docker-compose exec db psql -U postgres -d maintenance_dashboard

# Clean up
docker-compose down -v  # Removes volumes
docker-compose down --rmi all  # Removes images
```

## Environment Templates

The project includes pre-configured environment templates:

- **`env.development`** - Safe defaults for local development
- **`env.production`** - Secure settings for production deployment
- **`setup-env.sh`** - Interactive setup script

### Security Notes

- The `.env` file is automatically ignored by git (included in `.gitignore`)
- Production templates include secure passwords that should be changed
- Never commit the actual `.env` file to version control

## Migration from Old Files

The following files have been consolidated and removed:
- `docker-compose.enhanced.yml`
- `docker-compose.prod.yml`
- `portainer-stack-with-image.yml`

All functionality has been merged into the two main files. 