# Portainer Stack Deployment Guide

This guide provides multiple solutions for deploying the maintenance dashboard via Portainer stacks.

## Problem

The error `failed to read dockerfile: open Dockerfile: no such file or directory` occurs because Portainer can't access local files when you paste Docker Compose content directly into the stack editor.

## Solutions

### Solution 1: Pre-build Image (Recommended - Easiest)

This is the fastest way to get running:

1. **Build the image locally:**
```bash
chmod +x build-and-deploy.sh
./build-and-deploy.sh
```

2. **Deploy in Portainer:**
   - Go to Portainer → Stacks → Add Stack
   - Give it a name (e.g., "maintenance-dashboard")
   - Copy and paste the content from `portainer-stack-with-image.yml`
   - Click "Deploy the stack"

3. **Access your application:**
   - Application: http://localhost:8000
   - Database will be automatically created and migrated

### Solution 2: Git Repository Deployment

If your code is in a Git repository that Portainer can access:

1. **In Portainer:**
   - Go to Stacks → Add Stack
   - Choose "Git Repository" option
   - Enter your repository URL
   - Set the compose file path to `portainer-stack.yml`
   - Deploy

### Solution 3: Docker Hub Registry

For production or remote deployment:

1. **Build and push to Docker Hub:**
```bash
# Build image
docker build -t maintenance-dashboard:latest .

# Tag for Docker Hub (replace 'yourusername')
docker tag maintenance-dashboard:latest yourusername/maintenance-dashboard:latest

# Push to Docker Hub
docker push yourusername/maintenance-dashboard:latest
```

2. **Update the stack file:**
   - Edit `portainer-stack-with-image.yml`
   - Replace `maintenance-dashboard:latest` with `yourusername/maintenance-dashboard:latest`

3. **Deploy in Portainer:**
   - Use the updated stack file content

### Solution 4: Local Volume Mount (Development Only)

For development with live code changes:

```yaml
# Add this to web, celery, and celery-beat services in your stack:
volumes:
  - /path/to/your/project:/app  # Mount your project directory
```

⚠️ **Warning:** This requires the exact same file path to exist on the Portainer host machine.

## Stack Configuration

### Environment Variables

You can customize these in the Portainer stack editor:

```yaml
environment:
  - DEBUG=True                    # Set to False for production
  - SECRET_KEY=your-secret-key    # Change for production
  - DB_PASSWORD=your-db-password  # Change for production
  - ALLOWED_HOSTS=localhost,127.0.0.1,yourdomain.com
```

### Ports

The stack exposes these ports:
- `8000` - Django application
- `5432` - PostgreSQL database
- `6379` - Redis cache

Make sure these ports are available on your host.

### Persistent Data

The following volumes ensure data persistence:
- `postgres_data` - Database data
- `static_volume` - Static files
- `media_volume` - Uploaded media files

## Post-Deployment Steps

1. **Create superuser:**
```bash
# In Portainer, go to Containers → web container → Console
python manage.py createsuperuser
```

2. **Access admin interface:**
   - Go to http://localhost:8000/admin/
   - Use the superuser credentials you just created

## Troubleshooting

### Common Issues

1. **Port conflicts:**
   - Change ports in the stack file if 8000, 5432, or 6379 are in use

2. **Image not found:**
   - Make sure you've built the image locally with the correct tag
   - Or use a public registry image

3. **Database connection errors:**
   - Wait a few moments for PostgreSQL to fully start
   - Check that the database container is healthy

4. **Static files not loading:**
   - The first startup may take longer as static files are collected
   - Check the web container logs

### Viewing Logs

In Portainer:
1. Go to Containers
2. Click on the container name
3. Go to "Logs" tab
4. View real-time logs

## Production Considerations

For production deployment:

1. **Security:**
   - Change `SECRET_KEY` to a secure random value
   - Set `DEBUG=False`
   - Use strong database passwords
   - Configure proper `ALLOWED_HOSTS`

2. **SSL/HTTPS:**
   - Add nginx container with SSL certificates
   - Update Portainer to use HTTPS

3. **Backups:**
   - Set up regular database backups
   - Backup persistent volumes

4. **Monitoring:**
   - Use Portainer's monitoring features
   - Set up health check alerts

## Next Steps

After successful deployment:
- Access your application at http://localhost:8000
- Log into admin at http://localhost:8000/admin/
- Start adding equipment and maintenance records
- Monitor your stack through Portainer's web interface