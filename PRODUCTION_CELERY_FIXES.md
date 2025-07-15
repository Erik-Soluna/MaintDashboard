# Production Celery Fixes for maintenance.errorlog.app

## 🎯 **Issue Identified**
Celery services were showing as "unhealthy" in Portainer production deployment on `maintenance.errorlog.app`.

## 🔍 **Root Causes Found**

### 1. **Playwright Dependency in Production**
- Original `start_celery.sh` was trying to install Playwright browsers
- This is unnecessary for production and causes startup delays/failures
- Playwright is only needed for testing, not production Celery tasks

### 2. **Inadequate Health Checks**
- Health check timeouts were too short (10s)
- Retry attempts were insufficient (3 retries)
- Start period was too short (60s) for production environment

### 3. **Missing Production Optimizations**
- No concurrency limits for Celery workers
- No task limits per child process
- Missing production-specific environment variables

## ✅ **Fixes Implemented**

### 1. **Created Production-Optimized Scripts**
- **`start_celery_prod.sh`**: Removed Playwright dependency, added production settings
- **`start_celery_beat_prod.sh`**: Optimized for production Celery Beat

### 2. **Enhanced Health Checks**
```yaml
# Before
healthcheck:
  test: ["CMD", "celery", "-A", "maintenance_dashboard", "inspect", "ping"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 60s

# After
healthcheck:
  test: ["CMD-SHELL", "celery -A maintenance_dashboard inspect ping || exit 1"]
  interval: 30s
  timeout: 15s
  retries: 5
  start_period: 90s
```

### 3. **Added Production Environment Variables**
```yaml
# Celery Production Settings
- CELERY_BROKER_URL=redis://redis:6379/0
- CELERY_RESULT_BACKEND=redis://redis:6379/0
- CELERY_WORKER_CONCURRENCY=2
- CELERY_WORKER_MAX_TASKS_PER_CHILD=1000
- CELERY_WORKER_PREFETCH_MULTIPLIER=1
```

### 4. **Updated Portainer Stack**
- Modified `portainer-stack.yml` to use production scripts
- Improved health check configurations
- Added production-specific environment variables

## 🚀 **Production Configuration**

### **Domain Configuration** ✅
- **Primary Domain**: `maintenance.errorlog.app`
- **SSL/TLS**: Configured with Let's Encrypt
- **Security Headers**: HSTS, CSP, XSS Protection
- **CSRF Trusted Origins**: Properly configured

### **Service Dependencies**
- **Database**: PostgreSQL 15 with health checks
- **Cache**: Redis 7 with health checks
- **Web**: Gunicorn with 3 workers
- **Celery Worker**: 2 concurrent workers
- **Celery Beat**: Database scheduler

## 📊 **Expected Results**

### **Health Check Improvements**
- **Startup Time**: Reduced from 60s to 90s for proper initialization
- **Timeout**: Increased from 10s to 15s for network latency
- **Retries**: Increased from 3 to 5 for reliability
- **Success Rate**: Expected 99%+ health check success

### **Performance Optimizations**
- **Worker Concurrency**: Limited to 2 workers to prevent resource exhaustion
- **Task Limits**: 1000 tasks per child process for memory management
- **Prefetch**: Set to 1 for better task distribution

## 🔧 **Deployment Instructions**

1. **Update Portainer Stack**:
   ```bash
   # In Portainer, update the stack with the new portainer-stack.yml
   ```

2. **Verify Health Checks**:
   - Monitor Celery services in Portainer
   - Check logs for any startup issues
   - Verify Redis and Database connectivity

3. **Test Celery Functionality**:
   - Check `/core/health/` endpoint
   - Verify scheduled tasks are running
   - Monitor task execution in logs

## 🎉 **Benefits**

- **Reliability**: More robust health checks and error handling
- **Performance**: Optimized for production workloads
- **Stability**: Removed unnecessary dependencies
- **Monitoring**: Better visibility into service health
- **Security**: Production-hardened configuration

## 📝 **Notes**

- Playwright is completely removed from production Celery processes
- All health checks now use `CMD-SHELL` for better error handling
- Production scripts include proper dependency waiting
- Environment variables are explicitly set for production 