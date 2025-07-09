# Portainer Quick Start Guide

This guide will get you up and running with Portainer for managing your Maintenance Dashboard containers in just a few minutes.

## Prerequisites

- Docker and Docker Compose installed
- Maintenance Dashboard project cloned locally

## Step 1: Start the Stack

Start the complete stack including Portainer:

```bash
# Navigate to your project directory
cd maintenance-dashboard

# Start all services including Portainer
docker-compose up -d

# Verify all services are running
docker-compose ps
```

## Step 2: Access Portainer

Open your web browser and navigate to:
- **Development**: [http://localhost:9000](http://localhost:9000)
- **Production**: [https://localhost:9443](https://localhost:9443)

## Step 3: Initial Setup

### Create Admin User
1. On first visit, you'll see the "Create the first administrator user" screen
2. Enter:
   - **Username**: `admin` (or your preferred username)
   - **Password**: Choose a strong password (minimum 12 characters)
3. Click **Create user**

### Connect to Docker
1. Select **Docker** as the environment type
2. Choose **Local** to manage the local Docker environment
3. Click **Connect**

## Step 4: Explore Your Stack

### View All Containers
1. Click **Containers** in the left sidebar
2. You'll see all running containers:
   - `portainer` - Container management UI
   - `*_web_*` - Django web application
   - `*_db_*` - PostgreSQL database
   - `*_redis_*` - Redis cache
   - `*_celery_*` - Background task worker
   - `*_celery-beat_*` - Task scheduler

### View Stack Details
1. Click **Stacks** in the left sidebar
2. Find your maintenance dashboard stack (usually named after your directory)
3. Click on the stack name to view:
   - Service status and health
   - Resource usage
   - Configuration details

## Step 5: Common Tasks

### View Container Logs
1. Go to **Containers**
2. Click on any container name
3. Click the **Logs** tab
4. Use real-time log streaming and filtering

### Restart a Service
1. From **Containers** or **Stacks** view
2. Click the container name
3. Click **Restart**

### Monitor Resource Usage
1. Click **Dashboard** for overview
2. Click any container for detailed metrics:
   - CPU usage
   - Memory consumption
   - Network I/O
   - Disk usage

### Scale Services
1. Go to **Stacks** → Your stack
2. Find the service to scale (e.g., `web` or `celery`)
3. Adjust replica count
4. Click **Update**

## Step 6: Useful Features

### Quick Actions
- **Container Terminal**: Access container shell via browser
- **File Browser**: Browse container filesystem
- **Inspect**: View detailed container configuration
- **Stats**: Real-time resource monitoring

### Stack Management
- **Update Stack**: Modify docker-compose configuration
- **Duplicate Stack**: Create copies for testing
- **Export Stack**: Backup stack configuration

## Common URLs Quick Reference

| Service | Development URL | Production URL |
|---------|----------------|----------------|
| Maintenance Dashboard | http://localhost:8000 | https://yourdomain.com |
| Portainer | http://localhost:9000 | https://yourdomain.com:9443 |
| PostgreSQL | localhost:5432 | (internal only) |
| Redis | localhost:6379 | (internal only) |

## Troubleshooting

### Portainer Won't Load
```bash
# Check if Portainer is running
docker-compose ps portainer

# View Portainer logs
docker-compose logs portainer

# Restart Portainer
docker-compose restart portainer
```

### Can't See Containers
1. Ensure you selected the correct Docker environment during setup
2. Check that Docker daemon is accessible
3. Verify user has Docker permissions

### Port Conflicts
If port 9000 or 9443 is already in use:
1. Stop conflicting services
2. Or modify ports in `docker-compose.yml`:
   ```yaml
   portainer:
     ports:
       - "9001:9000"  # Change external port
       - "9444:9443"  # Change external port
   ```

## Next Steps

- Read the [complete Portainer documentation](PORTAINER.md)
- Explore Portainer's advanced features
- Set up production environment with SSL
- Configure user access and permissions

## Security Note

For production environments:
- Use HTTPS only (port 9443)
- Set strong passwords
- Configure SSL certificates
- Restrict network access to trusted IPs
- Regular security updates

## Getting Help

- [Portainer Documentation](https://docs.portainer.io/)
- [Maintenance Dashboard Documentation](../README.md)
- [Full Portainer Guide](PORTAINER.md)

---

**🎉 You're now ready to manage your Maintenance Dashboard with Portainer!**

The web interface makes it easy to monitor, troubleshoot, and manage your Docker containers without using the command line.