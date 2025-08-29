# Portainer Branding System Setup

## Overview

The branding system is now automatically set up when deploying through Portainer, eliminating the need for manual database migrations and setup commands. This document explains how the system works and how to customize it.

## How It Works

### 1. Automatic Setup Process

When a Portainer container starts up, the `docker-entrypoint.sh` script automatically:

1. **Runs Database Migrations**: Ensures all branding system tables exist
2. **Checks Existing Configuration**: Verifies if branding is already set up
3. **Creates Default Branding**: Runs `python manage.py setup_branding --noinput`
4. **Applies Environment Variables**: Customizes branding settings based on environment variables
5. **Logs Progress**: Provides detailed logging throughout the process

### 2. Entrypoint Script Integration

The branding setup is integrated into the main database initialization flow:

```bash
# In docker-entrypoint.sh
if python manage.py init_database; then
    print_success "Database initialization completed successfully!"
    
    # Now set up the branding system
    print_status "Setting up branding system..."
    if setup_branding_system; then
        print_success "Branding system setup completed successfully!"
    else
        print_warning "Branding system setup failed, but continuing..."
    fi
    
    return 0
fi
```

## Environment Variables

### Production Stack (`portainer-stack.yml`)

```yaml
environment:
  # Branding System Configuration
  - BRANDING_AUTO_SETUP=${BRANDING_AUTO_SETUP:-True}
  - BRANDING_SITE_NAME=${BRANDING_SITE_NAME:-Maintenance Dashboard}
  - BRANDING_SITE_TAGLINE=${BRANDING_SITE_TAGLINE:-Professional Maintenance Management System}
  - BRANDING_WINDOW_TITLE_PREFIX=${BRANDING_WINDOW_TITLE_PREFIX:-Maintenance Dashboard}
  - BRANDING_WINDOW_TITLE_SUFFIX=${BRANDING_WINDOW_TITLE_SUFFIX:-ErrorLog.app}
  - BRANDING_HEADER_BRAND_TEXT=${BRANDING_HEADER_BRAND_TEXT:-Maintenance Dashboard}
  - BRANDING_PRIMARY_COLOR=${BRANDING_PRIMARY_COLOR:-#4299e1}
  - BRANDING_SECONDARY_COLOR=${BRANDING_SECONDARY_COLOR:-#2d3748}
  - BRANDING_ACCENT_COLOR=${BRANDING_ACCENT_COLOR:-#3182ce}
```

### Development Stack (`portainer-stack-dev.yml`)

```yaml
environment:
  # Branding System Configuration
  - BRANDING_AUTO_SETUP=True
  - BRANDING_SITE_NAME=Maintenance Dashboard (Dev)
  - BRANDING_SITE_TAGLINE=Development Environment
  - BRANDING_WINDOW_TITLE_PREFIX=Maintenance Dashboard
  - BRANDING_WINDOW_TITLE_SUFFIX=Dev
  - BRANDING_HEADER_BRAND_TEXT=Maintenance Dashboard (Dev)
  - BRANDING_PRIMARY_COLOR=#4299e1
  - BRANDING_SECONDARY_COLOR=#2d3748
  - BRANDING_ACCENT_COLOR=#3182ce
```

## Environment Variable Reference

| Variable | Description | Default Value |
|----------|-------------|---------------|
| `BRANDING_AUTO_SETUP` | Enable/disable automatic branding setup | `True` |
| `BRANDING_SITE_NAME` | Main site name displayed throughout the application | `Maintenance Dashboard` |
| `BRANDING_SITE_TAGLINE` | Subtitle/tagline for the site | `Professional Maintenance Management System` |
| `BRANDING_WINDOW_TITLE_PREFIX` | Text before the page title in browser tabs | `Maintenance Dashboard` |
| `BRANDING_WINDOW_TITLE_SUFFIX` | Text after the page title in browser tabs | `ErrorLog.app` |
| `BRANDING_HEADER_BRAND_TEXT` | Text displayed in the main header | `Maintenance Dashboard` |
| `BRANDING_PRIMARY_COLOR` | Primary brand color (hex) | `#4299e1` |
| `BRANDING_SECONDARY_COLOR` | Secondary brand color (hex) | `#2d3748` |
| `BRANDING_ACCENT_COLOR` | Accent color for highlights (hex) | `#3182ce` |

## Customization

### 1. Modify Environment Variables

