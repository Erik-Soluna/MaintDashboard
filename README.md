# Maintenance Dashboard

A Django-based web maintenance dashboard for managing equipment, maintenance activities, and scheduling. This application was converted from a legacy web2py system to fix association issues and improve reliability.

## Features

### Fixed Issues from Original web2py Version
- **Proper Database Associations**: Fixed broken relationships between equipment, maintenance, and calendar events
- **PostgreSQL Support**: Moved from SQLite to PostgreSQL for better performance and reliability
- **Improved Authentication**: Uses Django's robust authentication system instead of custom groupID system
- **Better Data Validation**: Proper model validation and constraints
- **Hierarchical Locations**: Fixed location hierarchy with proper validation
- **Maintenance Scheduling**: Proper scheduling system with activity types and automation
- **Calendar Integration**: Fixed calendar events with proper equipment associations

### Core Functionality
- **Equipment Management**: Track equipment with categories, locations, and documentation
- **Maintenance Activities**: Schedule and track maintenance with proper workflows
- **Calendar Events**: Integrated calendar with maintenance activities and custom events
- **User Management**: Role-based access control with user profiles
- **Reporting**: Maintenance reports and analytics
- **API Endpoints**: RESTful APIs for integration

## Quick Start with Docker

### Prerequisites
- Docker
- Docker Compose
- Git

### 1. Clone the Repository
```bash
git clone <repository-url>
cd maintenance-dashboard
```

### 2. Configure Environment
Copy the environment file and customize as needed:
```bash
cp .env.example .env
```

Edit `.env` to set your preferences:
```env
# Database credentials
DB_PASSWORD=your-secure-password

# Admin user (change these!)
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@yourdomain.com
ADMIN_PASSWORD=change-me-please

# Django secret key (generate a new one for production)
SECRET_KEY=your-secret-key-here
```

### 3. Launch the Application
```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f web
```

### 4. Access the Application
- **Web Application**: http://localhost
- **Django Admin**: http://localhost/admin/
- **API Documentation**: http://localhost/api/docs/ (if enabled)

Default login credentials:
- Username: `admin` (or what you set in .env)
- Password: `admin123` (or what you set in .env)

**⚠️ Change the default password immediately after first login!**

## Architecture

### Services
The Docker setup includes the following services:

- **web**: Django application server (Gunicorn)
- **db**: PostgreSQL 15 database
- **redis**: Redis for caching and Celery
- **celery**: Background task worker
- **celery-beat**: Scheduled task scheduler
- **nginx**: Reverse proxy and static file server

### Database Models
The application includes properly associated models:

- **Equipment**: Main equipment with categories and locations
- **Maintenance Activities**: Scheduled and tracked maintenance
- **Calendar Events**: Integrated calendar system
- **Locations**: Hierarchical site and equipment locations
- **Users**: Extended user profiles with roles

## Development

### Local Development Setup
If you prefer to run without Docker:

1. **Create virtual environment**:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Setup PostgreSQL** (install locally or use Docker):
```bash
# Using Docker for just the database
docker run --name postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d postgres:15
```

4. **Configure settings**:
```bash
export DEBUG=True
export DB_HOST=localhost
export DB_PASSWORD=postgres
```

5. **Run migrations and create superuser**:
```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py load_initial_data
```

6. **Run development server**:
```bash
python manage.py runserver
```

### Useful Commands

```bash
# View all container logs
docker-compose logs

# Execute commands in web container
docker-compose exec web python manage.py shell

# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Backup database
docker-compose exec db pg_dump -U postgres maintenance_dashboard > backup.sql

# Restore database
docker-compose exec -T db psql -U postgres maintenance_dashboard < backup.sql
```

## Production Deployment

### Security Considerations
1. **Change default passwords** immediately
2. **Set strong SECRET_KEY** (use Django's key generator)
3. **Disable DEBUG** in production
4. **Configure proper ALLOWED_HOSTS**
5. **Set up SSL certificates** for HTTPS
6. **Regular backups** of database and media files

### Environment Variables for Production
```env
DEBUG=False
SECRET_KEY=your-very-long-random-secret-key
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DB_PASSWORD=very-secure-password
```

### SSL Setup
1. Place SSL certificates in `./ssl/` directory
2. Update `nginx.conf` to enable HTTPS
3. Restart nginx service

### Monitoring
The setup includes health checks for all services. Monitor using:
```bash
docker-compose ps
```

## API Documentation

The application provides RESTful APIs for:
- Equipment management
- Maintenance activities
- Calendar events
- User management

API endpoints follow Django REST framework conventions.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## Migration from web2py

This application fixes several issues from the original web2py version:

### Database Issues Fixed
- ✅ Proper foreign key relationships
- ✅ Database constraints and validation
- ✅ Consistent table structure
- ✅ PostgreSQL optimization

### Association Issues Fixed
- ✅ Equipment → Maintenance Activities (was broken)
- ✅ Calendar Events → Equipment (was loosely connected)
- ✅ Location hierarchy (was poorly implemented)
- ✅ User roles and permissions (was custom groupID system)

### Performance Improvements
- ✅ Database indexes and optimization
- ✅ Proper query optimization
- ✅ Caching with Redis
- ✅ Static file handling with nginx

## Support

For issues and questions:
1. Check the logs: `docker-compose logs`
2. Review this README
3. Check Django admin for data issues
4. Create an issue in the repository

## License

[Your License Here]