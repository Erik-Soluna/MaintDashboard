# Generated manually for active items functionality

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0022_remove_playwrightdebuglog'),
    ]

    operations = [
        migrations.AddField(
            model_name='dashboardsettings',
            name='show_active_items',
            field=models.BooleanField(default=True, help_text='Show active items section (in progress and pending)'),
        ),
        migrations.AddField(
            model_name='dashboardsettings',
            name='group_active_by_site',
            field=models.BooleanField(default=True, help_text='Group active items by site'),
        ),
        migrations.AddField(
            model_name='dashboardsettings',
            name='max_active_items_per_site',
            field=models.IntegerField(default=15, help_text='Maximum active items to show per site'),
        ),
        migrations.AddField(
            model_name='dashboardsettings',
            name='max_active_items_total',
            field=models.IntegerField(default=50, help_text='Maximum total active items across all sites'),
        ),
    ]

