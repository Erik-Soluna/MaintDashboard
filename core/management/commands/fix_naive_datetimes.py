"""
Management command to fix naive datetime warnings in MaintenanceActivity model.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from maintenance.models import MaintenanceActivity
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Fix naive datetime warnings by converting existing naive datetimes to timezone-aware datetimes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be fixed without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write('DRY RUN: Would fix naive datetime warnings...')
        else:
            self.stdout.write('Fixing naive datetime warnings...')
        
        # Get all maintenance activities with naive datetimes
        activities = MaintenanceActivity.objects.all()
        fixed_count = 0
        
        for activity in activities:
            needs_save = False
            
            # Check and fix scheduled_start
            if activity.scheduled_start and timezone.is_naive(activity.scheduled_start):
                if not dry_run:
                    activity.scheduled_start = timezone.make_aware(activity.scheduled_start)
                self.stdout.write(f'  Fixed scheduled_start for activity {activity.id}: {activity.scheduled_start}')
                needs_save = True
            
            # Check and fix scheduled_end
            if activity.scheduled_end and timezone.is_naive(activity.scheduled_end):
                if not dry_run:
                    activity.scheduled_end = timezone.make_aware(activity.scheduled_end)
                self.stdout.write(f'  Fixed scheduled_end for activity {activity.id}: {activity.scheduled_end}')
                needs_save = True
            
            # Check and fix actual_start
            if activity.actual_start and timezone.is_naive(activity.actual_start):
                if not dry_run:
                    activity.actual_start = timezone.make_aware(activity.actual_start)
                self.stdout.write(f'  Fixed actual_start for activity {activity.id}: {activity.actual_start}')
                needs_save = True
            
            # Check and fix actual_end
            if activity.actual_end and timezone.is_naive(activity.actual_end):
                if not dry_run:
                    activity.actual_end = timezone.make_aware(activity.actual_end)
                self.stdout.write(f'  Fixed actual_end for activity {activity.id}: {activity.actual_end}')
                needs_save = True
            
            if needs_save and not dry_run:
                activity.save()
                fixed_count += 1
        
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(f'DRY RUN: Would fix {fixed_count} maintenance activities')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully fixed {fixed_count} maintenance activities')
            ) 