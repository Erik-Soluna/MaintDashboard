from django.db import migrations
import datetime
from django.utils import timezone

def make_datetimes_aware(apps, schema_editor):
    MaintenanceActivity = apps.get_model('maintenance', 'MaintenanceActivity')
    for activity in MaintenanceActivity.objects.all():
        changed = False
        for field in ['scheduled_start', 'scheduled_end', 'actual_start', 'actual_end']:
            dt = getattr(activity, field)
            if dt and isinstance(dt, datetime.datetime) and timezone.is_naive(dt):
                setattr(activity, field, timezone.make_aware(dt))
                changed = True
        if changed:
            activity.save(update_fields=['scheduled_start', 'scheduled_end', 'actual_start', 'actual_end'])

def reverse_func(apps, schema_editor):
    # No-op: we do not want to make datetimes naive again
    pass

class Migration(migrations.Migration):
    dependencies = [
        ('maintenance', '0003_remove_maintenancereport_maintenance_activit_da135f_idx_and_more'),
    ]

    operations = [
        migrations.RunPython(make_datetimes_aware, reverse_func),
    ] 