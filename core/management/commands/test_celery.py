"""
Management command to test Celery setup.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from maintenance_dashboard.celery import debug_task


class Command(BaseCommand):
    help = 'Test Celery configuration and task execution'

    def add_arguments(self, parser):
        parser.add_argument(
            '--async',
            action='store_true',
            help='Run task asynchronously (requires Celery worker)',
        )

    def handle(self, *args, **options):
        self.stdout.write("Testing Celery configuration...")
        
        if options['async']:
            self.stdout.write("Running debug task asynchronously...")
            result = debug_task.delay()
            self.stdout.write(f"Task queued with ID: {result.id}")
            self.stdout.write("Check Celery worker logs to see task execution.")
        else:
            self.stdout.write("Running debug task synchronously...")
            result = debug_task()
            self.stdout.write(f"Task completed: {result}")
        
        # Test importing tasks from apps
        try:
            from maintenance.tasks import generate_scheduled_maintenance
            from events.tasks import send_event_reminders
            self.stdout.write(self.style.SUCCESS("✓ Successfully imported maintenance tasks"))
            self.stdout.write(self.style.SUCCESS("✓ Successfully imported events tasks"))
        except ImportError as e:
            self.stdout.write(self.style.ERROR(f"✗ Error importing tasks: {e}"))
        
        # Check Celery app configuration
        from maintenance_dashboard.celery import app
        self.stdout.write(f"Celery broker: {app.conf.broker_url}")
        self.stdout.write(f"Result backend: {app.conf.result_backend}")
        
        # List available tasks
        self.stdout.write("\nRegistered tasks:")
        for task_name in sorted(app.tasks.keys()):
            if not task_name.startswith('celery.'):
                self.stdout.write(f"  - {task_name}")
        
        self.stdout.write(self.style.SUCCESS("\nCelery test completed!"))
        self.stdout.write("To run Celery worker: celery -A maintenance_dashboard worker --loglevel=info")
        self.stdout.write("To run Celery beat: celery -A maintenance_dashboard beat --loglevel=info")