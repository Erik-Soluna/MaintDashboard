# Database Initialization and Admin User Setup Guide

## Overview

This guide explains the automatic database initialization system that has been implemented for your Django Maintenance Dashboard project. The system handles database migrations, admin user creation, and forces password changes on first login.

## Features Implemented

### 1. Automatic Database Initialization
- **Django Management Command**: `init_database`
- **Shell Script**: `init_database.sh`
- **Forced Password Change Middleware**: Ensures admin users change password on first login
- **Initial Data Creation**: Automatically creates sample categories and locations

### 2. Database Initialization Management Command

**Location**: `core/management/commands/init_database.py`

**Usage**:
```bash
# Basic usage
python manage.py init_database

# With custom admin credentials
python manage.py init_database --admin-username myuser --admin-email admin@company.com --admin-password mypass123

# Skip certain steps
python manage.py init_database --skip-migrations --skip-sample-data
```

**Features**:
- Runs database migrations automatically
- Creates admin superuser with configurable credentials
- Sets up initial equipment categories and locations
- Forces password change on first login
- Provides detailed progress feedback

### 3. Shell Script for Easy Execution

**Location**: `init_database.sh`

**Usage**:
```bash
# Make executable (if not already)
chmod +x init_database.sh

# Basic usage
./init_database.sh

# With custom parameters
./init_database.sh --username admin --email admin@company.com --password mypass123

# Using environment variables
ADMIN_USERNAME=admin ADMIN_PASSWORD=secret123 ./init_database.sh
```

**Features**:
- Waits for database to be ready
- Colored output for better visibility
- Environment variable support
- Database connection testing
- Comprehensive error handling

### 4. Forced Password Change System

**Components**:
- **Middleware**: `core/middleware.py` - `ForcePasswordChangeMiddleware`
- **Custom Admin**: Enhanced admin interface with password change handling
- **Authentication Flow**: Redirects first-time users to password change page

**How it works**:
1. When admin user is created, `last_login` is set to `None`
2. Middleware checks on each request if user has never logged in
3. If first login detected, redirects to password change page
4. After successful password change, `last_login` is updated
5. User can then access all features normally

### 5. Enhanced Dashboard

**Location**: `templates/core/dashboard.html`

**Features**:
- SOLUNA branding (as requested)
- Dark blue theme matching your screenshot
- Dynamic location-based columns
- Site selector in header
- Urgent and upcoming items sections
- Location-specific data display:
  - Scheduled Downtimes
  - Equipment in Repair

**Navigation**:
- Overview (active)
- Map (placeholder)
- Maintenance (links to existing functionality)
- Settings (placeholder)

## Setup Instructions

### 1. First Time Setup

```bash
# 1. Ensure PostgreSQL is running
sudo service postgresql start

# 2. Create database
sudo -u postgres createdb maintenance_dashboard

# 3. Set postgres user password
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres';"

# 4. Install Python dependencies (if not already done)
source venv/bin/activate
pip install -r requirements.txt

# 5. Initialize database and create admin user
python manage.py init_database
```

### 2. Using the Shell Script

```bash
# Run with default settings
./init_database.sh

# Or with custom admin credentials
./init_database.sh -u admin -e admin@company.com -p newpassword123
```

### 3. Admin User Login Process

1. Navigate to `/admin/` or login page
2. Use credentials:
   - **Username**: `admin` (or custom)
   - **Password**: `temppass123` (or custom)
3. You'll be automatically redirected to password change page
4. Set a new secure password
5. After successful change, you can access the dashboard

## Default Initial Data

### Equipment Categories Created:
- Transformers
- Switchgear  
- Motors
- Generators
- HVAC

### Locations Created:
- Main Site
  - Building A
    - Electrical Room
  - Building B

## Dashboard Features

### Site Selection
- Dropdown in header allows filtering by site
- "All - Soluna" shows data from all locations
- Selecting specific site filters dashboard content

### Dynamic Columns
The dashboard displays location-based columns showing:
- **Scheduled Downtimes**: Upcoming maintenance activities
- **Equipment in Repair**: Equipment currently under maintenance

### Urgent & Upcoming Items
- **Urgent Items**: Due within 7 days
- **Upcoming Items**: Due within 30 days

## Environment Variables

You can customize the default admin user using environment variables:

```bash
export ADMIN_USERNAME=myadmin
export ADMIN_EMAIL=admin@mycompany.com  
export ADMIN_PASSWORD=mysecurepass123
export SKIP_MIGRATIONS=false
export SKIP_ADMIN=false
export SKIP_SAMPLE_DATA=false
```

## Troubleshooting

### Database Connection Issues
```bash
# Check if PostgreSQL is running
sudo service postgresql status

# Start if not running
sudo service postgresql start

# Verify database exists
sudo -u postgres psql -l | grep maintenance
```

### Migration Issues
```bash
# Create missing migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Reset migrations (if needed)
python manage.py migrate core zero
python manage.py migrate
```

### Admin User Issues
```bash
# Delete existing admin and recreate
python manage.py shell
>>> from django.contrib.auth.models import User
>>> User.objects.filter(username='admin').delete()
>>> exit()

# Run init_database again
python manage.py init_database --skip-migrations --skip-sample-data
```

## Files Modified/Created

### New Files:
- `core/management/__init__.py`
- `core/management/commands/__init__.py`
- `core/management/commands/init_database.py`
- `core/middleware.py`
- `init_database.sh`
- `DATABASE_INITIALIZATION_GUIDE.md`

### Modified Files:
- `maintenance_dashboard/settings.py` (added middleware)
- `maintenance_dashboard/urls.py` (changed default route to dashboard)
- `core/views.py` (enhanced dashboard view)
- `core/admin.py` (enhanced admin interface)
- `templates/core/dashboard.html` (complete redesign)

## Security Notes

1. **Default Password**: Always change the default admin password immediately
2. **Password Requirements**: Django's built-in password validation is enabled
3. **Forced Change**: First-time login requires password change
4. **Session Security**: Middleware ensures secure authentication flow

## Next Steps

1. **Location Management**: Configure your actual locations via Settings
2. **Equipment Setup**: Add your real equipment through the admin interface
3. **User Management**: Create additional users as needed
4. **Customization**: Modify the dashboard layout as per your requirements

The system is now ready for production use with automatic database initialization and secure admin user setup!