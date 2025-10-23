# 🚀 Automated Deployment Guide

**Maintenance Dashboard - Zero-Touch Deployment System**

This guide provides a complete automated deployment solution that handles all setup tasks including database migrations, admin user creation, and application configuration.

## 📋 Quick Start

### Option 1: Portainer Deployment (Recommended)

1. **Run the quickstart script:**
   ```bash
   ./scripts/deployment/portainer-quickstart.sh
   ```

2. **Deploy in Portainer:**
   - Open Portainer Web UI
   - Go to "Stacks" → "Add Stack"
   - Name: `maintenance-dashboard-auto`
   - Use the stack file: `portainer-stack-dev-automated.yml`
   - Add the environment variables provided by the script
   - Click "Deploy the stack"

3. **Wait for initialization (2-3 minutes)**

4. **Access your application:**
   - URL: http://localhost:4407/ (or your configured domain)
   - Admin: http://localhost:4407/admin/
   - Username: `admin`
   - Password: `DevAdminPassword2024!`

### Option 2: Docker Compose Deployment

```bash
./scripts/deployment/deploy-automated.sh --docker-compose
```

## 🎯 What Gets Automated

### ✅ Database Setup
- Automatic PostgreSQL database creation
- User and permissions setup
- Connection retry logic with 30 attempts
- Health checks and monitoring

### ✅ Django Application
- Complete migration execution (with conflict resolution)
- Admin superuser creation
- Static file collection
- Branding and initial data setup
- Health check endpoints

### ✅ Services
- Redis cache setup
- Celery worker and beat scheduler
- Proper service dependencies
- Health monitoring for all services

### ✅ Error Recovery
- Migration conflict resolution
- Database connection retry logic
- Graceful failure handling
- Comprehensive logging

## 📁 Files Overview

### Core Automation Files
```
scripts/deployment/
├── docker-entrypoint-automated.sh     # Main automation script
├── deploy-automated.sh                # Deployment orchestration
└── portainer-quickstart.sh           # Portainer setup guide

portainer-stack-dev-automated.yml      # Automated Portainer stack
```

### Configuration Files
```
.env.automated                         # Auto-generated environment
AUTOMATED_DEPLOYMENT.md               # This guide
```

## 🔧 Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AUTO_MIGRATE` | `true` | Run migrations automatically |
| `AUTO_CREATE_ADMIN` | `true` | Create admin user automatically |
| `AUTO_SETUP_BRANDING` | `true` | Setup branding and initial data |
| `SKIP_DB_INIT` | `false` | Skip database initialization |
| `MAX_RETRIES` | `30` | Database connection retry attempts |
| `RETRY_DELAY` | `5` | Seconds between retry attempts |

### Admin User Configuration
```bash
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@dev.maintenance.errorlog.app
ADMIN_PASSWORD=DevAdminPassword2024!
```

### Database Configuration
```bash
DB_NAME=maintenance_dashboard_dev
DB_USER=maintenance_user_dev
DB_PASSWORD=DevPassword2024!
DB_HOST=db-dev
DB_PORT=5432
```

## 🚀 Deployment Scenarios

### Scenario 1: Fresh Development Environment
```bash
# Clean deployment with new volumes
./scripts/deployment/deploy-automated.sh --docker-compose --clean
```

### Scenario 2: Custom Domain and Port
```bash
# Deploy with custom configuration
./scripts/deployment/deploy-automated.sh \
  --docker-compose \
  --domain myapp.local \
  --port 8080 \
  --admin-user myuser \
  --admin-email admin@myapp.local
```

### Scenario 3: Portainer with Custom Settings
```bash
# Generate configuration for Portainer
./scripts/deployment/portainer-quickstart.sh

# Then modify environment variables in Portainer:
DOMAIN=myapp.local
ADMIN_USERNAME=myuser
ADMIN_EMAIL=admin@myapp.local
```

## 🔍 Monitoring and Troubleshooting

### Health Check Endpoints
- Application: `http://localhost:4407/health/simple/`
- Database status: `http://localhost:4407/health/database/`
- Full health check: `http://localhost:4407/health/comprehensive/`

### Log Messages to Look For

