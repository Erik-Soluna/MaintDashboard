# 🚀 Portainer Deployment Guide for Maintenance Dashboard

## 📋 **Current Version Information**
- **Version**: v14800.42dd435
- **Commit Count**: 14800
- **Commit Hash**: 42dd435
- **Branch**: latest
- **Date**: 2025-08-24

## 🔧 **Required Environment Variables**

### **Core Version Variables**
```bash
GIT_COMMIT_COUNT=14800
GIT_COMMIT_HASH=42dd435
GIT_BRANCH=latest
GIT_COMMIT_DATE=2025-08-24
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

### **Step 1: Prepare Portainer Environment**
1. **Copy the environment variables** above into your Portainer stack
2. **Choose the appropriate stack file** (production or development)
3. **Ensure the proxy-network exists** (required for Traefik integration)

### **Step 2: Deploy the Stack**
1. **Upload the stack file** to Portainer
2. **Set all environment variables** as listed above
3. **Deploy the stack**
4. **Monitor the deployment** for any errors

### **Step 3: Verify Deployment**
1. **Check container health** - all services should show as healthy
2. **Test health endpoint**: `http://your-domain/health/simple/`
3. **Test version endpoint**: `http://your-domain/version/`
4. **Verify database connection** and Redis connectivity

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

## 📚 **Additional Resources**

- **GitHub Actions Workflow**: `.github/workflows/auto-version.yml`
- **Version Management**: `version.py` script
- **Build Scripts**: `scripts/build_with_version.ps1`
- **Documentation**: `docs/AUTOMATED_VERSION_MANAGEMENT.md`

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

**Last Updated**: 2025-08-24  
**Version**: v14800.42dd435  
**Branch**: latest

