# Production Web Startup Fixes

## 🎯 **Issue Identified**
Production web container (`maintenance_web_prod`) stuck in "starting" state on `maintenance.errorlog.app`.

## 🔍 **Root Causes Found**

### 1. **Missing Production Scripts in Docker Image**
- Production containers trying to use `start_celery_prod.sh` and `start_celery_beat_prod.sh`
- These scripts weren't made executable in the Dockerfile
- Containers failing to start due to permission errors

### 2. **Management Command Argument Mismatch**
- `generate_pods` view calling command with `--all-sites` argument
- Management command didn't have this argument defined
- Causing Internal Server Errors on `/core/locations/generate-pods/` endpoint

### 3. **Timezone Warnings**
- Naive datetime warnings in maintenance activities
- Not critical but causing log noise

## ✅ **Fixes Implemented**

### 1. **Updated Dockerfile**
```dockerfile
# Before
RUN chmod +x /app/start_celery_beat.sh
RUN chmod +x /app/start_celery.sh

# After  
RUN chmod +x /app/start_celery_beat.sh
RUN chmod +x /app/start_celery.sh
RUN chmod +x /app/start_celery_beat_prod.sh
RUN chmod +x /app/start_celery_prod.sh
```

### 2. **Fixed Management Command**
```python
# Added missing argument to generate_pods command
parser.add_argument(
    '--all-sites',
    action='store_true',
    help='Generate PODs for all sites'
)
```

### 3. **Production Scripts Available**
- `start_celery_prod.sh` - Production Celery worker script
- `start_celery_beat_prod.sh` - Production Celery beat script
- Both scripts remove Playwright dependency and add production optimizations

## 🚀 **Expected Results**

### **Container Startup**
- **Web Container**: Should start successfully and show as "healthy"
- **Celery Container**: Should start successfully and show as "healthy"
- **Celery Beat Container**: Already healthy, should remain so

### **Error Resolution**
- **Internal Server Errors**: `/core/locations/generate-pods/` endpoint should work
- **Permission Errors**: Script execution permissions fixed
- **Startup Delays**: Removed Playwright dependency for faster startup

## 🔧 **Deployment Steps**

1. **Rebuild Production Images**:
   ```bash
   # On production server, rebuild the Docker images
   docker-compose -f portainer-stack.yml build
   ```

2. **Update Portainer Stack**:
   - Use the updated `portainer-stack.yml` in Portainer
   - Redeploy the stack to use new images

3. **Monitor Startup**:
   - Check container logs for any remaining issues
   - Verify all containers show as "healthy"
   - Test the web interface at `maintenance.errorlog.app`

## 📊 **Health Check Status**

| Container | Status | Expected |
|-----------|--------|----------|
| `maintenance_web_prod` | starting → **healthy** | ✅ |
| `maintenance_celery_prod` | starting → **healthy** | ✅ |
| `maintenance_celery_beat_prod` | healthy | ✅ |
| `maintenance_db_prod` | healthy | ✅ |
| `maintenance_redis_prod` | healthy | ✅ |

## 🎉 **Benefits**

- **Reliability**: Fixed startup failures and permission issues
- **Performance**: Removed unnecessary dependencies
- **Stability**: Proper error handling in management commands
- **Monitoring**: Clean logs without Internal Server Errors
- **Production Ready**: Optimized for production environment

## 📝 **Notes**

- All production scripts are now properly executable
- Management commands have correct argument definitions
- Web container should start successfully after rebuild
- Celery services should be healthy and functional 