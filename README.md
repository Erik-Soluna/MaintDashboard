# Maintenance Dashboard

A comprehensive Django-based maintenance management system with unified calendar and maintenance functionality.

## 🚀 Quick Start

### Prerequisites
- Docker Desktop
- Git

### Setup
1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd MaintDashboard
   ```

2. **Start the system**
   ```bash
   docker compose up -d
   ```

3. **Access the application**
   - URL: http://localhost:8000/
   - Username: `admin`
   - Password: `temppass123`

## 📁 Project Structure

```
MaintDashboard/
├── 📂 core/                    # Core application functionality
├── 📂 equipment/               # Equipment management
├── 📂 events/                  # Calendar events (unified with maintenance)
├── 📂 maintenance/             # Maintenance activities
├── 📂 maintenance_dashboard/   # Django project settings
├── 📂 templates/               # HTML templates
├── 📂 static/                  # Static files (CSS, JS, images)
├── 📂 media/                   # User-uploaded files
├── 📂 scripts/                 # Utility scripts and automation
├── 📂 tests/                   # Test files and test suites
├── 📂 docs/                    # Documentation and guides
├── 📂 deployment/              # Deployment configurations
├── 📂 debug/                   # Debug files and logs
├── 📂 images/                  # Screenshots and images
├── 📂 playwright/              # Playwright testing
├── 🐳 docker-entrypoint.sh    # Docker entrypoint script
├── 🐳 Dockerfile               # Main Docker configuration
├── 🐳 docker-compose.yml       # Docker Compose configuration
├── 📄 manage.py                # Django management script
└── 📄 README.md                # This file
```

## 🔧 Key Features

### ✅ Unified Calendar/Maintenance System
- **Single Data Model**: Calendar events with `event_type='maintenance'` are maintenance activities
- **No Synchronization Issues**: Eliminated complex sync operations
- **Compatibility Properties**: Seamless integration with existing views

### ✅ Equipment Management
- Hierarchical location system (Site > Pod > MDC)
- Equipment categorization and documentation
- Location-based filtering and selection

### ✅ Maintenance Activities
- Activity type categories with global options
- Scheduled and on-demand maintenance
- Status tracking and reporting

### ✅ User Management
- Role-based access control (RBAC)
- Customer-specific data isolation
- Admin and user interfaces

## 🧪 Testing

### Automated Tests
```bash
# Run comprehensive test suite
docker compose exec web python tests/test_unified_system.py

# Run specific test categories
docker compose exec web python tests/test_maintenance_reports.py
docker compose exec web python tests/test_web_interface.py
```

### Manual Testing
1. Access http://localhost:8000/
2. Create calendar events with type "Maintenance Activity"
3. Verify they appear in both calendar and maintenance views
4. Test equipment location selection and filtering

## 📚 Documentation

- **Setup Guide**: `docs/quickstart.md`
- **Unified System Testing**: `docs/UNIFIED_SYSTEM_TESTING.md`
- **Deployment Guide**: `docs/deployment/portainer.md`
- **Security Configuration**: `docs/SECURITY_CONFIGURATION.md`

## 🛠️ Development

### Scripts Directory
- `scripts/setup-env.sh` - Environment setup
- `scripts/ensure_database.sh` - Database initialization
- `scripts/fix-database-user.sh` - Database user fixes
- `scripts/start_celery.sh` - Celery worker startup

### Debug Directory
- Debug scripts and utilities
- Log files and JSON outputs
- Performance optimization tools

## 🚀 Deployment

### Docker Compose
```bash
# Development
docker compose up -d

# Production
docker compose -f deployment/docker-compose.prod.yml up -d
```

### Portainer Stack
- `deployment/portainer-stack.yml` - Production stack
- `deployment/portainer-stack-dev.yml` - Development stack

## 🔒 Security

- Role-based access control
- Customer data isolation
- Secure password handling
- HTTPS configuration ready

## 📊 Monitoring

- Health checks for all services
- Cache functionality verification
- Database connectivity monitoring
- Celery task monitoring

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `docker compose exec web python tests/test_unified_system.py`
5. Submit a pull request

## 📝 License

This project is proprietary software.

---

**Status**: ✅ Production Ready  
**Last Updated**: July 2025  
**Version**: 2.0 (Unified System)