# Hand-written: add only the facility-map layout columns to Equipment.
# (makemigrations wanted to bundle the un-migrated EquipmentIssue/IssueTag
# models into this file; those tables already exist in dev/prod, so creating
# them here would fail. That drift is tracked separately — this migration is
# deliberately limited to the four new nullable layout columns.)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('equipment', '0020_add_equipment_field_configuration'),
    ]

    operations = [
        migrations.AddField(
            model_name='equipment',
            name='layout_x',
            field=models.FloatField(blank=True, help_text='Facility-map X (site canvas units)', null=True),
        ),
        migrations.AddField(
            model_name='equipment',
            name='layout_y',
            field=models.FloatField(blank=True, help_text='Facility-map Y (site canvas units)', null=True),
        ),
        migrations.AddField(
            model_name='equipment',
            name='layout_width',
            field=models.FloatField(blank=True, help_text='Facility-map box width (site canvas units)', null=True),
        ),
        migrations.AddField(
            model_name='equipment',
            name='layout_height',
            field=models.FloatField(blank=True, help_text='Facility-map box height (site canvas units)', null=True),
        ),
    ]
