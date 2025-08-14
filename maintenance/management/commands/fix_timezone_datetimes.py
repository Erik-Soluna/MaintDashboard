from django.core.management.base import BaseCommand
from django.utils import timezone
from maintenance.models import MaintenanceActivity
from django.db import transaction
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Fix naive datetime fields in MaintenanceActivity models by making them timezone-aware'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        # Find all activities with naive datetimes
        activities = MaintenanceActivity.objects.all()
        fixed_count = 0
        
        self.stdout.write(f"Checking {activities.count()} maintenance activities for timezone issues...")
        
        for activity in activities:
            needs_update = False
            update_fields = []
            
            # Check each datetime field
            if activity.scheduled_start and timezone.is_naive(activity.scheduled_start):
                if not dry_run:
                    activity.scheduled_start = timezone.make_aware(activity.scheduled_start)
                update_fields.append('scheduled_start')
                needs_update = True
                self.stdout.write(f"  - Activity {activity.id}: scheduled_start needs timezone fix")
            
            if activity.scheduled_end and timezone.is_naive(activity.scheduled_end):
                if not dry_run:
                    activity.scheduled_end = timezone.make_aware(activity.scheduled_end)
                update_fields.append('scheduled_end')
                needs_update = True
                self.stdout.write(f"  - Activity {activity.id}: scheduled_end needs timezone fix")
            
            if activity.actual_start and timezone.is_naive(activity.actual_start):
                if not dry_run:
                    activity.actual_start = timezone.make_aware(activity.actual_start)
                update_fields.append('actual_start')
                needs_update = True
                self.stdout.write(f"  - Activity {activity.id}: actual_start needs timezone fix")
            
            if activity.actual_end and timezone.is_naive(activity.actual_end):
                if not dry_run:
                    activity.actual_end = timezone.make_aware(activity.actual_end)
                update_fields.append('actual_end')
                needs_update = True
                self.stdout.write(f"  - Activity {activity.id}: actual_end needs timezone fix")
            
            if needs_update:
                if not dry_run:
                    try:
                        with transaction.atomic():
                            activity.save(update_fields=update_fields)
                        fixed_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(f"  ✓ Fixed timezone for activity {activity.id}")
                        )
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f"  ✗ Failed to fix activity {activity.id}: {e}")
                        )
                else:
                    fixed_count += 1
        
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(f'DRY RUN: Would fix {fixed_count} activities')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully fixed {fixed_count} activities')
            )
        
        self.stdout.write(self.style.SUCCESS('Timezone fix operation completed!'))
