# Portainer Git Repository Deployment

Since you're deploying from a Git repository in Portainer, here's the streamlined deployment process.

## ✅ Problem Fixed

The Portainer service has been removed from all stack files to prevent conflicts with your existing Portainer instance.

## Quick Deployment Steps

### 1. In Portainer Interface:

1. **Go to Stacks → Add Stack**
2. **Choose "Git Repository" method**
3. **Fill in the repository details:**
   - Repository URL: `[your-git-repository-url]`
   - Reference: `main` (or your branch name)
   - Compose file path: `portainer-stack.yml`

4. **Deploy the stack**

### 2. Stack Configuration

The `portainer-stack.yml` file includes:
- ✅ **PostgreSQL database** with persistent storage
- ✅ **Redis cache** for background tasks  
- ✅ **Django web application** with auto-migration
- ✅ **Celery worker** for background processing
- ✅ **Celery beat** for scheduled tasks
- ✅ **Health checks** for all services
- ✅ **Restart policies** for reliability

### 3. Ports Exposed:
- **8000** - Django application (main app)
- **5432** - PostgreSQL database  
- **6379** - Redis cache

### 4. Post-Deployment:

1. **Wait for all services to be healthy** (check in Portainer containers view)

2. **Create superuser account:**
   - Go to Containers → Find "web" container → Console
   - Run: `python manage.py createsuperuser`

3. **Access your application:**
   - Main app: http://localhost:8000
   - Admin: http://localhost:8000/admin/

## Environment Variables (Optional Customization)

You can customize these in Portainer's stack editor before deployment:

```yaml
environment:
  - DEBUG=True                    # Set to False for production
  - SECRET_KEY=your-secret-key    # Use a secure key for production
  - DB_PASSWORD=postgres          # Change for better security
  - ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0,yourdomain.com
```

## Troubleshooting

### If deployment still fails:

1. **Check repository access:** Make sure Portainer can access your Git repository
2. **Verify file path:** Ensure `portainer-stack.yml` exists in the repository root
3. **Check ports:** Ensure ports 8000, 5432, 6379 are available
4. **View logs:** Go to Containers → Select container → Logs tab

### Common issues:

- **"No such file"**: Verify the compose file path in Git repository settings
- **Port conflicts**: Change ports in the stack file if they're already in use
- **Build context errors**: The stack now builds from the Git context, so this should be resolved

## Production Notes

For production deployment:
- Change `DEBUG=False`
- Use a secure `SECRET_KEY`
- Configure proper `ALLOWED_HOSTS`
- Use strong database passwords
- Consider adding SSL/HTTPS with nginx

Your application should now deploy successfully from the Git repository without any Portainer conflicts!