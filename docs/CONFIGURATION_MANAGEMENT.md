# Configuration Management Guide

## Overview

The Maintenance Dashboard uses **python-decouple** for robust configuration management. This system allows you to:

- ✅ **Environment-specific** configurations
- ✅ **Secure** handling of sensitive data
- ✅ **Docker-native** configuration
- ✅ **No code changes** for new configs
- ✅ **Type casting** and validation
- ✅ **Default values** for all settings

## Quick Start

### 1. Generate Environment File

```bash
# Generate .env file from template
python scripts/config_manager.py generate

# Or force overwrite existing file
python scripts/config_manager.py generate --force
```

### 2. Configure Your Environment

Edit the generated `.env` file with your actual values:

```bash
# Core settings
DEBUG=False
SECRET_KEY=your-super-secret-key-here
ALLOWED_HOSTS=maintenance.errorlog.app,localhost

# Database
DB_NAME=maintenance_dashboard
DB_USER=maintenance_user
DB_PASSWORD=your-secure-password
DB_HOST=db
DB_PORT=5432

# Redis
REDIS_URL=redis://redis:6379/0
```

### 3. Validate Configuration

```bash
# Check for configuration issues
python scripts/config_manager.py validate

# Show current configuration
python scripts/config_manager.py show

# Check Docker compatibility
python scripts/config_manager.py check-docker
```

## Configuration Categories

### 🔧 Core Django Settings

```bash
# Debug mode (True for development, False for production)
DEBUG=False

# Secret key for Django (CHANGE THIS!)
SECRET_KEY=your-super-secret-key-here

# Allowed hosts (comma-separated)
ALLOWED_HOSTS=maintenance.errorlog.app,localhost,127.0.0.1
```

### 🗄️ Database Configuration

```bash
# Database type (True for SQLite, False for PostgreSQL)
USE_SQLITE=False

# PostgreSQL settings
DB_NAME=maintenance_dashboard
DB_USER=maintenance_user
DB_PASSWORD=your-secure-password
DB_HOST=db
DB_PORT=5432
POSTGRES_PASSWORD=your-secure-password
```

### 🔴 Redis Configuration

```bash
# Redis URL (preferred method)
REDIS_URL=redis://redis:6379/0

# Or individual components
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=

# Redis usage
USE_REDIS=True
```

### 🐌 Celery Configuration

```bash
# Celery broker and result backend
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Worker settings
CELERY_WORKER_CONCURRENCY=2
CELERY_WORKER_MAX_TASKS_PER_CHILD=1000
CELERY_WORKER_PREFETCH_MULTIPLIER=1
```

### 📧 Email Configuration

```bash
# Email backend
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# SMTP settings
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@maintenance-dashboard.com
```

### 🔒 Security Settings

```bash
# SSL/HTTPS settings
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_BROWSER_XSS_FILTER=True
SECURE_CONTENT_TYPE_NOSNIFF=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True

# CSRF settings
CSRF_TRUSTED_ORIGINS=https://maintenance.errorlog.app,https://www.maintenance.errorlog.app

# Proxy settings
USE_X_FORWARDED_HOST=True
USE_X_FORWARDED_PORT=True
SECURE_PROXY_SSL_HEADER=HTTP_X_FORWARDED_PROTO,https
```

### 👤 Admin User Creation

```bash
# Admin user settings
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@maintenance.errorlog.app
ADMIN_PASSWORD=SecureAdminPassword2024!
```

## Environment-Specific Configurations

### Development Environment

```bash
# Development settings
DEBUG=True
SECURE_SSL_REDIRECT=False
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False
SECURE_HSTS_SECONDS=0
SECURE_HSTS_INCLUDE_SUBDOMAINS=False
SECURE_HSTS_PRELOAD=False
ALLOWED_HOSTS=localhost,127.0.0.1,dev.maintenance.errorlog.app
CSRF_TRUSTED_ORIGINS=http://dev.maintenance.errorlog.app,https://dev.maintenance.errorlog.app
```

### Production Environment

```bash
# Production settings
DEBUG=False
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True
ALLOWED_HOSTS=maintenance.errorlog.app,www.maintenance.errorlog.app
CSRF_TRUSTED_ORIGINS=https://maintenance.errorlog.app,https://www.maintenance.errorlog.app
```

## Docker Integration

### Environment Variables in Docker

The configuration system works seamlessly with Docker environment variables:

