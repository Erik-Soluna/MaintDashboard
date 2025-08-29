# Generated manually for breadcrumb controls

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_userprofile_timezone_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='brandingsettings',
            name='breadcrumb_enabled',
            field=models.BooleanField(default=True, help_text='Whether to show breadcrumbs globally'),
        ),
        migrations.AddField(
            model_name='brandingsettings',
            name='breadcrumb_home_text',
            field=models.CharField(default='Home', help_text='Text for the home breadcrumb link', max_length=50),
        ),
        migrations.AddField(
            model_name='brandingsettings',
            name='breadcrumb_separator',
            field=models.CharField(default='>', help_text='Separator between breadcrumb items', max_length=10),
        ),
        migrations.AddField(
            model_name='brandingsettings',
            name='breadcrumb_link_color',
            field=models.CharField(default='#4299e1', help_text='Breadcrumb link color in hex format (#RRGGBB)', max_length=7),
        ),
        migrations.AddField(
            model_name='brandingsettings',
            name='breadcrumb_text_color',
            field=models.CharField(default='#a0aec0', help_text='Breadcrumb text color in hex format (#RRGGBB)', max_length=7),
        ),
        migrations.AddField(
            model_name='brandingsettings',
            name='breadcrumb_separator_color',
            field=models.CharField(default='#a0aec0', help_text='Breadcrumb separator color in hex format (#RRGGBB)', max_length=7),
        ),
    ]
