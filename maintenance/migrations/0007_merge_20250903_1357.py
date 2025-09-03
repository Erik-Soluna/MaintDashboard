# Generated manually to merge conflicting migrations

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('maintenance', '0002_add_timeline_entry_types'),
        ('maintenance', '0005_activitytypecategory_is_global'),
        ('maintenance', '0006_globalschedule_scheduleoverride_and_more'),
    ]

    operations = [
        # No operations needed - this is just a merge migration
    ]