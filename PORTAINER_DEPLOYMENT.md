# Portainer Stack Deployment Guide

This guide explains how to deploy the Maintenance Dashboard using Portainer Docker Stacks.

## Prerequisites

- Portainer CE or EE installed and running
- Docker Swarm enabled (for stack deployment)
- Traefik reverse proxy configured (optional, for SSL termination)
- External network `proxy-network` created (if using Traefik)

## Quick Start

### 1. Prepare Environment Variables

1. Copy the example environment file:
   ```bash
   cp stack.env.example stack.env
   ```

2. Edit `stack.env` with your production values:
   ```bash
   # Database Configuration
   DB_NAME=maintenance_dashboard_prod
   DB_USER=maintenance_user
   DB_PASSWORD=YourSecurePassword123!
   DB_PORT=5432
   
   # Web Application
   WEB_PORT=4405
   DEBUG=False
   SECRET_KEY=your-super-secret-key-change-this-immediately
   ALLOWED_HOSTS=your-domain.com,localhost,127.0.0.1
   
   # Admin User Setup
   ADMIN_USERNAME=admin
   ADMIN_EMAIL=admin@your-domain.com
   ADMIN_PASSWORD=SecureAdminPassword123!
   
   # Domain for Traefik
   DOMAIN=your-domain.com
   ```

### 2. Deploy via Portainer UI

1. **Access Portainer**: Navigate to your Portainer instance
2. **Go to Stacks**: Click on "Stacks" in the left sidebar
3. **Add Stack**: Click "Add stack"
4. **Configure Stack**:
   - **Name**: `maintenance-dashboard`
   - **Build method**: Select "Web editor"
   - **Copy contents**: Copy the contents of `portainer-stack.yml`
   - **Environment variables**: Upload your `stack.env` file
5. **Deploy**: Click "Deploy the stack"

### 3. Deploy via Portainer API

```bash
# Create the stack using Portainer API
curl -X POST \
  -H "X-API-Key: YOUR_PORTAINER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "Name": "maintenance-dashboard",
    "SwarmID": "your-swarm-id",
    "StackFileContent": "'"$(cat portainer-stack.yml)"'",
    "Env": "'"$(cat stack.env)"'"
  }' \
  http://your-portainer-host:9000/api/stacks
```

## Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_NAME` | `maintenance_dashboard_prod` | PostgreSQL database name |
| `DB_USER` | `maintenance_user` | PostgreSQL username |
| `DB_PASSWORD` | `SecureProdPassword2024!` | PostgreSQL password |
| `DB_PORT` | `5432` | PostgreSQL port |
| `REDIS_PORT` | `6379` | Redis port |
| `WEB_PORT` | `4405` | Web application port |
| `DEBUG` | `False` | Django debug mode |
| `SECRET_KEY` | `django-production-secret-key...` | Django secret key |
| `ALLOWED_HOSTS` | `maintenance.errorlog.app,...` | Allowed hostnames |
| `ADMIN_USERNAME` | `admin` | Admin user username |
| `ADMIN_EMAIL` | `admin@maintenance.errorlog.app` | Admin user email |
| `ADMIN_PASSWORD` | `SecureAdminPassword2024!` | Admin user password |
| `DOMAIN` | `errorlog.app` | Domain for Traefik routing |

### Services

The stack includes the following services:

1. **db** (PostgreSQL 15)
   - Persistent volume for data storage
   - Health checks enabled
   - Resource limits: 1GB memory

2. **redis** (Redis 7 Alpine)
   - In-memory cache and message broker
   - Health checks enabled
   - Resource limits: 256MB memory

3. **web** (Django Application)
   - Gunicorn WSGI server
   - Static files collection
   - Database initialization
   - Traefik integration for SSL
   - Resource limits: 2GB memory

4. **celery** (Background Tasks)
   - Celery worker for async tasks
   - Health checks enabled
   - Resource limits: 1GB memory

5. **celery-beat** (Scheduled Tasks)
   - Celery beat scheduler
   - Health checks enabled
   - Resource limits: 512MB memory

### Networks

- **maintenance_network**: Internal bridge network for service communication
- **proxy-network**: External network for Traefik integration (must exist)

### Volumes

- **postgres_data**: Persistent PostgreSQL data
- **static_volume**: Static files storage
- **media_volume**: User uploaded media files

## Health Checks

All services include health checks:

- **Database**: `pg_isready` command
- **Redis**: `redis-cli ping` command
- **Web**: HTTP health endpoint `/core/health/simple/`
- **Celery**: `celery inspect ping` command
- **Celery Beat**: Process check for beat scheduler

## Monitoring

### Access Logs

View service logs in Portainer:
1. Go to "Stacks" → "maintenance-dashboard"
2. Click on any service
3. Go to "Logs" tab

### Health Status

Monitor service health:
1. Go to "Stacks" → "maintenance-dashboard"
2. View the health status indicators
3. Check "Tasks" tab for running instances

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Check `DB_HOST`, `DB_USER`, `DB_PASSWORD` in environment
   - Verify database service is healthy
   - Check network connectivity

2. **Redis Connection Failed**
   - Verify Redis service is running
   - Check `REDIS_URL` environment variable
   - Ensure Redis port is accessible

3. **Web Service Unhealthy**
   - Check Django logs for errors
   - Verify `ALLOWED_HOSTS` includes your domain
   - Ensure database migrations are applied

4. **Traefik Routing Issues**
   - Verify `proxy-network` exists
   - Check domain configuration in labels
   - Ensure Traefik is properly configured

### Debug Mode

To enable debug mode for troubleshooting:

```bash
# In stack.env
DEBUG=True
```

### Manual Database Initialization

If automatic initialization fails:

```bash
# Access the web container
docker exec -it maintenance_web_prod bash

# Run initialization manually
python manage.py init_database --admin-username admin --admin-email admin@your-domain.com --admin-password your-password
```

## Security Considerations

1. **Change Default Passwords**: Always change default passwords in production
2. **Secure Secret Key**: Generate a strong Django secret key
3. **Network Security**: Use proper firewall rules
4. **SSL/TLS**: Enable HTTPS with Traefik
5. **Regular Updates**: Keep images and dependencies updated

## Backup and Recovery

### Database Backup

```bash
# Create backup
docker exec maintenance_db_prod pg_dump -U maintenance_user maintenance_dashboard_prod > backup.sql

# Restore backup
docker exec -i maintenance_db_prod psql -U maintenance_user maintenance_dashboard_prod < backup.sql
```

### Volume Backup

```bash
# Backup volumes
docker run --rm -v maintenance-dashboard_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz -C /data .
```

## Scaling

To scale services:

1. Go to "Stacks" → "maintenance-dashboard"
2. Click on a service
3. Go to "Tasks" tab
4. Adjust the number of replicas

**Recommended scaling:**
- **Web**: 2-3 replicas for high availability
- **Celery**: 2-4 replicas based on workload
- **Celery Beat**: 1 replica (scheduler should be single instance)

## Support

For issues and questions:
- Check the logs in Portainer
- Review the Django documentation
- Check the project README for additional information 