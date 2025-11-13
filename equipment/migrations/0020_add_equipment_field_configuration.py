# Generated manually for equipment field configuration

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('equipment', '0005_rename_equipment_e_source__a0b8c8_idx_equipment_e_source__76e455_idx_and_more'),
        ('core', '0019_add_dashboard_settings'),
    ]

    operations = [
        migrations.CreateModel(
            name='EquipmentFieldConfiguration',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('field_name', models.CharField(help_text='Field identifier (e.g., \'name\', \'manufacturer\', \'power_ratings\', or \'custom_oil_type\')', max_length=100, unique=True)),
                ('display_label', models.CharField(blank=True, help_text='Custom display label (leave blank to use default)', max_length=200)),
                ('field_group', models.CharField(choices=[('basic', 'Basic Information'), ('technical', 'Technical Specifications'), ('hidden', 'Hidden')], default='basic', help_text='Which section to display this field in', max_length=20)),
                ('sort_order', models.PositiveIntegerField(default=0, help_text='Order within the group (lower numbers appear first)')),
                ('is_visible', models.BooleanField(default=True, help_text='Whether this field should be displayed')),
                ('is_custom_field', models.BooleanField(default=False, help_text='Whether this is a custom category field')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('category', models.ForeignKey(blank=True, help_text='Category this field belongs to (for custom fields only)', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='field_configurations', to='core.equipmentcategory')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='equipmentfieldconfiguration_created', to='auth.user')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='equipmentfieldconfiguration_updated', to='auth.user')),
            ],
            options={
                'verbose_name': 'Equipment Field Configuration',
                'verbose_name_plural': 'Equipment Field Configurations',
                'ordering': ['field_group', 'sort_order', 'field_name'],
            },
        ),
        migrations.AddIndex(
            model_name='equipmentfieldconfiguration',
            index=models.Index(fields=['field_group', 'sort_order'], name='equipment_e_field_g_7a8b2a_idx'),
        ),
        migrations.AddIndex(
            model_name='equipmentfieldconfiguration',
            index=models.Index(fields=['is_visible', 'field_group'], name='equipment_e_is_visi_8c9d3e_idx'),
        ),
    ]

