from django.core.management.base import BaseCommand
from django.utils import timezone
from maintenance.models import MaintenanceActivity
import datetime


class Command(BaseCommand):
    help = 'Fix naive datetime objects in MaintenanceActivity model'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be fixed without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        # Get all maintenance activities
        activities = MaintenanceActivity.objects.all()
        fixed_count = 0
        
        for activity in activities:
            changed = False
            fields_to_check = ['scheduled_start', 'scheduled_end', 'actual_start', 'actual_end']
            
            for field_name in fields_to_check:
                field_value = getattr(activity, field_name)
                if field_value and isinstance(field_value, datetime.datetime) and timezone.is_naive(field_value):
                    aware_value = timezone.make_aware(field_value)
                    if dry_run:
                        self.stdout.write(
                            f'Would fix {activity.id}: {field_name} from {field_value} to {aware_value}'
                        )
                    else:
                        setattr(activity, field_name, aware_value)
                    changed = True
            
            if changed:
                if not dry_run:
                    activity.save(update_fields=fields_to_check)
                fixed_count += 1
        
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(f'DRY RUN: Would fix {fixed_count} maintenance activities')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully fixed {fixed_count} maintenance activities')
            ) 