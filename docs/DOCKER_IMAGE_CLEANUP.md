# Docker Image Cleanup Guide

## Problem
When using Portainer's "Pull and Redeploy" feature, Docker creates new images on each deployment without automatically cleaning up old ones. This causes disk space to fill up over time.

## Solution

### 1. Image Tagging (Automatic)
The stack files have been updated to tag images with the git commit hash:
- Development: `maint-dashboard-dev:<commit-hash>`
- Production: `maint-dashboard-prod:<commit-hash>`

This allows Docker to properly track and manage image versions.

### 2. Manual Cleanup Script
Run the cleanup script periodically:

```bash
# Dry run (see what would be removed)
DRY_RUN=true ./scripts/deployment/cleanup_docker_images.sh

# Interactive cleanup (keeps last 3 images)
./scripts/deployment/cleanup_docker_images.sh

# Force cleanup (removes all unused images, keeps last 3)
FORCE=true ./scripts/deployment/cleanup_docker_images.sh

# Keep more images (e.g., last 5)
KEEP_LAST_N=5 ./scripts/deployment/cleanup_docker_images.sh
```

### 3. Automatic Cleanup via Portainer
You can configure Portainer to automatically prune images:

1. Go to **Portainer** → **Settings** → **Docker**
2. Enable **Automatic cleanup of unused images**
3. Set cleanup interval (e.g., daily)

### 4. Manual Docker Commands

#### Remove all unused images:
```bash
docker image prune -a
```

#### Remove only Maintenance Dashboard images (keeps last 3):
```bash
# List images
docker images maint-dashboard*

# Remove specific images (replace IMAGE_ID)
docker rmi <IMAGE_ID>
```

#### System-wide cleanup (removes unused containers, networks, images, and build cache):
```bash
docker system prune -a
```

### 5. Pre-Deployment Cleanup
Add cleanup to your deployment workflow:

```bash
# Before deploying
./scripts/deployment/cleanup_docker_images.sh

# Deploy
# (Portainer pull and redeploy)

# After deploying (optional)
./scripts/deployment/cleanup_docker_images.sh
```

## Best Practices

1. **Keep Last N Images**: Always keep the last 2-3 images for rollback capability
2. **Regular Cleanup**: Run cleanup weekly or monthly depending on deployment frequency
3. **Monitor Disk Space**: Check disk usage regularly: `df -h`
4. **Use Image Tags**: The updated stack files now use commit hash tags for better tracking

## Disk Space Monitoring

Check Docker disk usage:
```bash
docker system df
```

Check specific image sizes:
```bash
docker images maint-dashboard* --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"
```

## Troubleshooting

### "Image is in use" error
If an image can't be removed because it's in use:
1. Stop the container using the image
2. Remove the container
3. Then remove the image

### "Permission denied" error
Run with sudo or as root:
```bash
sudo ./scripts/deployment/cleanup_docker_images.sh
```

### Portainer cleanup not working
- Check Portainer logs for errors
- Verify Docker API access
- Try manual cleanup script instead

