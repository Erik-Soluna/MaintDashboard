# Maintenance Dashboard

[![Development Status](https://img.shields.io/badge/status-unstable-orange.svg)](https://github.com/your-repo/maintenance-dashboard)
[![Branch](https://img.shields.io/badge/branch-unstable%2Fdevelopment-orange.svg)](https://github.com/your-repo/maintenance-dashboard/tree/unstable/development)

> ⚠️ **UNSTABLE DEVELOPMENT BRANCH** ⚠️
> 
> This branch is currently under active development and contains experimental features. 
> **Do not use in production** - features may be incomplete, broken, or change without notice.
> 
> For stable releases, please use the `main` branch or check for tagged releases.

A Django-based web application for managing equipment maintenance, events, and related operations with integrated Docker stack management.

## ✨ Key Features

- **Equipment Management** - Track and manage equipment items
- **Maintenance Scheduling** - Plan and track maintenance activities  
- **Event Logging** - Record and monitor maintenance events
- **Calendar Integration** - iCal and Google Calendar sync
- **CSV Import/Export** - Bulk data operations
- **Container Management** - Integrated Portainer for Docker management
- **User Authentication** - Secure role-based access control

## 🚀 Quick Start

### Docker Installation (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd maintenance-dashboard

# Start all services
docker-compose up -d

# Create admin user
docker-compose exec web python manage.py createsuperuser
```

**Access the application**: `http://localhost:8000`  
**Container management**: `http://localhost:9000` (Portainer)

> **🌐 Using with Nginx Proxy Manager?** See the [Nginx Proxy Manager Setup Guide](docs/NGINX_PROXY_MANAGER_SETUP.md) for SSL proxy configuration with custom domains.

### Manual Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up database (PostgreSQL required)
python manage.py migrate
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

## 📚 Documentation

**Complete documentation is available in the [docs/](docs/) directory.**

### Quick Links
- **📖 [Full Documentation Index](docs/README.md)** - Complete guide to all documentation
- **⚡ [Quick Start Guide](docs/quickstart.md)** - Detailed setup instructions
- **🐳 [Docker Deployment](docs/deployment/docker.md)** - Docker setup and configuration
- **🌐 [Nginx Proxy Manager Setup](docs/NGINX_PROXY_MANAGER_SETUP.md)** - SSL proxy configuration with Portainer
- **🗄️ [Database Setup](docs/database/setup.md)** - Database configuration
- **✨ [Features Guide](docs/features/overview.md)** - Complete feature documentation
- **🔧 [Development Setup](docs/development/setup.md)** - Development environment
- **🆘 [Troubleshooting](docs/troubleshooting/common-issues.md)** - Common issues and fixes

## 🛠️ Technology Stack

- **Backend**: Django 4.x, PostgreSQL, Redis
- **Frontend**: Bootstrap, JavaScript, crispy-forms
- **Containerization**: Docker, Docker Compose
- **Management**: Portainer for container orchestration

## 📋 Prerequisites

- **Docker & Docker Compose** (recommended) OR
- **Python 3.8+**, **PostgreSQL 12+**, **Redis** (manual installation)

## 🔧 Configuration

Create a `.env` file for environment variables:

```env
# Database
DB_NAME=maintenance_dashboard
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432

# Django
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Redis
REDIS_URL=redis://localhost:6379/0
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

See [Development Guide](docs/development/contributing.md) for detailed contribution guidelines.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- **Documentation**: [docs/README.md](docs/README.md)
- **Issues**: [GitHub Issues](link-to-issues)
- **Discussions**: [GitHub Discussions](link-to-discussions)

---

**Need help?** Start with the [Quick Start Guide](docs/quickstart.md) or check [Common Issues](docs/troubleshooting/common-issues.md).