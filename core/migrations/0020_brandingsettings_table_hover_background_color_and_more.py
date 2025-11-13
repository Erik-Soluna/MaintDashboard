# Generated manually to add table hover colors to BrandingSettings

from django.db import migrations, models


def add_table_hover_fields_if_not_exists(apps, schema_editor):
    """Safely add table hover fields if they don't exist"""
    db_alias = schema_editor.connection.alias
    
    # Use raw SQL to check and add columns if they don't exist
    with schema_editor.connection.cursor() as cursor:
        # Check if column exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='core_brandingsettings' 
            AND column_name='table_hover_background_color';
        """)
        bg_exists = cursor.fetchone() is not None
        
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='core_brandingsettings' 
            AND column_name='table_hover_text_color';
        """)
        text_exists = cursor.fetchone() is not None
        
        # Add columns if they don't exist
        if not bg_exists:
            cursor.execute("""
                ALTER TABLE core_brandingsettings 
                ADD COLUMN table_hover_background_color VARCHAR(7) DEFAULT '#374151';
            """)
        
        if not text_exists:
            cursor.execute("""
                ALTER TABLE core_brandingsettings 
                ADD COLUMN table_hover_text_color VARCHAR(7) DEFAULT '#ffffff';
            """)


def reverse_migration(apps, schema_editor):
    """Remove the fields if needed"""
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("""
            ALTER TABLE core_brandingsettings 
            DROP COLUMN IF EXISTS table_hover_background_color;
        """)
        cursor.execute("""
            ALTER TABLE core_brandingsettings 
            DROP COLUMN IF EXISTS table_hover_text_color;
        """)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0019_add_dashboard_settings'),
    ]

    operations = [
        migrations.RunPython(add_table_hover_fields_if_not_exists, reverse_migration),
    ]

