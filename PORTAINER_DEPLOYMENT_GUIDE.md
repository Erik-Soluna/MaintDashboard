# 🚀 Portainer Deployment Guide for Maintenance Dashboard

## 📋 **Current Version Information**
- **Version**: v414.11e13c5
- **Commit Count**: 414
- **Commit Hash**: 11e13c5
- **Branch**: latest
- **Date**: 2025-09-02

## 🔧 **Required Environment Variables**

### **Core Version Variables**
```bash
GIT_COMMIT_COUNT=414
GIT_COMMIT_HASH=11e13c5
GIT_BRANCH=latest
GIT_COMMIT_DATE=2025-09-02
```

### **Database Configuration**
```bash
DB_NAME=maintenance_dashboard_prod
DB_USER=maintenance_user
DB_PASSWORD=SecureProdPassword2024!
POSTGRES_PASSWORD=SecureProdPassword2024!
DB_PORT=5432
```

### **Web Service Configuration**
```bash
WEB_PORT=4405
DEBUG=False
SECRET_KEY=django-production-secret-key-change-this-immediately-2024
ALLOWED_HOSTS=maintenance.errorlog.app,10.0.0.28,localhost,127.0.0.1
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@maintenance.errorlog.app
ADMIN_PASSWORD=SecureAdminPassword2024!
DOMAIN=errorlog.app
```

### **Redis Configuration**
```bash
REDIS_PORT=6379
REDIS_URL=redis://redis:6379/0
```

## 📁 **Deployment Files**

### **Production Stack**
- **File**: `portainer-stack.yml`
- **Use Case**: Production environment with full security
- **Features**: SSL, security headers, production settings

### **Development Stack**
- **File**: `portainer-stack-dev.yml`
- **Use Case**: Development/testing environment
- **Features**: Debug mode, development ports, relaxed security

## 🚀 **Deployment Steps**

### **Step 1: Validate Production Environment**
Before deploying, validate your production environment:

**Linux/macOS:**
```bash
./scripts/validate_production_environment.sh
```

**Windows PowerShell:**
```powershell
.\scripts\validate_production_environment.ps1
```

This will check:
- ✅ All required files are present
- ✅ Environment variables are properly configured
- ✅ Security settings are enabled
- ✅ Docker configuration is valid
- ✅ Version information is up to date

### **Step 2: Prepare for Deployment**
Run the production deployment preparation script:

**Linux/macOS:**
```bash
./scripts/portainer_deploy_production.sh
```

**Windows PowerShell:**
```powershell
.\scripts\portainer_deploy_production.ps1
```

This will:
- 📊 Update version information automatically
- 🔧 Validate production configuration
- 📋 Generate deployment checklist
- 📝 Create environment variables summary

### **Step 3: Deploy to Portainer**
1. **Copy the environment variables** from the script output into your Portainer stack
2. **Upload the stack file** (`portainer-stack.yml`) to Portainer
3. **Set all environment variables** as listed in the script output
4. **Deploy the stack**
5. **Monitor the deployment** for any errors

### **Step 4: Verify Deployment**
1. **Check container health** - all services should show as healthy
2. **Test health endpoint**: `https://your-domain/health/simple/`
3. **Test version endpoint**: `https://your-domain/version/`
4. **Verify database connection** and Redis connectivity
5. **Follow the deployment checklist** created by the preparation script

## 🔍 **Health Check Endpoints**

### **Application Health**
- **URL**: `/health/simple/`
- **Expected Response**: `{"status": "ok", "database": "healthy", "redis": "healthy"}`
- **Check Interval**: 30 seconds

### **Version Information**
- **URL**: `/version/`
- **Expected Response**: Current version JSON with commit information
- **Auto-updated**: Yes, via GitHub Actions

## 📊 **Monitoring & Troubleshooting**

### **Container Health Status**
- **Web Service**: Should show as healthy with `/health/simple/` endpoint
- **Database**: PostgreSQL health check via `pg_isready`
- **Redis**: Redis health check via `redis-cli ping`
- **Celery**: Worker health check via `celery inspect ping`

### **Common Issues**
1. **Health Check Failures**: Verify `/health/simple/` endpoint is accessible
2. **Database Connection**: Check PostgreSQL credentials and network connectivity
3. **Redis Connection**: Verify Redis service is running and accessible
4. **Version Mismatch**: Ensure environment variables match current version.json

## 🔄 **Auto-Version Management**

### **How It Works**
1. **GitHub Actions** automatically updates version files on commits
2. **Version information** is embedded in Docker images during build
3. **Environment variables** are injected at runtime
4. **Health checks** verify the application is running with correct version

### **Updating Versions**
1. **Automatic**: GitHub Actions updates version files automatically
2. **Manual**: Use `python version.py --update` to refresh version information
3. **Redeploy**: Update environment variables in Portainer and redeploy

## 🛠️ **Automated Deployment Scripts**

### **Production Deployment Scripts**
The following scripts automate the production deployment process:

#### **Linux/macOS Scripts**
- **`scripts/portainer_deploy_production.sh`** - Complete production deployment preparation
- **`scripts/validate_production_environment.sh`** - Production environment validation
- **`scripts/portainer_build.sh`** - Version information capture for Portainer

#### **Windows PowerShell Scripts**
- **`scripts/portainer_deploy_production.ps1`** - Complete production deployment preparation
- **`scripts/validate_production_environment.ps1`** - Production environment validation
- **`scripts/portainer_build.ps1`** - Version information capture for Portainer

### **Script Features**
- ✅ **Automatic version detection** from git repository
- ✅ **Environment validation** before deployment
- ✅ **Security checks** for production readiness
- ✅ **Deployment checklist generation**
- ✅ **Cross-platform support** (Linux, macOS, Windows)
- ✅ **Comprehensive error handling** and reporting

### **Usage Examples**
```bash
# Validate production environment
./scripts/validate_production_environment.sh

# Prepare for deployment
./scripts/portainer_deploy_production.sh

# Windows PowerShell
.\scripts\validate_production_environment.ps1
.\scripts\portainer_deploy_production.ps1
```

## 📚 **Additional Resources**

- **GitHub Actions Workflow**: `.github/workflows/auto-version.yml`
- **Version Management**: `version.py` script
- **Build Scripts**: `scripts/build_with_version.ps1`
- **Documentation**: `docs/AUTOMATED_VERSION_MANAGEMENT.md`
- **Deployment Scripts**: `scripts/portainer_deploy_production.*`
- **Validation Scripts**: `scripts/validate_production_environment.*`

## ✅ **Deployment Checklist**

- [ ] Environment variables configured in Portainer
- [ ] Appropriate stack file selected (production/development)
- [ ] Proxy network exists and is accessible
- [ ] Stack deployed successfully
- [ ] All containers showing as healthy
- [ ] Health endpoints responding correctly
- [ ] Version information displaying correctly
- [ ] Database and Redis connections working
- [ ] Application accessible via configured domain

---

**Last Updated**: 2025-09-02  
**Version**: v414.11e13c5  
**Branch**: latest

