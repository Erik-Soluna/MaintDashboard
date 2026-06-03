# Data fix: the old edit form omitted is_active, so saving an equipment silently
# set is_active=False and hid it from the maintenance/calendar pickers (and,
# until recently, the map). Reactivate units that are clearly still in service —
# is_active=False but operational status active/maintenance. Retired/inactive
# status equipment is left alone (may be deactivated on purpose). Idempotent.

from django.db import migrations


def reactivate(apps, schema_editor):
    Equipment = apps.get_model('equipment', 'Equipment')
    Equipment.objects.filter(
        is_active=False, status__in=['active', 'maintenance']
    ).update(is_active=True)


def noop(apps, schema_editor):
    # No reverse — we don't know which units were intentionally inactive before.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('equipment', '0021_equipment_layout_fields'),
    ]

    operations = [
        migrations.RunPython(reactivate, noop),
    ]
