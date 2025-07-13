from django.db import migrations

def create_heartbeat_task(apps, schema_editor):
    IntervalSchedule = apps.get_model('django_celery_beat', 'IntervalSchedule')
    PeriodicTask = apps.get_model('django_celery_beat', 'PeriodicTask')

    # Create or get 1-minute interval
    interval, _ = IntervalSchedule.objects.get_or_create(
        every=1,
        period='minutes',
    )

    # Create or update the heartbeat periodic task
    PeriodicTask.objects.update_or_create(
        name='Celery Beat Heartbeat',
        defaults={
            'interval': interval,
            'task': 'core.tasks.celery_beat_heartbeat',
            'enabled': True,
        }
    )

class Migration(migrations.Migration):
    dependencies = [
        ('core', '0005_merge_20250713_0219'),
        ('django_celery_beat', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_heartbeat_task, reverse_code=migrations.RunPython.noop),
    ] 