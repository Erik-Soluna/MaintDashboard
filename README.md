# Maintenance Dashboard

A Django-based web application for managing equipment maintenance, events, and related operations.

## Features

- **Equipment Management**: Track and manage various equipment items
- **Maintenance Scheduling**: Plan and track maintenance activities
- **Event Logging**: Record and monitor maintenance events
- **User Authentication**: Secure login and user management
- **Responsive UI**: Bootstrap-based interface with crispy forms
- **Filtering & Tables**: Advanced filtering and tabular data views
- **Media Management**: File and image upload capabilities

## Prerequisites

- Python 3.8 or higher
- PostgreSQL 12 or higher
- Redis (for background tasks with Celery)
- Git

## Installation Options

Choose one of the following installation methods:

> **💡 Recommendation**: Use Docker installation for the easiest setup experience with all dependencies automatically configured.

## Docker Installation (Recommended)

Docker provides an easy way to run the entire application stack without manual setup of PostgreSQL, Redis, or Python dependencies.

### Prerequisites

- Docker and Docker Compose installed on your system
- Git

### Quick Start with Docker

1. **Clone the Repository**
```bash
git clone <repository-url>
cd maintenance-dashboard
```

2. **Build and Start Services**
```bash
docker-compose up --build
```

This command will:
- Build the Django application image
- Start PostgreSQL database
- Start Redis server
- Run database migrations
- Start the Django application
- Start Celery worker and scheduler

3. **Access the Application**

The application will be available at `http://localhost:8000`

4. **Create a Superuser**

In a new terminal, run:
```bash
docker-compose exec web python manage.py createsuperuser
```

### Docker Commands

**Start services in background:**
```bash
docker-compose up -d
```

**View logs:**
```bash
docker-compose logs -f
```

**Stop services:**
```bash
docker-compose down
```

**Stop services and remove volumes (WARNING: This will delete all data):**
```bash
docker-compose down -v
```

**Rebuild services:**
```bash
docker-compose up --build
```

**Run Django management commands:**
```bash
docker-compose exec web python manage.py <command>
```

**Access Django shell:**
```bash
docker-compose exec web python manage.py shell
```

**Access database shell:**
```bash
docker-compose exec db psql -U postgres -d maintenance_dashboard
```

### Production Docker Setup

For production deployment, create a `docker-compose.prod.yml` file:

```yaml
version: '3.8'

services:
  web:
    build: .
    environment:
      - DEBUG=False
      - SECRET_KEY=your-production-secret-key
      - ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
      - DB_PASSWORD=your-secure-password
    restart: unless-stopped

  db:
    environment:
      POSTGRES_PASSWORD: your-secure-password
    restart: unless-stopped

  redis:
    restart: unless-stopped
```

Run production setup:
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Manual Installation (Alternative)

If you prefer to install without Docker, follow these steps:

### 1. Clone the Repository

```bash
git clone <repository-url>
cd maintenance-dashboard
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables

Create a `.env` file in the project root with the following variables:

```bash
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database Configuration
DB_NAME=maintenance_dashboard
DB_USER=postgres
DB_PASSWORD=your-database-password
DB_HOST=localhost
DB_PORT=5432

# Redis Configuration (for Celery)
REDIS_URL=redis://localhost:6379/0
```

### 5. Set Up PostgreSQL Database

Create a PostgreSQL database:

```sql
CREATE DATABASE maintenance_dashboard;
CREATE USER maintenance_user WITH PASSWORD 'your-password';
GRANT ALL PRIVILEGES ON DATABASE maintenance_dashboard TO maintenance_user;
```

### 6. Run Database Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 7. Create a Superuser

```bash
python manage.py createsuperuser
```

### 8. Collect Static Files

```bash
python manage.py collectstatic
```

## Usage

### Development Server

Start the Django development server:

```bash
python manage.py runserver
```

The application will be available at `http://localhost:8000`

### Background Tasks (Optional)

If you need to run background tasks with Celery:

1. Start Redis server:
```bash
redis-server
```

2. Start Celery worker:
```bash
celery -A maintenance_dashboard worker --loglevel=info
```

### Admin Interface

Access the Django admin interface at `http://localhost:8000/admin/` using the superuser credentials you created.

### Main Features Access

- **Dashboard**: `http://localhost:8000/` - Main dashboard view
- **Equipment**: Manage equipment items and their details
- **Maintenance**: Schedule and track maintenance activities
- **Events**: Log and monitor maintenance events
- **Reports**: View maintenance reports and analytics

## Project Structure

```
maintenance_dashboard/
├── maintenance_dashboard/    # Main Django project settings
├── equipment/               # Equipment management app
├── maintenance/            # Maintenance scheduling app
├── events/                 # Event logging app
├── core/                   # Core functionality app
├── controllers/            # Controller logic
├── models/                 # Data models
├── views/                  # View logic
├── static/                 # Static files (CSS, JS, images)
├── templates/              # HTML templates
├── manage.py              # Django management script
└── requirements.txt       # Python dependencies
```

## Production Deployment

### Environment Setup

1. Set `DEBUG=False` in your `.env` file
2. Configure proper `ALLOWED_HOSTS`
3. Set up a production database
4. Configure a web server (nginx) and WSGI server (gunicorn)

### Using Gunicorn

```bash
gunicorn maintenance_dashboard.wsgi:application --bind 0.0.0.0:8000
```

### Static Files

The project is configured to use WhiteNoise for serving static files in production.

## Configuration

### Database

The project uses PostgreSQL by default. You can modify database settings in the `.env` file or directly in `maintenance_dashboard/settings.py`.

### Authentication

- Login URL: `/auth/login/`
- Logout redirect: `/auth/login/`
- Home redirect after login: `/`

### Media Files

Uploaded files are stored in the `media/` directory. Make sure this directory has proper write permissions.

## Development

### Running Tests

```bash
python manage.py test
```

### Django Shell

Access the Django shell for debugging:

```bash
python manage.py shell
```

### Database Shell

Access the database shell:

```bash
python manage.py dbshell
```

## Troubleshooting

### Docker Issues

1. **Port already in use**: If port 8000, 5432, or 6379 is already in use:
   ```bash
   docker-compose down
   # Kill processes using the ports or change ports in docker-compose.yml
   ```

2. **Permission denied errors**: 
   ```bash
   sudo chown -R $USER:$USER .
   docker-compose down -v
   docker-compose up --build
   ```

3. **Database connection issues**:
   ```bash
   docker-compose down -v  # This will remove all data
   docker-compose up --build
   ```

4. **View Docker logs**:
   ```bash
   docker-compose logs web
   docker-compose logs db
   docker-compose logs redis
   ```

5. **Reset everything**:
   ```bash
   docker-compose down -v
   docker system prune -a --volumes
   docker-compose up --build
   ```

### Common Issues (Manual Installation)

1. **Database Connection Error**: Ensure PostgreSQL is running and credentials are correct
2. **Static Files Not Loading**: Run `python manage.py collectstatic`
3. **Migration Issues**: Try `python manage.py makemigrations` followed by `python manage.py migrate`
4. **Permission Errors**: Ensure proper file permissions on media and static directories
5. **Virtual Environment Issues**: Make sure virtual environment is activated

### Logs

- **Docker**: Use `docker-compose logs -f` to view real-time logs
- **Manual Installation**: Application logs are stored in `debug.log` in the project root directory

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## Support

For support and questions, please refer to the project documentation or create an issue in the repository.