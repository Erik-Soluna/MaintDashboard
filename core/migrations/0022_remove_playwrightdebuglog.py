# Generated manually to remove PlaywrightDebugLog model

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0020_brandingsettings_table_hover_background_color_and_more'),
    ]
    
    # Note: This migration removes the PlaywrightDebugLog model
    # The table may have been created by migration 0006_playwrightdebuglog
    # This migration safely drops the table if it exists using SeparateDatabaseAndState
    # to handle both Django's state and the actual database

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    # Drop the table if it exists (safe for production)
                    sql="DROP TABLE IF EXISTS core_playwrightdebuglog CASCADE;",
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
            state_operations=[
                migrations.DeleteModel(
                    name='PlaywrightDebugLog',
                ),
            ],
        ),
    ]

