# Generated manually to add status color fields to BrandingSettings

from django.db import migrations, models


def add_status_color_fields_if_not_exists(apps, schema_editor):
    """Safely add status color fields if they don't exist"""
    db_alias = schema_editor.connection.alias
    
    # Use raw SQL to check and add columns if they don't exist
    with schema_editor.connection.cursor() as cursor:
        status_color_fields = [
            ('status_color_scheduled', '#808080'),
            ('status_color_pending', '#4299e1'),
            ('status_color_in_progress', '#ed8936'),
            ('status_color_cancelled', '#000000'),
            ('status_color_completed', '#48bb78'),
            ('status_color_overdue', '#f56565'),
        ]
        
        for field_name, default_value in status_color_fields:
            # Check if column exists
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='core_brandingsettings' 
                AND column_name=%s;
            """, [field_name])
            
            if cursor.fetchone() is None:
                # Add column if it doesn't exist
                cursor.execute(f"""
                    ALTER TABLE core_brandingsettings 
                    ADD COLUMN {field_name} VARCHAR(7) DEFAULT %s;
                """, [default_value])


def reverse_migration(apps, schema_editor):
    """Remove the fields if needed"""
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
            cursor.execute(f"""
                ALTER TABLE core_brandingsettings 
                DROP COLUMN IF EXISTS {field_name};
            """)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0025_dashboardsettings_add_activity_title_template'),
    ]

    operations = [
        # Use SeparateDatabaseAndState to handle existing columns
        migrations.SeparateDatabaseAndState(
            # Database operations: safely add columns if they don't exist
            database_operations=[
                migrations.RunPython(add_status_color_fields_if_not_exists, reverse_migration),
            ],
            # State operations: tell Django these fields exist in the model
            state_operations=[
                migrations.AddField(
                    model_name='brandingsettings',
                    name='status_color_scheduled',
                    field=models.CharField(default='#808080', help_text='Scheduled status color', max_length=7),
                ),
                migrations.AddField(
                    model_name='brandingsettings',
                    name='status_color_pending',
                    field=models.CharField(default='#4299e1', help_text='Pending status color', max_length=7),
                ),
                migrations.AddField(
                    model_name='brandingsettings',
                    name='status_color_in_progress',
                    field=models.CharField(default='#ed8936', help_text='In Progress status color', max_length=7),
                ),
                migrations.AddField(
                    model_name='brandingsettings',
                    name='status_color_cancelled',
                    field=models.CharField(default='#000000', help_text='Cancelled status color', max_length=7),
                ),
                migrations.AddField(
                    model_name='brandingsettings',
                    name='status_color_completed',
                    field=models.CharField(default='#48bb78', help_text='Completed status color', max_length=7),
                ),
                migrations.AddField(
                    model_name='brandingsettings',
                    name='status_color_overdue',
                    field=models.CharField(default='#f56565', help_text='Overdue status color', max_length=7),
                ),
            ],
        ),
    ]

