# Nginx Proxy Manager Setup Guide

## Issue Resolution: URL Masking with maintenance.errorlog.app

The issue you're experiencing where Nginx Proxy Manager isn't properly masking the URL with `maintenance.errorlog.app` is typically caused by missing Django configuration for reverse proxy handling.

## ✅ Django Configuration (Already Fixed)

I've updated your Django settings with the following changes:

1. **Added domain to ALLOWED_HOSTS**: `maintenance.errorlog.app`
2. **Enabled X-Forwarded headers**: `USE_X_FORWARDED_HOST = True`
3. **Added CSRF trusted origins**: For proper form handling behind proxy
4. **Configured proxy SSL headers**: For HTTPS detection

## 🔧 Nginx Proxy Manager Configuration

### Step 1: Create Proxy Host

1. **Access Nginx Proxy Manager** admin interface
2. **Add Proxy Host** with these settings:

```
Domain Names: maintenance.errorlog.app
Scheme: http (your Django container)
Forward Hostname/IP: your-django-container-ip or container-name
Forward Port: 8000
```

### Step 2: SSL Configuration

1. **Enable SSL**: ✅ Force SSL
2. **Request SSL Certificate**: Let's Encrypt
3. **HTTP/2 Support**: ✅ Enable

### Step 3: Advanced Configuration

Add these custom headers in the **Advanced** tab:

```nginx
# Proxy headers for Django
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header X-Forwarded-Host $host;
proxy_set_header X-Forwarded-Port $server_port;

# WebSocket support (if needed)
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";

# Timeouts
proxy_connect_timeout 60s;
proxy_send_timeout 60s;
proxy_read_timeout 60s;

# Buffer settings
proxy_buffering on;
proxy_buffer_size 4k;
proxy_buffers 8 4k;
```

## 🐳 Docker Configuration

### Option 1: Using Docker Compose Network

Ensure both Nginx Proxy Manager and your Django app are on the same Docker network:

```yaml
# In your docker-compose.yml
version: '3.8'

networks:
  nginx-proxy:
    external: true  # If using external NPM network
  
services:
  web:
    # ... your Django config
    networks:
      - nginx-proxy
      - default
```

### Option 2: Container Name Resolution

If using container names, ensure your Django container has a consistent name:

```yaml
services:
  web:
    container_name: maintenance-dashboard
    # ... rest of config
```

Then use `maintenance-dashboard:8000` as your forward address in NPM.

## 🔍 Troubleshooting Common Issues

### Issue 1: 400 Bad Request (Invalid Host Header)

**Cause**: Domain not in `ALLOWED_HOSTS`
**Solution**: ✅ Already fixed - added `maintenance.errorlog.app`

### Issue 2: CSRF Verification Failed

**Cause**: Missing trusted origins
**Solution**: ✅ Already fixed - added `CSRF_TRUSTED_ORIGINS`

### Issue 3: Mixed Content Warnings

**Cause**: HTTPS detection not working
**Solution**: ✅ Already fixed - configured `SECURE_PROXY_SSL_HEADER`

### Issue 4: Assets Not Loading

**Cause**: Static file serving issues
**Solution**: Ensure Django serves static files properly:

```python
# In settings.py (already configured)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
```

## 📋 Environment Variables

Create a `.env` file based on `.env.example`:

```bash
# Copy the example
cp .env.example .env

# Edit with your values
nano .env
```

Key variables for proxy setup:
```env
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,maintenance.errorlog.app
USE_X_FORWARDED_HOST=True
USE_X_FORWARDED_PORT=True
```

## 🧪 Testing the Setup

### 1. Test Direct Access
```bash
# Should work
curl -H "Host: maintenance.errorlog.app" http://your-server:8000
```

### 2. Test Through Proxy
```bash
# Should work and show proper headers
curl -I https://maintenance.errorlog.app
```

### 3. Check Django Logs
```bash
# View Django container logs
docker logs your-django-container

# Look for proper Host header recognition
# Should show: Host: maintenance.errorlog.app
```

## 🔧 NPM Advanced Settings (Custom Config)

If you need more control, you can add custom Nginx configuration:

```nginx
location / {
    proxy_pass http://your-django-container:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Host $host;
    
    # Handle Django static files
    location /static/ {
        proxy_pass http://your-django-container:8000;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    location /media/ {
        proxy_pass http://your-django-container:8000;
        expires 7d;
        add_header Cache-Control "public";
    }
}
```

## 🚀 Quick Fix Steps

1. **Restart Django container** to pick up new settings:
   ```bash
   docker restart your-django-container
   ```

2. **Update NPM proxy host** with proper headers (see Step 3 above)

3. **Test URL**: https://maintenance.errorlog.app

4. **Check logs** if issues persist:
   ```bash
   # NPM logs
   docker logs nginx-proxy-manager
   
   # Django logs  
   docker logs your-django-container
   ```

## 🎯 Expected Result

After these changes:
- ✅ `https://maintenance.errorlog.app` should load your Django app
- ✅ All internal links should use the correct domain
- ✅ Static files and media should load properly
- ✅ Forms should submit without CSRF errors
- ✅ HTTPS should be properly detected

## 📞 Still Having Issues?

If the URL masking still isn't working:

1. **Check DNS**: Ensure `maintenance.errorlog.app` points to your NPM server
2. **Check NPM logs**: `docker logs nginx-proxy-manager`
3. **Verify network connectivity**: NPM can reach Django container
4. **Test with simple HTTP first**: Then add HTTPS

The most common issue is the container networking - ensure NPM can reach your Django container on the specified port.