```yaml
# portainer-stack.yml
environment:
  - DEBUG=False
  - SECRET_KEY=your-production-secret-key
  - DB_NAME=maintenance_dashboard_prod
  - DB_USER=maintenance_user
  - DB_PASSWORD=SecureProdPassword2024!
  - DB_HOST=db
  - DB_PORT=5432
  - REDIS_URL=redis://redis:6379/0
```

### Export Docker Environment

```bash
# Export current environment to Docker format
python scripts/config_manager.py export --output docker.env
```

## Configuration Manager Script

The `scripts/config_manager.py` script provides several useful commands:

### Validate Configuration

```bash
python scripts/config_manager.py validate
```

Checks for:
- Missing critical environment variables
- Security issues (default secret keys)
- Configuration conflicts
- Required files

### Show Current Configuration

```bash
# Show configuration (hides secrets)
python scripts/config_manager.py show

# Show configuration including secrets
python scripts/config_manager.py show --show-secrets
```

### Generate Environment File

```bash
# Generate .env file from template
python scripts/config_manager.py generate

# Force overwrite existing file
python scripts/config_manager.py generate --force
```

### Check Docker Compatibility

```bash
python scripts/config_manager.py check-docker
```

Verifies:
- Docker-specific hostnames (db, redis)
- Required Docker environment variables
- Configuration compatibility with Docker deployment

### Export Environment

```bash
# Export to default docker.env file
python scripts/config_manager.py export

# Export to custom file
python scripts/config_manager.py export --output production.env
```

## Best Practices

### 🔐 Security

1. **Never commit `.env` files** to version control
2. **Use strong, unique secret keys** for each environment
3. **Rotate passwords** regularly
4. **Use environment-specific** configurations

### 🏗️ Organization

1. **Group related settings** together in `.env` file
2. **Use descriptive variable names**
3. **Provide meaningful default values**
4. **Document custom configurations**

### 🐳 Docker

1. **Use Docker environment variables** for sensitive data
2. **Keep Docker-specific hostnames** (db, redis)
3. **Validate Docker compatibility** before deployment
4. **Use separate configurations** for dev/staging/prod

### 🔄 Environment Management

1. **Use different `.env` files** for different environments
2. **Validate configuration** before deployment
3. **Test configuration changes** in development first
4. **Backup configuration** before major changes

## Troubleshooting

### Common Issues

#### Missing Environment Variables

```bash
# Check what's missing
python scripts/config_manager.py validate

# Generate template
python scripts/config_manager.py generate
```

#### Docker Connection Issues

```bash
# Check Docker compatibility
python scripts/config_manager.py check-docker

# Verify hostnames
DB_HOST=db  # Not localhost
REDIS_HOST=redis  # Not localhost
```

#### Configuration Conflicts

```bash
# Show current configuration
python scripts/config_manager.py show

# Check for conflicts
python scripts/config_manager.py validate
```

### Debug Mode

For debugging configuration issues:

```bash
# Show all configuration including secrets
python scripts/config_manager.py show --show-secrets

# Validate with detailed output
python scripts/config_manager.py validate
```

## Migration from Hardcoded Values

If you have hardcoded values in your code, replace them with `config()` calls:

### Before (Hardcoded)

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'maintenance_dashboard',
        'USER': 'maintenance_user',
        'PASSWORD': 'hardcoded_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

### After (Using python-decouple)

```python
from decouple import config

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='maintenance_dashboard'),
        'USER': config('DB_USER', default='maintenance_user'),
        'PASSWORD': config('DB_PASSWORD', default=''),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}
```

## Advanced Features

### Type Casting

```python
from decouple import config, Csv

# Boolean casting
DEBUG = config('DEBUG', default=False, cast=bool)

# Integer casting
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)

# Float casting
MONITORING_THRESHOLD = config('MONITORING_THRESHOLD', default=5.0, cast=float)

# List casting (comma-separated)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost', cast=Csv())
```

### Conditional Configuration

```python
# Database selection
USE_SQLITE = config('USE_SQLITE', default=False, cast=bool)

if USE_SQLITE:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DB_NAME'),
            'USER': config('DB_USER'),
            'PASSWORD': config('DB_PASSWORD'),
            'HOST': config('DB_HOST'),
            'PORT': config('DB_PORT'),
        }
    }
```

## Conclusion

The python-decouple configuration system provides a robust, secure, and flexible way to manage your Maintenance Dashboard configuration. By following these guidelines, you can:

- ✅ **Easily switch** between environments
- ✅ **Keep secrets secure** out of code
- ✅ **Validate configurations** before deployment
- ✅ **Manage Docker deployments** effectively
- ✅ **Scale configurations** as your project grows

For more information, see the [python-decouple documentation](https://github.com/henriquebastos/python-decouple).
