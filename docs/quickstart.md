# Quick Start Guide

Get the Maintenance Dashboard up and running in under 10 minutes with this step-by-step guide.

## 🎯 Prerequisites

Choose your preferred installation method:

### Option A: Docker (Recommended - Easiest)
- [Docker](https://docs.docker.com/get-docker/) & [Docker Compose](https://docs.docker.com/compose/install/)
- Git

### Option B: Manual Installation
- Python 3.8 or higher
- PostgreSQL 12 or higher
- Redis server
- Git

## 🚀 Option A: Docker Installation (5 minutes)

### Step 1: Clone the Repository
```bash
git clone <your-repository-url>
cd maintenance-dashboard
```

### Step 2: Configure Environment (Optional)
Create a `.env` file for custom configuration:
```env
# Database
DB_PASSWORD=your_secure_password

# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com

# Admin User (optional - can create later)
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@yourcompany.com
ADMIN_PASSWORD=your_admin_password
```

### Step 3: Start All Services
```bash
# Start everything in the background
docker-compose up -d

# View startup logs (optional)
docker-compose logs -f
```

### Step 4: Create Admin User
```bash
# If you didn't set admin user in .env file
docker-compose exec web python manage.py createsuperuser
```

### Step 5: Access the Application
- **Main Application**: http://localhost:8000
- **Admin Interface**: http://localhost:8000/admin/
- **Container Management**: http://localhost:9000 (Portainer)

🎉 **You're done!** The application is now running with all services.

---

## 🔧 Option B: Manual Installation (10 minutes)

### Step 1: Clone and Setup Environment
```bash
# Clone repository
git clone <your-repository-url>
cd maintenance-dashboard

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Setup Database
```bash
# Start PostgreSQL (if not running)
sudo systemctl start postgresql  # Linux
brew services start postgresql   # macOS

# Create database
sudo -u postgres psql -c "CREATE DATABASE maintenance_dashboard;"
sudo -u postgres psql -c "CREATE USER maintenance_user WITH PASSWORD 'your_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE maintenance_dashboard TO maintenance_user;"
```

### Step 3: Configure Environment Variables
Create `.env` file:
```env
# Database Configuration
DB_NAME=maintenance_dashboard
DB_USER=maintenance_user
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432

# Django Configuration
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Redis Configuration
REDIS_URL=redis://localhost:6379/0
```

### Step 4: Initialize Database
```bash
# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput
```

### Step 5: Start Development Server
```bash
# Start Redis (in another terminal)
redis-server

# Start Django development server
python manage.py runserver
```

### Step 6: Access the Application
- **Main Application**: http://localhost:8000
- **Admin Interface**: http://localhost:8000/admin/

---

## 🔍 Verify Installation

### Check Services Status

#### Docker Installation
```bash
# Check all containers are running
docker-compose ps

# Should show:
# - web (Django app)
# - db (PostgreSQL)
# - redis (Redis server)
# - portainer (Container management)
```

#### Manual Installation
```bash
# Check Django
curl http://localhost:8000

# Check database connection
python manage.py check --database default

# Check Redis
redis-cli ping
```

### Test Core Functionality

1. **Login**: Visit http://localhost:8000/admin/ and login with your admin credentials
2. **Create Site**: Go to Sites and create your first site location
3. **Add Equipment**: Navigate to Equipment and add a test equipment item
4. **Schedule Maintenance**: Create a maintenance activity for your equipment

## 🎛️ Initial Configuration

### 1. Create Your First Site
1. Go to **Core > Sites** in admin interface
2. Click "Add Site"
3. Fill in site details (name, location, coordinates)
4. Save

### 2. Setup Locations
1. Go to **Core > Locations**
2. Create a location hierarchy (e.g., Building > Floor > Room)
3. Associate locations with your site

### 3. Add Equipment Categories
1. Go to **Equipment > Categories**
2. Create categories that match your equipment types
3. Add equipment items to these categories

### 4. Configure User Roles
1. Go to **Core > Roles**
2. Create roles like "Technician", "Manager", "Viewer"
3. Assign permissions to each role
4. Assign roles to users

## 🐳 Portainer Setup (Docker Only)

### Access Portainer
1. Go to http://localhost:9000
2. Create admin user (first time only)
3. Select "Docker" environment
4. Click "Connect"

### Key Features
- **Containers**: View and manage all containers
- **Stacks**: Manage your entire application stack
- **Logs**: Real-time log viewing
- **Stats**: Resource usage monitoring

## 🔧 Common Post-Installation Tasks

### Import Existing Data
```bash
# For Docker
docker-compose exec web python manage.py shell

# For Manual
python manage.py shell
```

### Setup Backup Strategy
```bash
# Database backup (Docker)
docker exec maintenance_db pg_dump -U postgres maintenance_dashboard > backup.sql

# Database backup (Manual)
pg_dump -U maintenance_user maintenance_dashboard > backup.sql
```

### Configure Email (Optional)
Add to your `.env` file:
```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

## 🆘 Troubleshooting Quick Fixes

### Docker Issues
```bash
# If containers won't start
docker-compose down
docker-compose up --build

# If database issues
docker-compose exec web python manage.py migrate

# View logs
docker-compose logs web
docker-compose logs db
```

### Manual Installation Issues
```bash
# Database connection error
python manage.py check --database default

# Static files not loading
python manage.py collectstatic --noinput

# Permission errors
sudo chown -R $USER:$USER .
```

### Port Already in Use
```bash
# Check what's using port 8000
lsof -i :8000

# Kill process
sudo kill -9 <PID>

# Or change port in docker-compose.yml or Django settings
```

## 📚 What's Next?

1. **Read Full Documentation**: [docs/README.md](README.md)
2. **Configure Features**: [features/overview.md](features/overview.md)
3. **Setup Calendar Integration**: [features/calendar-integration.md](features/calendar-integration.md)
4. **Import/Export Data**: [features/csv-import-export.md](features/csv-import-export.md)
5. **Production Deployment**: [deployment/production.md](deployment/production.md)

## 🤝 Need Help?

- **Documentation**: [docs/README.md](README.md)
- **Common Issues**: [troubleshooting/common-issues.md](troubleshooting/common-issues.md)
- **GitHub Issues**: [Create an issue](link-to-issues)
- **Community**: [GitHub Discussions](link-to-discussions)

---

**Congratulations! 🎉** Your Maintenance Dashboard is now ready to use. Start by adding your sites, equipment, and scheduling your first maintenance activities.