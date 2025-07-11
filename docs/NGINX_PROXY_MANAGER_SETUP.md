# Nginx Proxy Manager Setup with Portainer

This guide explains how to connect your Django maintenance dashboard to Nginx Proxy Manager when both are running as separate stacks in Portainer.

## Overview

This setup provides:
- SSL termination with automatic Let's Encrypt certificates
- Domain-based routing to your Django application
- Network isolation with intentional connections
- Secure proxy configuration

## Prerequisites

- Portainer running and accessible
- Django app deployed as a Portainer stack
- Nginx Proxy Manager deployed as a separate Portainer stack
- Domain name pointing to your server's IP address

## Architecture

```
Internet → Nginx Proxy Manager (Port 80/443) → Django App (Port 8000)
```

**Key Components:**
- **Nginx Proxy Manager**: Handles SSL, domains, and proxying
- **Django App**: Your maintenance dashboard
- **Proxy Network**: Shared network for container communication

## Step-by-Step Setup

### 1. Create Shared Network

1. **In Portainer, go to Networks**
2. **Click "Add network"**
3. **Configure:**
   - **Name**: `proxy-network`
   - **Driver**: `bridge`
   - **Access Control**: `Administrators`
4. **Click "Create network"**

### 2. Connect Django App to Proxy Network

1. **Go to Containers**
2. **Find your Django web container** (e.g., `slnh-maintenance-web-1`)
3. **Click on the container name**
4. **Scroll to "Connected networks" section**
5. **Click "Join network" or "Connect"**
6. **Select** `proxy-network`
7. **Click "Connect"**

### 3. Connect Nginx Proxy Manager to Proxy Network

1. **Go to Containers**
2. **Find your Nginx Proxy Manager container** (e.g., `nginx-proxy-manager-app-1`)
3. **Click on the container name**
4. **Scroll to "Connected networks" section**
5. **Click "Join network" or "Connect"**
6. **Select** `proxy-network`
7. **Click "Connect"**

### 4. Verify Network Connectivity

1. **Access Nginx Proxy Manager container console**
2. **Run connectivity test:**
   ```bash
   curl -v http://slnh-maintenance-web-1:8000/
   ```
3. **Expected response:** HTTP 302 redirect to `/core/dashboard/`

### 5. Configure Proxy Host in Nginx Proxy Manager

1. **Access Nginx Proxy Manager admin panel** (typically port 81)
2. **Go to "Proxy Hosts"**
3. **Click "Add Proxy Host"**
4. **Configure Details tab:**
   - **Domain Names**: `maintenance.errorlog.app`
   - **Scheme**: `https`
   - **Forward Hostname/IP**: `slnh-maintenance-web-1`
   - **Forward Port**: `8000`
   - **Cache Assets**: Enable
   - **Block Common Exploits**: Enable
   - **Websockets Support**: Enable

5. **Configure SSL tab:**
   - **SSL Certificate**: `*.errorlog.app` (or create new)
   - **Force SSL**: Enable
   - **HTTP/2 Support**: Enable
   - **HSTS Enabled**: Enable
   - **HSTS Subdomains**: Enable

6. **Click "Save"**

### 6. Test the Setup

1. **Visit your domain:** `https://maintenance.errorlog.app`
2. **Expected result:** Django app loads properly with SSL
3. **Verify SSL:** Check for green padlock in browser

## Container Configuration

### Django App Container Requirements

Your Django app should have these environment variables:

```yaml
environment:
  - ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0,maintenance.errorlog.app
  - DEBUG=False  # For production
  - SECRET_KEY=your-secret-key-here
```

### Port Configuration

- **Django Container**: Exposes port 8000 internally
- **Host Port Mapping**: 4405:8000 (for direct access if needed)
- **Nginx Proxy Manager**: Uses internal port 8000 via container name

## Network Configuration

### Network Isolation

Each Portainer stack creates its own isolated network:

- **Django Stack**: `slnh-maintenance_default` (172.18.0.0/16)
- **Nginx Proxy Manager**: `nginx-proxy-manager_default` (172.19.0.0/16)
- **Shared Network**: `proxy-network` (172.20.0.0/16)

### Container Communication

- **Internal Communication**: Via `proxy-network` using container names
- **External Access**: Via Nginx Proxy Manager on ports 80/443
- **Direct Access**: Available on port 4405 (optional, can be disabled)

## Troubleshooting

### Common Issues

#### 1. 504 Gateway Timeout
- **Symptom**: Nginx shows 504 error
- **Cause**: Containers not on same network
- **Solution**: Ensure both containers are connected to `proxy-network`

#### 2. DNS Resolution Issues
- **Symptom**: Domain doesn't resolve
- **Cause**: DNS not configured
- **Solution**: Verify A record points to server IP

#### 3. SSL Certificate Issues
- **Symptom**: SSL warnings or errors
- **Cause**: Certificate not generated or expired
- **Solution**: Regenerate Let's Encrypt certificate

#### 4. Connection Refused
- **Symptom**: Can't connect to Django app
- **Cause**: Wrong port or container name
- **Solution**: Use `slnh-maintenance-web-1:8000`

### Debug Commands

**Test from Nginx Proxy Manager container:**
```bash
# Test container connectivity
curl -v http://slnh-maintenance-web-1:8000/

# Test DNS resolution
nslookup maintenance.errorlog.app

# Check network configuration
ip route show
```

**Test from Django container:**
```bash
# Test Django app directly
curl -v http://localhost:8000/

# Check allowed hosts
python manage.py shell -c "from django.conf import settings; print(settings.ALLOWED_HOSTS)"
```

## Security Considerations

### Network Security
- **Principle of Least Privilege**: Only necessary containers connected
- **Network Isolation**: Each stack isolated by default
- **Intentional Connections**: Explicit network connections only

### Access Control
- **SSL/TLS**: All traffic encrypted
- **HSTS**: Prevents downgrade attacks
- **Block Common Exploits**: Enabled in proxy configuration

### Monitoring
- **Container Health**: Monitor container status
- **Network Traffic**: Monitor unusual connections
- **SSL Expiration**: Monitor certificate expiration

## Maintenance

### Regular Tasks
- **Certificate Renewal**: Automatic via Let's Encrypt
- **Container Updates**: Update base images regularly
- **Network Monitoring**: Check for unusual traffic
- **Backup Configuration**: Export proxy host configurations

### Configuration Backup
Export your Nginx Proxy Manager configuration regularly:
1. **Go to Nginx Proxy Manager admin**
2. **Settings → Export Configuration**
3. **Store backup securely**

## Advanced Configuration

### Custom SSL Certificates
If using custom certificates instead of Let's Encrypt:

1. **Upload certificate files**
2. **Configure in SSL tab**
3. **Set up renewal process**

### Multiple Domains
To add additional domains:

1. **Add domain to proxy host**
2. **Update Django ALLOWED_HOSTS**
3. **Configure SSL for new domain**

### IP Restrictions
To restrict access by IP:

1. **Go to Access Lists in Nginx Proxy Manager**
2. **Create IP whitelist**
3. **Apply to proxy host**

## References

- [Nginx Proxy Manager Documentation](https://nginxproxymanager.com/guide/)
- [Portainer Documentation](https://docs.portainer.io/)
- [Django Deployment Documentation](https://docs.djangoproject.com/en/stable/howto/deployment/)

## Changelog

- **Initial Setup**: Basic proxy configuration
- **Network Isolation**: Added shared network setup
- **Security Hardening**: Added SSL and security configurations