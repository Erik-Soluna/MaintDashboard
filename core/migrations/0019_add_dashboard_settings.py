# Generated manually for dashboard settings functionality

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0018_alter_logo_options_remove_logo_favicon_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='DashboardSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('show_urgent_items', models.BooleanField(default=True, help_text='Show urgent items section')),
                ('show_upcoming_items', models.BooleanField(default=True, help_text='Show upcoming items section')),
                ('show_site_status', models.BooleanField(default=True, help_text='Show site status cards')),
                ('show_kpi_cards', models.BooleanField(default=True, help_text='Show KPI cards at top')),
                ('show_overview_data', models.BooleanField(default=True, help_text='Show overview data (pods/sites)')),
                ('group_urgent_by_site', models.BooleanField(default=True, help_text='Group urgent items by site')),
                ('group_upcoming_by_site', models.BooleanField(default=True, help_text='Group upcoming items by site')),
                ('max_urgent_items_per_site', models.IntegerField(default=15, help_text='Maximum urgent items to show per site')),
                ('max_upcoming_items_per_site', models.IntegerField(default=15, help_text='Maximum upcoming items to show per site')),
                ('max_urgent_items_total', models.IntegerField(default=50, help_text='Maximum total urgent items across all sites')),
                ('max_upcoming_items_total', models.IntegerField(default=50, help_text='Maximum total upcoming items across all sites')),
                ('urgent_days_ahead', models.IntegerField(default=7, help_text='Number of days ahead to consider items as urgent')),
                ('upcoming_days_ahead', models.IntegerField(default=30, help_text='Number of days ahead to consider items as upcoming')),
                ('is_active', models.BooleanField(default=True, help_text='Whether these dashboard settings are currently active')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Dashboard Settings',
                'verbose_name_plural': 'Dashboard Settings',
            },
        ),
    ]

