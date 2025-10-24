# Migration Conflict Resolution Guide

This guide explains how to resolve Django migration conflicts in the Maintenance Dashboard application, particularly for the conflicting migrations between `core` and `maintenance` apps.

## Overview

The Maintenance Dashboard has experienced migration conflicts due to parallel development on different branches, resulting in multiple leaf nodes in the migration graph:

- **Core App**: Conflicting migrations `0005_add_branding_models` and `0012_add_breadcrumb_controls`
- **Maintenance App**: Conflicting migrations `0002_add_timeline_entry_types` and `0006_globalschedule_scheduleoverride_and_more`

## Automatic Resolution (Recommended)

### 1. Portainer Stack Deployment

The updated `portainer-stack-dev.yml` now includes automatic migration conflict resolution:

```yaml
environment:
  # Migration Conflict Resolution
  - MIGRATION_CONFLICT_RESOLUTION=True
  - AUTO_MERGE_MIGRATIONS=True
  - FORCE_MIGRATION_MERGE=False
```

When you deploy this stack to your remote dev server, the container will automatically:

1. Detect migration conflicts
2. Attempt to merge conflicting migrations using `python manage.py makemigrations --merge`
3. Apply the merged migrations
4. Continue with branding system setup

### 2. Docker Entrypoint Integration

The `docker-entrypoint.sh` script has been enhanced to:

- Check for migration conflicts before branding system setup
- Automatically resolve conflicts using multiple detection methods
- Provide detailed logging of the resolution process
- Continue with normal initialization even if conflicts exist

## Manual Resolution

If automatic resolution fails, you can manually resolve conflicts on your remote dev server:

### Option 1: Using the Resolution Script

1. SSH into your remote dev server
2. Navigate to the container or mount the script
3. Run the comprehensive resolution script:

```bash
# Make the script executable
chmod +x scripts/deployment/resolve-migration-conflicts.sh

# Run the script
./scripts/deployment/resolve-migration-conflicts.sh
```

This script will:
- Show current migration status
- Detect conflicts automatically
- Try multiple resolution strategies
- Provide detailed feedback

### Option 2: Manual Django Commands

1. Access the Django container:
```bash
docker exec -it <container_name> bash
```

2. Check migration status:
```bash
python manage.py showmigrations --list
python manage.py showmigrations core
python manage.py showmigrations maintenance
```

3. Merge conflicting migrations:
```bash
python manage.py makemigrations --merge
```

4. Apply merged migrations:
```bash
python manage.py migrate
```

5. Verify resolution:
```bash
python manage.py migrate --plan
```

## Resolution Strategies

### Strategy 1: Automatic Merge (Recommended)
- Uses Django's built-in `makemigrations --merge` command
- Creates a new migration that combines conflicting paths
- Safest approach for most conflict scenarios

### Strategy 2: Fake Application
- Marks problematic migrations as applied without running them
- Useful when migrations are already applied to the database
- Less safe but effective for certain scenarios

### Strategy 3: Forced Resolution
- Resets migration state and recreates from scratch
- Most destructive approach
- Use only as a last resort

## Environment Variables

The following environment variables control migration conflict resolution:

| Variable | Default | Description |
|----------|---------|-------------|
| `MIGRATION_CONFLICT_RESOLUTION` | `False` | Enable/disable automatic conflict resolution |
| `AUTO_MERGE_MIGRATIONS` | `True` | Enable automatic migration merging |
| `FORCE_MIGRATION_MERGE` | `False` | Enable forced resolution strategies |

## Troubleshooting

### Common Issues

1. **Permission Denied**: Ensure the script has execute permissions
2. **Database Connection**: Verify database connectivity before running migrations
3. **Migration State Mismatch**: Check if migrations are already applied to the database

### Debugging

Enable verbose logging by setting:
```bash
export DJANGO_DEBUG=True
export PYTHONPATH=/app:$PYTHONPATH
```

### Logs

Check container logs for detailed migration information:
```bash
docker logs <container_name> | grep -i migration
```

## Best Practices

1. **Always backup your database** before resolving migration conflicts
2. **Test resolution in development** before applying to production
3. **Use the automatic resolution** when possible
4. **Monitor logs** during the resolution process
5. **Verify resolution** by running health checks

## Recovery

If resolution fails and breaks the application:

1. **Restore from backup** if available
2. **Check migration state** in the database
3. **Review Django migration history** table
4. **Consider rolling back** to a known good state

## Support

For persistent migration issues:

1. Check the [Django migration documentation](https://docs.djangoproject.com/en/stable/topics/migrations/)
2. Review the specific migration files for conflicts
3. Consider squashing migrations for complex scenarios
4. Contact the development team with detailed error logs

## Related Files

- `portainer-stack-dev.yml` - Updated stack configuration
- `scripts/deployment/docker-entrypoint.sh` - Enhanced entrypoint script
- `scripts/deployment/resolve-migration-conflicts.sh` - Manual resolution script
- `fix_migration_conflicts.py` - Python-based resolution script
