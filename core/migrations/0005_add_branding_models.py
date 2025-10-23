# Generated manually for branding functionality

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_add_more_maintenance_categories'),
    ]

    operations = [
        migrations.CreateModel(
            name='BrandingSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('site_name', models.CharField(default='Maintenance Dashboard', help_text='Main website name displayed in header', max_length=200)),
                ('site_tagline', models.CharField(blank=True, help_text='Optional tagline below the site name', max_length=300)),
                ('window_title_prefix', models.CharField(blank=True, default='', help_text='Text to prepend to all page titles', max_length=100)),
                ('window_title_suffix', models.CharField(blank=True, default='', help_text='Text to append to all page titles', max_length=100)),
                ('header_brand_text', models.CharField(default='Maintenance Dashboard', help_text='Text displayed next to logo in header', max_length=200)),
                ('navigation_overview_label', models.CharField(default='Overview', help_text='Label for Overview navigation item', max_length=50)),
                ('navigation_equipment_label', models.CharField(default='Equipment', help_text='Label for Equipment navigation item', max_length=50)),
                ('navigation_maintenance_label', models.CharField(default='Maintenance', help_text='Label for Maintenance navigation item', max_length=50)),
                ('navigation_calendar_label', models.CharField(default='Calendar', help_text='Label for Calendar navigation item', max_length=50)),
                ('navigation_map_label', models.CharField(default='Map', help_text='Label for Map navigation item', max_length=50)),
                ('navigation_settings_label', models.CharField(default='Settings', help_text='Label for Settings navigation item', max_length=50)),
                ('navigation_debug_label', models.CharField(default='Debug', help_text='Label for Debug navigation item', max_length=50)),
                ('footer_copyright_text', models.CharField(default='© 2025 Maintenance Dashboard. All rights reserved.', help_text='Copyright text in footer', max_length=200)),
                ('footer_powered_by_text', models.CharField(default='Powered by Django', help_text='Text displayed in footer', max_length=100)),
                ('primary_color', models.CharField(default='#4299e1', help_text='Primary color in hex format (#RRGGBB)', max_length=7)),
                ('secondary_color', models.CharField(default='#2d3748', help_text='Secondary color in hex format (#RRGGBB)', max_length=7)),
                ('accent_color', models.CharField(default='#3182ce', help_text='Accent color in hex format (#RRGGBB)', max_length=7)),
                ('is_active', models.BooleanField(default=True, help_text='Whether these branding settings are currently active')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('logo', models.ForeignKey(blank=True, help_text='Main site logo', null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.logo')),
            ],
            options={
                'verbose_name': 'Branding Settings',
                'verbose_name_plural': 'Branding Settings',
            },
        ),
        migrations.CreateModel(
            name='CSSCustomization',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Name for this CSS customization', max_length=100)),
                ('item_type', models.CharField(choices=[('header', 'Header'), ('navigation', 'Navigation'), ('dashboard', 'Dashboard'), ('equipment', 'Equipment'), ('maintenance', 'Maintenance'), ('calendar', 'Calendar'), ('map', 'Map'), ('settings', 'Settings'), ('forms', 'Forms'), ('tables', 'Tables'), ('buttons', 'Buttons'), ('cards', 'Cards'), ('modals', 'Modals'), ('alerts', 'Alerts'), ('breadcrumbs', 'Breadcrumbs'), ('footer', 'Footer'), ('global', 'Global')], help_text='Type of item this CSS affects', max_length=20)),
                ('description', models.TextField(blank=True, help_text='Describe what this CSS customization does')),
                ('css_code', models.TextField(help_text='CSS code (without <style> tags)')),
                ('is_active', models.BooleanField(default=True, help_text='Whether this CSS customization is currently active')),
                ('priority', models.IntegerField(default=0, help_text='Higher priority CSS loads later (overrides earlier CSS)')),
                ('order', models.IntegerField(default=0, help_text='Order within the same priority level')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='auth.user')),
            ],
            options={
                'verbose_name': 'CSS Customization',
                'verbose_name_plural': 'CSS Customizations',
                'ordering': ['-priority', 'order', 'name'],
            },
        ),
        migrations.AddField(
            model_name='logo',
            name='favicon',
            field=models.ImageField(blank=True, help_text='Website favicon (16x16, 32x32, or 48x48 recommended)', upload_to='favicons/'),
        ),
    ]