To customize branding for your deployment:

1. **Edit the Portainer stack file** (`portainer-stack.yml` or `portainer-stack-dev.yml`)
2. **Update the environment variables** with your desired values
3. **Redeploy the stack** in Portainer

### 2. Example Customization

```yaml
environment:
  - BRANDING_SITE_NAME=Acme Corp Maintenance
  - BRANDING_SITE_TAGLINE=Keeping Your Equipment Running
  - BRANDING_WINDOW_TITLE_PREFIX=Acme Corp
  - BRANDING_WINDOW_TITLE_SUFFIX=Maintenance System
  - BRANDING_HEADER_BRAND_TEXT=Acme Corp Maintenance
  - BRANDING_PRIMARY_COLOR=#e53e3e
  - BRANDING_SECONDARY_COLOR=#2d3748
  - BRANDING_ACCENT_COLOR=#38a169
```

### 3. Post-Deployment Customization

After the initial setup, you can further customize branding through the web interface:

- Navigate to **Settings → Branding**
- Modify site information, colors, and navigation labels
- Create custom CSS rules for specific UI elements
- Upload custom logos and favicons

## Deployment Process

### 1. Initial Deployment

1. **Deploy the Portainer stack** with your desired branding environment variables
2. **The container will automatically**:
   - Create the database and run migrations
   - Set up the branding system with your custom values
   - Start the application with your branding applied

### 2. Redeployment

When redeploying:

1. **Update environment variables** in the Portainer stack if needed
2. **Redeploy the stack**
3. **The branding system will be updated** with new values (if tables exist, it will update existing settings)

### 3. Environment Variable Updates

To change branding without redeploying:

1. **Update environment variables** in Portainer
2. **Restart the web service** container
3. **The branding will be updated** on the next container startup

## Troubleshooting

### 1. Check Container Logs

View the container logs to see the branding setup process:

```bash
# In Portainer or via docker logs
docker logs maintenance_web_prod
```

Look for branding-related messages:
```
[INFO] 🚀 Setting up branding system...
[INFO] Running database migrations...
[SUCCESS] Migrations completed successfully
[INFO] Setting up default branding configuration...
[SUCCESS] Default branding configuration created successfully with custom values
```

### 2. Common Issues

#### Branding Setup Fails
- Check if database migrations completed successfully
- Verify environment variables are properly set
- Check container logs for specific error messages

#### Environment Variables Not Applied
- Ensure environment variables are correctly formatted in the stack file
- Verify the container was restarted after variable changes
- Check that the `BRANDING_AUTO_SETUP` variable is set to `True`

#### Tables Don't Exist
- The system will automatically create tables via migrations
- If migrations fail, check database connectivity and permissions
- Ensure the database user has sufficient privileges

### 3. Manual Setup (Fallback)

If automatic setup fails, you can manually run:

```bash
# Connect to the running container
docker exec -it maintenance_web_prod bash

# Run migrations
python manage.py migrate

# Set up branding
python manage.py setup_branding
```

## Benefits

### 1. **Zero Manual Intervention**
- Branding system is automatically configured on deployment
- No need to remember to run setup commands
- Consistent setup across all environments

### 2. **Environment-Specific Customization**
- Different branding for development vs. production
- Easy customization through environment variables
- Version-controlled branding configuration

### 3. **Robust Error Handling**
- Graceful fallback if branding setup fails
- Detailed logging for troubleshooting
- Non-blocking setup (application continues even if branding fails)

### 4. **Seamless Updates**
- Branding updates on container restart
- No downtime for branding changes
- Easy rollback by changing environment variables

## Future Enhancements

### 1. **Dynamic Branding Updates**
- API endpoints for real-time branding changes
- Webhook integration for external branding management
- A/B testing for different branding configurations

### 2. **Multi-Tenant Branding**
- Support for multiple branding configurations
- Tenant-specific branding based on domain
- Branding inheritance and overrides

### 3. **Branding Templates**
- Pre-built branding themes
- Import/export branding configurations
- Branding marketplace for common industry themes

## Conclusion

The automatic branding system setup in Portainer provides a robust, maintainable solution for deploying branded maintenance dashboards. By leveraging environment variables and automatic initialization, you can ensure consistent branding across all deployments while maintaining the flexibility to customize for different environments and use cases.

For questions or issues, refer to the container logs and the troubleshooting section above.
