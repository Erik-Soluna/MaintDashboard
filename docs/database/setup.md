# Database Setup Guide

## Overview

The Maintenance Dashboard uses PostgreSQL as its primary database with Redis for caching and background tasks. This guide covers both manual and automated database setup options.

## 🐳 Docker Setup (Recommended)

### Quick Start
The easiest way to set up the database is using Docker Compose, which automatically handles PostgreSQL and Redis setup:

```bash
# Start all services including database
docker-compose up -d

# Check database status
docker-compose ps db
```

### Database Configuration in Docker
The Docker setup automatically:
- Creates PostgreSQL database
- Sets up Redis for caching
- Runs database migrations
- Creates necessary tables and relationships

### Environment Variables for Docker
Configure your `.env` file:
```env
# Database Configuration
DB_NAME=maintenance_dashboard
DB_USER=postgres
DB_PASSWORD=your_secure_password
DB_HOST=db
DB_PORT=5432

# Redis Configuration
REDIS_URL=redis://redis:6379/0
```

## 🔧 Manual Setup

### Prerequisites
- PostgreSQL 12 or higher
- Redis server
- Python 3.8+

### PostgreSQL Installation

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

#### CentOS/RHEL
```bash
sudo yum install postgresql-server postgresql-contrib
sudo postgresql-setup initdb
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

#### macOS
```bash
brew install postgresql
brew services start postgresql
```

#### Windows
Download and install from [PostgreSQL official website](https://www.postgresql.org/download/windows/)

### Database Creation

1. **Access PostgreSQL as superuser:**
```bash
sudo -u postgres psql
```

2. **Create database and user:**
```sql
CREATE DATABASE maintenance_dashboard;
CREATE USER maintenance_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE maintenance_dashboard TO maintenance_user;
ALTER USER maintenance_user CREATEDB;
\q
```

3. **Test connection:**
```bash
psql -h localhost -U maintenance_user -d maintenance_dashboard
```

### Redis Installation

#### Ubuntu/Debian
```bash
sudo apt install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

#### CentOS/RHEL
```bash
sudo yum install redis
sudo systemctl start redis
sudo systemctl enable redis
```

#### macOS
```bash
brew install redis
brew services start redis
```

## ⚙️ Django Configuration

### Settings Configuration
Update your `settings.py` or use environment variables:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'maintenance_dashboard'),
        'USER': os.getenv('DB_USER', 'maintenance_user'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'your_password'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

# Redis Configuration
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}
```

### Database Migrations

1. **Create migration files:**
```bash
python manage.py makemigrations
```

2. **Apply migrations:**
```bash
python manage.py migrate
```

3. **Create superuser:**
```bash
python manage.py createsuperuser
```

4. **Collect static files:**
```bash
python manage.py collectstatic --noinput
```

## 🔄 Database Initialization

### Automated Initialization
For production environments, use the automated initialization system:

```bash
# Make initialization script executable
chmod +x auto_init_database.py

# Run automated initialization
python3 auto_init_database.py
```

This script provides:
- Automatic database creation
- Connection retry logic
- Health monitoring
- Error recovery

For detailed information, see [Automated Database Initialization](automated-init.md).

### Manual Initialization
For development or custom setups:

```bash
# Check database connection
python manage.py check --database default

# Create database if it doesn't exist
python manage.py shell -c "
from django.db import connection
cursor = connection.cursor()
"

# Run migrations
python manage.py migrate

# Load initial data (if available)
python manage.py loaddata initial_data.json
```

## 🗄️ Database Schema

### Core Tables
The application creates several core tables:

- **auth_user**: Django user authentication
- **core_site**: Site locations and information
- **core_location**: Hierarchical location structure
- **core_userprofile**: Extended user profiles with roles
- **equipment_equipment**: Equipment inventory
- **equipment_category**: Equipment categorization
- **maintenance_activity**: Maintenance activities and scheduling
- **maintenance_schedule**: Recurring maintenance schedules
- **events_event**: Event logging and tracking

### Relationships
- Sites contain multiple Locations
- Locations can have child Locations (hierarchical)
- Equipment belongs to Locations
- Maintenance Activities are assigned to Equipment
- Events track changes to all entities

## 🛠️ Database Management

### Backup and Restore

#### Backup
```bash
# Docker environment
docker exec maintenance_db pg_dump -U postgres maintenance_dashboard > backup.sql

# Manual environment
pg_dump -U maintenance_user -h localhost maintenance_dashboard > backup.sql
```

#### Restore
```bash
# Docker environment
docker exec -i maintenance_db psql -U postgres maintenance_dashboard < backup.sql

# Manual environment
psql -U maintenance_user -h localhost maintenance_dashboard < backup.sql
```

### Performance Optimization

#### Database Indexing
The application includes optimized indexes for:
- Equipment location queries
- Maintenance activity filtering
- User role lookups
- Event date ranges

#### Connection Pooling
For production, consider using connection pooling:

```python
DATABASES = {
    'default': {
        # ... other settings
        'CONN_MAX_AGE': 600,  # Connection reuse - Django setting
        'OPTIONS': {
            # PostgreSQL-specific connection options
            # Note: MAX_CONNS and MIN_CONNS are not valid PostgreSQL options
            # Use a connection pooler like PgBouncer for advanced pooling
        }
    }
}
```

## 🔍 Troubleshooting

### Common Issues

#### Connection Refused
```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Check port availability
netstat -an | grep 5432

# Test connection
telnet localhost 5432
```

#### Authentication Failed
```bash
# Check pg_hba.conf configuration
sudo nano /etc/postgresql/12/main/pg_hba.conf

# Ensure line exists:
# local   all             all                                     md5
```

#### Database Does Not Exist
```bash
# Create database manually
sudo -u postgres createdb maintenance_dashboard

# Or use automated script
python3 auto_init_database.py
```

#### Permission Denied
```sql
-- Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE maintenance_dashboard TO maintenance_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO maintenance_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO maintenance_user;
```

### Health Checks

#### Database Health
```bash
# Check database connection
python manage.py shell -c "
from django.db import connection
try:
    connection.ensure_connection()
    print('Database: Connected')
except Exception as e:
    print(f'Database: Error - {e}')
"
```

#### Redis Health
```bash
# Test Redis connection
redis-cli ping

# Check Redis info
redis-cli info
```

## 🔒 Security Considerations

### Database Security
- Use strong passwords for database users
- Limit database user permissions to necessary operations only
- Enable SSL connections for production
- Regular security updates for PostgreSQL

### Network Security
- Configure firewall rules to restrict database access
- Use connection encryption (SSL/TLS)
- Implement connection rate limiting
- Monitor database access logs

### Backup Security
- Encrypt database backups
- Store backups in secure locations
- Regular backup testing and validation
- Implement backup retention policies

---

For automated database setup and monitoring, see [Automated Database Initialization Guide](automated-init.md).
For database troubleshooting, see [Database Troubleshooting Guide](troubleshooting.md).