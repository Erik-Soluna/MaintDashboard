# Maintenance Dashboard

A comprehensive Django-based maintenance management system with unified calendar and maintenance functionality.

## 🚀 Quick Start

The app is deployed via **Portainer** using the stack files in this repo:

- **Production:** `portainer-stack.yml`
- **Development:** `portainer-stack-dev.yml`

### Setup
1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd MaintDashboard
   ```

2. **Deploy the stack in Portainer**
   - Create a stack from `portainer-stack-dev.yml` (dev) or `portainer-stack.yml` (prod).
   - Set the required environment variables (see `env.example`) — at minimum
     `SECRET_KEY`, `ALLOWED_HOSTS`, and the database credentials.

3. **Create the admin user** (in the running `web` container)
   ```bash
   python manage.py create_admin_user --username admin --force
   ```

> Need a quick local instance for development? Run with Postgres via the dev
> stack; a SQLite-only run is not currently supported (a Postgres-specific
> migration is required).

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
│   ├── 📂 database/            # Database scripts
│   ├── 📂 deployment/          # Deployment scripts
│   ├── 📂 celery/              # Celery management scripts
│   └── 📂 utilities/           # Utility scripts
├── 📂 tests/                   # Test files and test suites
├── 📂 docs/                    # Documentation and guides
├── 📂 deployment/              # Environment configurations
├── 📂 images/                  # Screenshots and images
├── 🐳 Dockerfile               # Main Docker configuration
├── 🐳 portainer-stack.yml      # Production Portainer stack (canonical)
├── 🐳 portainer-stack-dev.yml  # Development Portainer stack (canonical)
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
Run inside the running `web` container (e.g. via the Portainer console or
`docker exec <web-container> ...`):
```bash
python tests/test_unified_system.py
python tests/test_maintenance_reports.py
python tests/test_web_interface.py
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
- **Database**: `scripts/database/ensure_database.sh` - Comprehensive database initialization
- **Deployment**: `scripts/deployment/setup-env.sh` - Environment setup
- **Celery**: `scripts/celery/start_celery.sh` - Celery worker startup
- **Utilities**: `scripts/utilities/` - Various utility scripts

See `scripts/README.md` for complete documentation.

## 🚀 Deployment

Deployment is via **Portainer stacks** (the canonical compose files):
- `portainer-stack.yml` — production
- `portainer-stack-dev.yml` — development

Create/update the stack in Portainer and set the required environment variables
(see `env.example`). Pushing to the `latest` branch builds the dev image; redeploy
the dev stack to pick it up.

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
**Version**: 2.0 (Unified System)# Test commit for auto-version workflow
