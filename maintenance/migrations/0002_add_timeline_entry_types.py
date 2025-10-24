# Generated manually to add new timeline entry types

from django.db import migrations


def add_timeline_entry_types(apps, schema_editor):
    """Add new timeline entry types to existing choices."""
    # This migration is for data consistency
    # The new choices will be available in the model
    pass


def reverse_timeline_entry_types(apps, schema_editor):
    """Reverse migration (no action needed)."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('maintenance', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(add_timeline_entry_types, reverse_timeline_entry_types),
    ]
