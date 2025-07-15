# Issue: Main Branch Web Server Startup Failure

## 🚨 Problem Description
The main branch fails to start the web server fully when deployed via Portainer CE using `portainer-stack.yml`. The application does not reach a fully operational state.

## 🔍 Investigation Findings

### 1. **Missing Python Dependencies**
- **Root Cause**: Main branch lacks Python virtual environment and dependencies
- **Evidence**: `ModuleNotFoundError: No module named 'django'` when running `python manage.py runserver`
- **Impact**: Server cannot start without Django and other required packages

### 2. **URL Routing Issues**
- **Root Cause**: Missing URL pattern for `test_database` view
- **Evidence**: `NoReverseMatch: Reverse for 'test_database' not found` in debug.log
- **Impact**: Template rendering fails, causing server startup issues

### 3. **Environment Configuration**
- **Root Cause**: Missing `.env` file and environment setup
- **Evidence**: No environment variables configured for local development
- **Impact**: Database connections and other services fail to initialize

## 🛠️ Required Fixes

### Priority 1: Dependencies Installation
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Priority 2: URL Configuration Fix
- **File**: `maintenance_dashboard/urls.py` or relevant URL configuration
- **Action**: Add missing `test_database` URL pattern or remove references to it
- **Location**: Check templates and views for `{% url 'test_database' %}` references

### Priority 3: Environment Setup
```bash
# Copy development environment
cp env.development .env

# Or run setup script
./setup-env.sh
```

### Priority 4: Database Initialization
```bash
# Run database migrations
python manage.py migrate

# Initialize database with admin user
python manage.py init_database --admin-username admin --admin-email admin@maintenance.local --admin-password temppass123
```

## 🔧 Portainer Deployment Considerations

### Current Stack Configuration Issues:
1. **Build Context**: The `portainer-stack.yml` builds from the current directory
2. **Dependencies**: Docker build should handle Python dependencies via `requirements.txt`
3. **Environment Variables**: Stack uses production environment variables
4. **Health Checks**: Health check endpoint may not exist or be accessible

### Recommended Actions:
1. **Verify Dockerfile**: Ensure `requirements.txt` is properly copied and installed
2. **Check Health Endpoint**: Verify `/core/health/simple/` endpoint exists and responds
3. **Environment Variables**: Ensure all required environment variables are set in Portainer
4. **Database Connection**: Verify database connection parameters in production environment

## 📋 Testing Steps

### Local Testing:
```bash
# 1. Setup environment
./setup-env.sh  # Choose development environment

# 2. Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Test database connection
python manage.py check --database default

# 4. Run migrations
python manage.py migrate

# 5. Start server
python manage.py runserver 0.0.0.0:8000
```

### Portainer Testing:
1. **Deploy Stack**: Use `portainer-stack.yml` in Portainer CE
2. **Check Logs**: Monitor container logs for startup errors
3. **Health Check**: Verify health endpoint responds correctly
4. **Database**: Ensure database container is healthy and accessible

## 🎯 Success Criteria
- [ ] Web server starts without errors
- [ ] All URL patterns resolve correctly
- [ ] Database connection established
- [ ] Health check endpoint responds
- [ ] Application accessible via browser
- [ ] Portainer deployment successful

## 📝 Additional Notes
- The `latest` branch appears to be working correctly
- Main branch is 125 commits behind origin/main
- Consider merging latest changes to main or creating a new stable branch
- Review all automated Cursor branches that were cleaned up for any important fixes

## 🔗 Related Files
- `portainer-stack.yml` - Production deployment configuration
- `docker-compose.yml` - Development deployment configuration
- `requirements.txt` - Python dependencies
- `maintenance_dashboard/settings.py` - Django settings
- `maintenance_dashboard/urls.py` - URL routing configuration
- `env.development` - Development environment template
- `setup-env.sh` - Environment setup script

---
**Issue Created**: $(date)
**Branch**: main
**Environment**: Portainer CE + portainer-stack.yml
**Priority**: High
**Status**: Open