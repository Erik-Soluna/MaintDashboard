# Generated manually for EquipmentCategoryConditionalField model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
        ('equipment', '0003_equipmentcategoryfield_equipmentcustomvalue'),
    ]

    operations = [
        migrations.CreateModel(
            name='EquipmentCategoryConditionalField',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True, help_text='Is this conditional field assignment active?')),
                ('override_label', models.CharField(blank=True, help_text='Override the field label for this category (optional)', max_length=200)),
                ('override_help_text', models.TextField(blank=True, help_text='Override the help text for this category (optional)')),
                ('override_required', models.BooleanField(blank=True, help_text='Override the required setting for this category (optional)', null=True)),
                ('override_default_value', models.TextField(blank=True, help_text='Override the default value for this category (optional)')),
                ('override_sort_order', models.PositiveIntegerField(blank=True, help_text='Override the sort order for this category (optional)', null=True)),
                ('override_field_group', models.CharField(blank=True, help_text='Override the field group for this category (optional)', max_length=100)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='equipmentcategoryconditionalfield_created', to='core.userprofile')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='equipmentcategoryconditionalfield_updated', to='core.userprofile')),
                ('field', models.ForeignKey(help_text='The field to conditionally assign', on_delete=django.db.models.deletion.CASCADE, related_name='conditional_assignments', to='equipment.equipmentcategoryfield')),
                ('source_category', models.ForeignKey(help_text='Equipment category that provides the field', on_delete=django.db.models.deletion.CASCADE, related_name='conditional_field_sources', to='core.equipmentcategory')),
                ('target_category', models.ForeignKey(help_text='Equipment category that receives the field', on_delete=django.db.models.deletion.CASCADE, related_name='conditional_field_targets', to='core.equipmentcategory')),
            ],
            options={
                'verbose_name': 'Equipment Category Conditional Field',
                'verbose_name_plural': 'Equipment Category Conditional Fields',
                'ordering': ['target_category', 'override_sort_order', 'field__sort_order'],
                'unique_together': {('target_category', 'field')},
            },
        ),
        migrations.AddIndex(
            model_name='equipmentcategoryconditionalfield',
            index=models.Index(fields=['source_category', 'target_category'], name='equipment_e_source__a0b8c8_idx'),
        ),
        migrations.AddIndex(
            model_name='equipmentcategoryconditionalfield',
            index=models.Index(fields=['target_category', 'is_active'], name='equipment_e_target__c0d9e0_idx'),
        ),
    ]
