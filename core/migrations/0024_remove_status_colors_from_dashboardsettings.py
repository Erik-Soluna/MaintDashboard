# Generated manually - remove status color fields from DashboardSettings
# Status colors are now only in BrandingSettings for consistency

from django.db import migrations


def remove_status_color_fields_if_exist(apps, schema_editor):
    """Safely remove status color fields from DashboardSettings if they exist"""
    db_alias = schema_editor.connection.alias
    
    # Use raw SQL to check and remove columns if they exist
    with schema_editor.connection.cursor() as cursor:
        status_color_fields = [
            'status_color_scheduled',
            'status_color_pending',
            'status_color_in_progress',
            'status_color_cancelled',
            'status_color_completed',
            'status_color_overdue',
        ]
        
        for field_name in status_color_fields:
            # Check if column exists
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='core_dashboardsettings' 
                AND column_name=%s;
            """, [field_name])
            
            if cursor.fetchone() is not None:
                # Column exists, remove it
                cursor.execute(f"""
                    ALTER TABLE core_dashboardsettings 
                    DROP COLUMN {field_name};
                """)


def reverse_migration(apps, schema_editor):
    """Re-add the fields if needed (for rollback)"""
    # This is a no-op since we're removing fields that may not have existed
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0023_dashboardsettings_add_active_items_fields'),
    ]

    operations = [
        # Use SeparateDatabaseAndState to handle fields that may not exist in migration state
        migrations.SeparateDatabaseAndState(
            # Database operations: safely remove columns if they exist in the database
            database_operations=[
                migrations.RunPython(remove_status_color_fields_if_exist, reverse_migration),
            ],
            # State operations: Empty because these fields were never added via migration
            # The fields don't exist in Django's migration state, so we can't remove them
            # Django will automatically sync the state when it detects the model change
            state_operations=[
                # No state operations needed - fields were never in migration state
            ],
        ),
    ]