**Successful Initialization:**
```
🚀 MAINTENANCE DASHBOARD - AUTOMATED DEPLOYMENT
✅ Database connection successful!
✅ Migrations completed successfully
✅ Admin user "admin" created successfully
✅ Static files collected
✅ Health check completed
🎉 DEPLOYMENT COMPLETED SUCCESSFULLY!
```

**Common Issues:**
```
❌ Database connection failed after 30 attempts
❌ Migration failed, trying conflict resolution
⚠️ Admin user "admin" already exists
⚠️ Static file collection failed
```

### Viewing Logs

**Docker Compose:**
```bash
docker-compose -f portainer-stack-dev-automated.yml logs -f web-dev
```

**Portainer:**
1. Go to Containers
2. Click on `maintenance_web_dev_auto`
3. Click "Logs" tab
4. Enable "Auto-refresh logs"

### Common Troubleshooting

**Database Connection Issues:**
- Verify PostgreSQL container is running
- Check database credentials
- Ensure network connectivity
- Wait for database health check to pass

**Migration Conflicts:**
- The system automatically resolves most conflicts
- Check logs for specific migration errors
- Use `--clean` flag for fresh start if needed

**Admin User Issues:**
- User creation is automatic and idempotent
- Check logs for creation status
- Verify credentials in environment variables

## 🔒 Security Considerations

### Development Environment
- Uses development-safe defaults
- SSL disabled for local development
- Debug mode enabled
- Weak default passwords (change after deployment)

### Production Readiness
To make this production-ready:

1. **Change default passwords:**
   ```bash
   ADMIN_PASSWORD=YourSecurePassword123!
   DB_PASSWORD=YourSecureDatabasePassword123!
   ```

2. **Enable SSL:**
   ```bash
   SECURE_SSL_REDIRECT=True
   SESSION_COOKIE_SECURE=True
   CSRF_COOKIE_SECURE=True
   ```

3. **Update domain and security headers:**
   ```bash
   DOMAIN=yourdomain.com
   CSRF_TRUSTED_ORIGINS=https://yourdomain.com
   ```

4. **Disable debug mode:**
   ```bash
   DEBUG=False
   ```

## 📊 Service Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Nginx/Traefik │────│   Django Web    │────│   PostgreSQL    │
│   (Proxy)       │    │   (Port 8000)   │    │   (Port 5432)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                               │
                       ┌───────┴───────┐
                       │               │
               ┌───────▼──────┐ ┌──────▼──────┐
               │    Redis     │ │    Celery   │
               │ (Port 6379)  │ │   Workers   │
               └──────────────┘ └─────────────┘
```

## 🎛️ Advanced Configuration

### Custom Branding
```bash
BRANDING_SITE_NAME="My Maintenance System"
BRANDING_SITE_TAGLINE="Custom Tagline"
BRANDING_PRIMARY_COLOR="#ff6b6b"
BRANDING_SECONDARY_COLOR="#4ecdc4"
```

### Performance Tuning
```bash
CELERY_WORKER_CONCURRENCY=4
CELERY_WORKER_MAX_TASKS_PER_CHILD=1000
DB_CONN_MAX_AGE=300
```

### Development Features
```bash
DEBUG=True
FORCE_FRESH_START=true  # Rebuilds everything from scratch
SKIP_COLLECTSTATIC=true # Skip static file collection
```

## 🆘 Support and Maintenance

### Regular Maintenance Tasks
```bash
# Update and restart
docker-compose -f portainer-stack-dev-automated.yml pull
docker-compose -f portainer-stack-dev-automated.yml up -d

# View resource usage
docker stats

# Backup database
docker exec maintenance_db_dev_auto pg_dump -U maintenance_user_dev maintenance_dashboard_dev > backup.sql
```

### Getting Help
1. Check the logs first (see monitoring section)
2. Verify all services are healthy
3. Test database connectivity
4. Review environment variables
5. Try a clean deployment if issues persist

---

## 🎉 Success!

Once deployed successfully, you'll have a fully functional Maintenance Dashboard with:
- ✅ Working database with all migrations applied
- ✅ Admin user ready for login
- ✅ All static files served correctly  
- ✅ Background tasks running
- ✅ Health monitoring active
- ✅ Proper security headers configured

**Default Access:**
- **URL:** http://localhost:4407/
- **Admin:** http://localhost:4407/admin/
- **Username:** admin
- **Password:** DevAdminPassword2024!

**Remember to change the admin password after first login!**