from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0028_location_layout_height_location_layout_width_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='location',
            name='grid_row',
            field=models.PositiveSmallIntegerField(blank=True, null=True, help_text='Facility-map grid row (0-based)'),
        ),
        migrations.AddField(
            model_name='location',
            name='grid_col',
            field=models.PositiveSmallIntegerField(blank=True, null=True, help_text='Facility-map grid column (0-based)'),
        ),
    ]
