# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0026_add_status_colors_to_brandingsettings'),
    ]

    operations = [
        migrations.AddField(
            model_name='dashboardsettings',
            name='urgent_statuses',
            field=models.JSONField(default=list, help_text='Statuses to show in Urgent Items section. Options: scheduled, pending, in_progress, completed, cancelled, overdue'),
        ),
        migrations.AddField(
            model_name='dashboardsettings',
            name='upcoming_statuses',
            field=models.JSONField(default=list, help_text='Statuses to show in Upcoming Items section. Options: scheduled, pending, in_progress, completed, cancelled, overdue'),
        ),
        migrations.AddField(
            model_name='dashboardsettings',
            name='active_statuses',
            field=models.JSONField(default=list, help_text='Statuses to show in Active Items section. Options: scheduled, pending, in_progress, completed, cancelled, overdue'),
        ),
    ]

