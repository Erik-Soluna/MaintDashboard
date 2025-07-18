# Scripts Directory

This directory contains all utility scripts for the Maintenance Dashboard application, organized by category.

## Directory Structure

### 📁 database/
Database initialization, setup, and maintenance scripts.

- **`ensure_database.sh`** - Comprehensive database initialization with cache table creation
- **`ensure-database.sh`** - Alternative database initialization script
- **`init_database.sh`** - Basic database initialization
- **`auto_init_database.py`** - Python script for automated database initialization
- **`create_database.py`** - Database creation utility
- **`fix-database-now.sh`** - Quick database fixes
- **`fix-database-user.sh`** - Database user permission fixes
- **`fix-database-user-docker.sh`** - Docker-specific database user fixes

### 📁 deployment/
Deployment and environment setup scripts.

- **`docker-entrypoint.sh`** - Docker container entrypoint script
- **`setup-env.sh`** - Environment setup script
- **`setup_auto_init.sh`** - Automated initialization setup
- **`fix-permissions.sh`** - Permission fixes for deployment
- **`fix_roles_permissions.sh`** - Role and permission management

### 📁 celery/
Celery task queue management scripts.

- **`start_celery.sh`** - Start Celery worker (development)
- **`start_celery_prod.sh`** - Start Celery worker (production)
- **`start_celery_beat.sh`** - Start Celery beat scheduler (development)
- **`start_celery_beat_prod.sh`** - Start Celery beat scheduler (production)

### 📁 utilities/
General utility and helper scripts.

- **`create_demo_reports.py`** - Generate demo maintenance reports
- **`create_equipment_sophie.py`** - Create sample equipment data
- **`create_test_prompt.py`** - Generate test prompts
- **`generate_dga_pdf.py`** - PDF generation utility

## Usage

### Database Setup
```bash
# For comprehensive database initialization
./scripts/database/ensure_database.sh

# For basic setup
./scripts/database/init_database.sh
```

### Deployment
```bash
# Setup environment
./scripts/deployment/setup-env.sh

# Fix permissions
./scripts/deployment/fix-permissions.sh
```

### Celery Management
```bash
# Start Celery worker (development)
./scripts/celery/start_celery.sh

# Start Celery beat scheduler (production)
./scripts/celery/start_celery_beat_prod.sh
```

### Utilities
```bash
# Generate demo data
python scripts/utilities/create_demo_reports.py

# Create sample equipment
python scripts/utilities/create_equipment_sophie.py
```

## Script Categories

### 🔧 Database Scripts
These scripts handle all database-related operations including initialization, migrations, and troubleshooting.

### 🚀 Deployment Scripts
Scripts for setting up and maintaining the application in various environments (development, staging, production).

### ⚡ Celery Scripts
Task queue management for background job processing and scheduled tasks.

### 🛠️ Utility Scripts
Helper scripts for data generation, testing, and various maintenance tasks.

## Notes

- All shell scripts are executable and include proper error handling
- Python scripts include proper Django environment setup
- Scripts are designed to be idempotent where possible
- Environment variables are sourced from appropriate configuration files
- Scripts include logging and status reporting for better debugging

## Troubleshooting

If you encounter issues with any script:

1. Check that all required environment variables are set
2. Ensure database connectivity is available
3. Verify that Django settings are properly configured
4. Check script permissions (should be executable)
5. Review script logs for specific error messages

For database-specific issues, start with `ensure_database.sh` as it includes comprehensive error handling and recovery mechanisms. 