# Portainer Stack Management

Portainer is a lightweight management UI that allows you to easily manage your Docker environments. It has been integrated into the Maintenance Dashboard stack to provide an intuitive interface for container management, monitoring, and stack operations.

> **🚀 Quick Start**: If you want to get started immediately, see the [Portainer Quick Start Guide](PORTAINER_QUICKSTART.md) for a step-by-step walkthrough.

## Table of Contents

- [Overview](#overview)
- [Installation & Setup](#installation--setup)
- [First-Time Configuration](#first-time-configuration)
- [Accessing Portainer](#accessing-portainer)
- [Using Portainer with the Maintenance Dashboard](#using-portainer-with-the-maintenance-dashboard)
- [Common Operations](#common-operations)
- [Monitoring & Troubleshooting](#monitoring--troubleshooting)
- [Security Considerations](#security-considerations)
- [Production Deployment](#production-deployment)
- [Backup & Restore](#backup--restore)
- [Troubleshooting](#troubleshooting)

## Overview

Portainer provides the following benefits for the Maintenance Dashboard:

- **Visual Container Management**: View and manage all containers in a web-based interface
- **Stack Management**: Manage Docker Compose stacks through the UI
- **Real-time Monitoring**: Monitor container health, resources, and logs
- **Easy Scaling**: Scale services up or down with simple controls
- **Log Management**: Access container logs without using command line
- **Resource Monitoring**: View CPU, memory, and network usage
- **Template Management**: Deploy new stacks from templates

## Installation & Setup

Portainer is automatically included in the Docker Compose configuration. Simply start the stack as usual:

### Development Environment

```bash
# Start the entire stack including Portainer
docker-compose up -d

# Or build and start if it's the first time
docker-compose up --build -d
```

### Production Environment

```bash
# Start with production configuration
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Verify Portainer is Running

```bash
# Check if Portainer container is running
docker-compose ps portainer

# View Portainer logs
docker-compose logs portainer
```

## First-Time Configuration

1. **Access Portainer**: Navigate to `http://localhost:9000` (or `https://localhost:9443` for HTTPS)

2. **Create Admin User**: 
   - On first access, you'll be prompted to create an admin user
   - Choose a strong password (minimum 12 characters)
   - Complete the setup wizard

3. **Connect to Docker Environment**:
   - Select "Docker" as the environment type
   - Choose "Local" to manage the local Docker environment
   - Click "Connect"

4. **Verify Setup**:
   - You should see the dashboard with container statistics
   - Navigate to "Containers" to see all running containers
   - Navigate to "Stacks" to see the maintenance dashboard stack

## Accessing Portainer

### URLs

- **Development**: 
  - HTTP: `http://localhost:9000`
  - HTTPS: `https://localhost:9443`

- **Production**: 
  - HTTPS: `https://yourdomain.com:9443` (recommended)
  - Configure reverse proxy for custom domain

### Default Ports

- **9000**: HTTP interface (development only)
- **9443**: HTTPS interface (recommended for production)

## Using Portainer with the Maintenance Dashboard

### Viewing the Stack

1. Navigate to **Stacks** in the left sidebar
2. Find the maintenance dashboard stack (usually named after your directory)
3. Click on the stack name to view details

### Managing Services

From the stack view, you can:
- **Start/Stop/Restart** individual services
- **View logs** for each service
- **Scale services** (increase/decrease replicas)
- **Update service configurations**

### Monitoring Containers

1. Go to **Containers** in the left sidebar
2. View all containers with their status, resource usage, and uptime
3. Click on any container for detailed information:
   - Resource usage graphs
   - Environment variables
   - Volume mounts
   - Network settings

## Common Operations

### Restarting Services

1. Navigate to **Stacks** → Your stack
2. Click on the service you want to restart
3. Click **Restart** button

Or restart the entire stack:
1. Go to **Stacks** → Your stack
2. Click **Stop stack** then **Start stack**

### Viewing Logs

1. Navigate to **Containers**
2. Click on the container name
3. Go to **Logs** tab
4. Use the search and filter options to find specific log entries

### Updating Service Configuration

1. Navigate to **Stacks** → Your stack
2. Click **Editor** tab
3. Modify the Docker Compose configuration
4. Click **Update the stack**

⚠️ **Warning**: Always test configuration changes in development first.

### Scaling Services

1. Navigate to **Services** or go to your stack
2. Click on the service you want to scale
3. Adjust the **Replicas** number
4. Click **Scale** or **Update service**

Common scaling scenarios:
- Scale `web` service for higher traffic
- Scale `celery` workers for background processing

### Managing Volumes

1. Navigate to **Volumes** in the left sidebar
2. View all volumes and their usage
3. Create backups or inspect volume contents

### Managing Networks

1. Navigate to **Networks** in the left sidebar
2. View network topology and connected containers
3. Troubleshoot connectivity issues

## Monitoring & Troubleshooting

### Container Health Monitoring

Portainer provides real-time monitoring:

1. **Dashboard Overview**: Quick stats on containers, images, volumes
2. **Container Details**: CPU, memory, network, and disk I/O graphs
3. **Health Checks**: Visual indicators for container health status

### Log Analysis

Effective log monitoring:

1. **Real-time Logs**: Use the log viewer for real-time monitoring
2. **Log Filtering**: Filter by time range, log level, or search terms
3. **Download Logs**: Export logs for external analysis

### Resource Usage

Monitor resource consumption:

1. **Container Stats**: View CPU and memory usage per container
2. **Host Stats**: Overall system resource usage
3. **Alerts**: Set up notifications for resource thresholds (Portainer Business)

### Common Issues and Solutions

| Issue | Solution |
|-------|----------|
| Container not starting | Check logs and environment variables |
| High memory usage | Scale services or optimize application |
| Database connection issues | Verify DB container health and network connectivity |
| Service unavailable | Check port mappings and firewall settings |

## Security Considerations

### Development Environment

- Portainer runs on HTTP (port 9000) for ease of development
- Use strong admin passwords
- Limit network access to development machines only

### Production Environment

- **HTTPS Only**: Production setup forces HTTPS (port 9443)
- **SSL Certificates**: Configure proper SSL certificates
- **Firewall**: Restrict access to Portainer ports
- **Regular Updates**: Keep Portainer updated to latest version

### Access Control

1. **User Management**: Create separate users for team members
2. **Role-Based Access**: Assign appropriate roles (Admin, User, Read-only)
3. **Team Management**: Organize users into teams with specific permissions

### Security Best Practices

- Enable two-factor authentication (Portainer Business)
- Regular security audits of user access
- Monitor login attempts and activities
- Use environment-specific access controls

## Production Deployment

### SSL Configuration

For production, configure SSL certificates:

1. **Certificate Files**: Place SSL certificates in `./ssl/` directory
2. **Environment Variables**: Set appropriate SSL environment variables
3. **Reverse Proxy**: Configure nginx or similar for SSL termination

### Environment Variables

```bash
# Production environment variables
PORTAINER_HTTP_DISABLED=true
PORTAINER_HTTPS_PORT=9443
PORTAINER_SSL_CERT=/certs/cert.pem
PORTAINER_SSL_KEY=/certs/key.pem
```

### Reverse Proxy Setup

Example nginx configuration for Portainer:

```nginx
server {
    listen 443 ssl;
    server_name portainer.yourdomain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass https://localhost:9443;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### High Availability

For high availability setups:
- Use Portainer Business edition
- Configure multiple Portainer instances
- Use external database for Portainer data
- Implement load balancing

## Backup & Restore

### Portainer Data Backup

```bash
# Backup Portainer data volume
docker run --rm -v portainer_data:/data -v $(pwd):/backup busybox tar czf /backup/portainer-backup.tar.gz -C /data .

# Restore Portainer data
docker run --rm -v portainer_data:/data -v $(pwd):/backup busybox tar xzf /backup/portainer-backup.tar.gz -C /data
```

### Stack Configuration Backup

1. **Export Stack**: Use Portainer's export feature in Stack → Editor
2. **Version Control**: Keep docker-compose files in version control
3. **Environment Variables**: Document and backup environment configurations

### Application Data Backup

Don't forget to backup application data:

```bash
# Backup PostgreSQL data
docker-compose exec db pg_dump -U postgres maintenance_dashboard > backup.sql

# Backup media files
docker run --rm -v maintenance-dashboard_media_volume:/data -v $(pwd):/backup busybox tar czf /backup/media-backup.tar.gz -C /data .
```

## Troubleshooting

### Portainer Won't Start

1. **Check Docker Socket**: Ensure Docker socket is accessible
   ```bash
   ls -la /var/run/docker.sock
   ```

2. **Port Conflicts**: Verify ports 9000/9443 are not in use
   ```bash
   netstat -tlnp | grep -E ':(9000|9443)'
   ```

3. **Permission Issues**: Check file permissions
   ```bash
   docker-compose logs portainer
   ```

### Cannot Access Portainer UI

1. **Firewall**: Check firewall settings
2. **Network**: Verify container networking
3. **SSL Issues**: Check SSL certificate configuration in production

### Stack Management Issues

1. **Compose File Errors**: Validate docker-compose syntax
2. **Resource Limits**: Check available system resources
3. **Network Conflicts**: Verify network configurations

### Performance Issues

1. **Resource Allocation**: Monitor container resource usage
2. **Database Performance**: Check database container health
3. **Log Rotation**: Implement log rotation to prevent disk space issues

### Getting Help

1. **Portainer Documentation**: https://docs.portainer.io/
2. **Community Forums**: https://github.com/portainer/portainer/discussions
3. **Project Issues**: Report bugs to the Maintenance Dashboard repository

## Advanced Features (Portainer Business)

For enhanced capabilities, consider Portainer Business Edition:

- **Role-Based Access Control**: Advanced user and team management
- **GitOps**: Git integration for stack management
- **Container Scanning**: Security vulnerability scanning
- **Logging**: Advanced logging and audit capabilities
- **Support**: Professional support and SLA

## Integration with CI/CD

Portainer can be integrated with CI/CD pipelines:

1. **API Access**: Use Portainer API for automation
2. **Webhooks**: Configure webhooks for deployment notifications
3. **Stack Updates**: Automate stack updates via API
4. **Environment Promotion**: Promote configurations between environments

## Conclusion

Portainer significantly simplifies Docker container management for the Maintenance Dashboard. It provides a user-friendly interface for both development and production environments, making it easier to monitor, troubleshoot, and manage the application stack.

For additional features and enterprise-grade capabilities, consider upgrading to Portainer Business Edition based on your organization's needs.