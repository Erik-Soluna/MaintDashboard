# Generated manually for timezone support

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('maintenance', '0004_make_maintenanceactivity_datetimes_aware'),
    ]

    operations = [
        migrations.AddField(
            model_name='maintenanceactivity',
            name='timezone',
            field=models.CharField(
                choices=[
                    ('UTC', 'UTC'),
                    ('America/New_York', 'Eastern Time (ET)'),
                    ('America/Chicago', 'Central Time (CT)'),
                    ('America/Denver', 'Mountain Time (MT)'),
                    ('America/Los_Angeles', 'Pacific Time (PT)'),
                    ('America/Anchorage', 'Alaska Time (AKT)'),
                    ('Pacific/Honolulu', 'Hawaii Time (HST)'),
                    ('Europe/London', 'London (GMT)'),
                    ('Europe/Paris', 'Paris (CET)'),
                    ('Asia/Tokyo', 'Tokyo (JST)'),
                    ('Australia/Sydney', 'Sydney (AEST)'),
                ],
                default='America/Chicago',
                help_text='Timezone for the scheduled maintenance times',
                max_length=50,
            ),
        ),
    ]
