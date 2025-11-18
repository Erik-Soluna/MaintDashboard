# Generated manually - remove status color fields from DashboardSettings
# Status colors are now only in BrandingSettings for consistency

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0023_dashboardsettings_add_active_items_fields'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='dashboardsettings',
            name='status_color_scheduled',
        ),
        migrations.RemoveField(
            model_name='dashboardsettings',
            name='status_color_pending',
        ),
        migrations.RemoveField(
            model_name='dashboardsettings',
            name='status_color_in_progress',
        ),
        migrations.RemoveField(
            model_name='dashboardsettings',
            name='status_color_cancelled',
        ),
        migrations.RemoveField(
            model_name='dashboardsettings',
            name='status_color_completed',
        ),
        migrations.RemoveField(
            model_name='dashboardsettings',
            name='status_color_overdue',
        ),
    ]

