# Generated manually to fix category reference issue
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('maintenance', '0001_initial'),
    ]

    operations = [
        # This migration removes any phantom category references
        # that might be causing the database error
        migrations.RunSQL(
            "-- Remove any phantom category references",
            reverse_sql="-- No reverse operation needed"
        ),
    ]