# Generated manually for activity title template

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0024_remove_status_colors_from_dashboardsettings'),
    ]

    operations = [
        migrations.AddField(
            model_name='dashboardsettings',
            name='activity_title_template',
            field=models.CharField(
                default='{Activity_Type} - {Equipment}',
                help_text='Template for auto-generating maintenance activity titles. Available variables: {Activity_Type}, {Equipment}, {Date}, {Priority}, {Status}',
                max_length=200
            ),
        ),
    ]

