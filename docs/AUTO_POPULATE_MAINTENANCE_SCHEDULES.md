# Auto-Population of Maintenance Schedules

This document explains how the maintenance dashboard automatically creates maintenance schedules when activity types are created or modified.

## Overview

The system automatically creates maintenance schedules in the following scenarios:

1. **New Activity Type Created**: When a new `MaintenanceActivityType` is created, schedules are automatically created for all equipment in the applicable equipment categories.

2. **Activity Type Modified**: When an existing activity type is modified (e.g., frequency changes, applicable categories updated), existing schedules are updated and new schedules are created for newly applicable equipment.

3. **New Equipment Added**: When new equipment is added to a category that has applicable activity types, schedules are automatically created for that equipment.

## How It Works

### Automatic Schedule Creation

The system uses Django signals to automatically trigger schedule creation:

- **`create_maintenance_schedules_for_activity_type`**: Triggered when a new activity type is created
- **`update_maintenance_schedules_for_activity_type`**: Triggered when an existing activity type is modified
- **`create_maintenance_schedules_for_equipment`**: Triggered when new equipment is added

### Frequency Mapping

The system automatically maps `frequency_days` to human-readable frequency choices:

| Days | Frequency Choice |
|------|------------------|
| 1    | Daily           |
| 7    | Weekly          |
| 30   | Monthly         |
| 90   | Quarterly       |
| 180  | Semi-Annual     |
| 365  | Annual          |
| Other| Custom          |

### Schedule Properties

Each automatically created schedule includes:

- **Equipment**: The specific equipment item
- **Activity Type**: The maintenance activity type
- **Frequency**: Mapped from frequency_days
- **Frequency Days**: Exact number of days from activity type
- **Start Date**: Today's date
- **Auto Generate**: Enabled by default
- **Advance Notice**: 7 days by default
- **Active**: Enabled by default

## Manual Schedule Creation

### Management Command

Use the `create_maintenance_schedules` command to manually create schedules for existing data:

```bash
# Create schedules for all activity types and equipment
python manage.py create_maintenance_schedules

# Create schedules for a specific activity type
python manage.py create_maintenance_schedules --activity-type "T-A-1"

# Create schedules for a specific equipment category
python manage.py create_maintenance_schedules --equipment-category "Transformers"

# Dry run to see what would be created
python manage.py create_maintenance_schedules --dry-run

# Force creation even if schedules exist
python manage.py create_maintenance_schedules --force
```

### Command Options

- **`--activity-type`**: Process only a specific activity type
- **`--equipment-category`**: Process only a specific equipment category
- **`--dry-run`**: Show what would be created without making changes
- **`--force`**: Update existing schedules instead of skipping them

## Configuration

### Activity Type Setup

To enable auto-population for an activity type:

1. Set `is_active = True`
2. Select applicable equipment categories in `applicable_equipment_categories`
3. Set `frequency_days` to the desired interval

### Equipment Setup

To enable auto-population for equipment:

1. Set `is_active = True`
2. Assign the equipment to a category that has applicable activity types

## Troubleshooting

### Common Issues

1. **Schedules Not Created**: Check that both activity type and equipment are active
2. **Wrong Frequency**: Verify `frequency_days` value in activity type
3. **Missing Equipment**: Ensure equipment is assigned to the correct category

### Debugging

Enable debug logging to see detailed information about schedule creation:

```python
# In settings.py
LOGGING = {
    'loggers': {
        'maintenance.signals': {
            'level': 'DEBUG',
            'handlers': ['console'],
        },
    },
}
```

### Manual Verification

Check existing schedules in the Django admin or use the management command with `--dry-run` to see what would be created.

## Best Practices

1. **Plan Categories**: Organize equipment into logical categories before creating activity types
2. **Set Frequencies**: Use standard frequency values (1, 7, 30, 90, 180, 365) when possible
3. **Test First**: Use `--dry-run` when running the management command on production data
4. **Monitor Logs**: Check logs for any errors during automatic schedule creation

## Future Enhancements

Potential improvements to consider:

- **Bulk Operations**: Add admin actions for bulk schedule creation
- **Template System**: Allow activity types to inherit from templates
- **Conditional Logic**: Add rules for when schedules should/shouldn't be created
- **Notification System**: Alert administrators when schedules are automatically created
