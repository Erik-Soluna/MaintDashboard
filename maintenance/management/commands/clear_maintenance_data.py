"""
Management command to clear all maintenance activities and calendar events.
Use with caution - this will permanently delete all maintenance data.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from maintenance.models import MaintenanceActivity, MaintenanceSchedule
from events.models import CalendarEvent
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Clear all maintenance activities and calendar events'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm that you want to delete all maintenance data',
        )
        parser.add_argument(
            '--keep-schedules',
            action='store_true',
            help='Keep maintenance schedules (only delete activities and events)',
        )

    def handle(self, *args, **options):
        if not options['confirm']:
            raise CommandError(
                'This command will permanently delete all maintenance activities and calendar events.\n'
                'Use --confirm to proceed with the deletion.'
            )

        try:
            with transaction.atomic():
                # Count existing records
                activity_count = MaintenanceActivity.objects.count()
                event_count = CalendarEvent.objects.count()
                schedule_count = MaintenanceSchedule.objects.count()
                
                self.stdout.write(
                    self.style.WARNING(
                        f'Found {activity_count} maintenance activities, '
                        f'{event_count} calendar events, and '
                        f'{schedule_count} maintenance schedules'
                    )
                )
                
                # Delete calendar events first (they reference maintenance activities)
                if event_count > 0:
                    self.stdout.write('Deleting calendar events...')
                    CalendarEvent.objects.all().delete()
                    self.stdout.write(
                        self.style.SUCCESS(f'Deleted {event_count} calendar events')
                    )
                
                # Delete maintenance activities
                if activity_count > 0:
                    self.stdout.write('Deleting maintenance activities...')
                    MaintenanceActivity.objects.all().delete()
                    self.stdout.write(
                        self.style.SUCCESS(f'Deleted {activity_count} maintenance activities')
                    )
                
                # Delete maintenance schedules (optional)
                if not options['keep_schedules'] and schedule_count > 0:
                    self.stdout.write('Deleting maintenance schedules...')
                    MaintenanceSchedule.objects.all().delete()
                    self.stdout.write(
                        self.style.SUCCESS(f'Deleted {schedule_count} maintenance schedules')
                    )
                elif options['keep_schedules']:
                    self.stdout.write(
                        self.style.WARNING('Keeping maintenance schedules as requested')
                    )
                
                self.stdout.write(
                    self.style.SUCCESS(
                        '\n✅ Successfully cleared all maintenance data!\n'
                        'The system is now clean and ready for fresh data.'
                    )
                )
                
        except Exception as e:
            raise CommandError(f'Error clearing maintenance data: {str(e)}')
