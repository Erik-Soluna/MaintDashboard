# Deployment Guide

This guide covers all deployment options for the Maintenance Dashboard system.

## 🐳 Docker Deployment (Recommended)

### Quick Start
```bash
# Clone and start
git clone <repository-url>
cd MaintDashboard
docker compose up -d

# Access the application
# URL: http://localhost:8000/
# Username: admin
# Password: temppass123
```

### Docker Compose Configuration
The system uses Docker Compose with the following services:
- **Web**: Django application server
- **DB**: PostgreSQL database
- **Redis**: Cache and message broker
- **Celery**: Background task processing
- **Celery Beat**: Scheduled task management

### Environment Configuration
Copy the appropriate environment file from the deployment directory:
```bash
# Development
cp deployment/env.development .env

# Production
cp deployment/env.production .env

# GitHub Actions
cp deployment/env.github.example .env.github
```

## 🌐 Portainer Deployment

### Stack Files
Portainer stack files are located in the root directory for easy access:
- `portainer-stack.yml` - Production configuration
- `portainer-stack-dev.yml` - Development configuration

### Production Stack
Use the production Portainer stack configuration:
```yaml
# portainer-stack.yml (root directory)
```

### Development Stack
Use the development configuration for testing:
```yaml
# portainer-stack-dev.yml (root directory)
```

### Portainer Template
Import the Portainer template for easy deployment:
```json
# deployment/portainer-template.json
```

## 🔒 Security Configuration

### Environment Variables
Configure these security-related environment variables:

```env
# Django Security
SECRET_KEY=your-secure-secret-key
DEBUG=False
ALLOWED_HOSTS=your-domain.com,localhost

# Database Security
DB_PASSWORD=secure-database-password
POSTGRES_PASSWORD=secure-postgres-password

# Admin User
ADMIN_PASSWORD=secure-admin-password
```

### HTTPS Configuration
For production deployments, configure HTTPS:

1. **Nginx Proxy Manager** (Recommended)
   - Use the Nginx Proxy Manager setup guide
   - Configure SSL certificates
   - Set up reverse proxy

2. **Load Balancer Configuration**
   - Configure health checks
   - Set up SSL termination
   - Configure rate limiting

## 📊 Monitoring and Health Checks

### Health Check Endpoints
- **Application Health**: `http://localhost:8000/health/`
- **Database Health**: Built into Docker health checks
- **Cache Health**: Redis connectivity monitoring

### Logging
- **Application Logs**: `docker compose logs web`
- **Database Logs**: `docker compose logs db`
- **Celery Logs**: `docker compose logs celery`

## 🔧 Troubleshooting

### Common Issues

#### Database Connection Issues
```bash
# Check database status
docker compose exec db psql -U postgres -c "SELECT version();"

# Reset database
docker compose down -v
docker compose up -d
```

#### Cache Issues
```bash
# Check Redis connectivity
docker compose exec web python -c "import redis; r=redis.Redis(); print(r.ping())"

# Clear cache
docker compose exec web python manage.py shell -c "from django.core.cache import cache; cache.clear()"
```

#### Static Files Issues
```bash
# Collect static files
docker compose exec web python manage.py collectstatic --noinput

# Check static files directory
docker compose exec web ls -la /app/staticfiles/
```

### Performance Optimization

#### Database Optimization
- Enable connection pooling
- Configure appropriate indexes
- Monitor query performance

#### Cache Optimization
- Configure Redis persistence
- Set appropriate cache timeouts
- Monitor cache hit rates

#### Application Optimization
- Configure worker processes
- Enable compression
- Optimize static file serving

## 🚀 Production Checklist

- [ ] Environment variables configured
- [ ] HTTPS/SSL certificates installed
- [ ] Database backups configured
- [ ] Monitoring and alerting set up
- [ ] Log aggregation configured
- [ ] Performance monitoring enabled
- [ ] Security scanning completed
- [ ] Load testing performed

## 📚 Additional Resources

- **Docker Setup**: `docs/DOCKER_SETUP.md`
- **Security Configuration**: `docs/SECURITY_CONFIGURATION.md`
- **Nginx Proxy Manager**: `docs/NGINX_PROXY_MANAGER_SETUP.md`
- **Network Configuration**: `docs/PROXY_NETWORK_GUIDE.md`

---

**Last Updated**: July 2025  
**Version**: 2.0 (Unified System) 