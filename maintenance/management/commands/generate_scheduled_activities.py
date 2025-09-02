"""
Management command to generate maintenance activities from existing schedules.
This command can be run manually or via cron to generate upcoming maintenance activities.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from maintenance.models import MaintenanceSchedule


class Command(BaseCommand):
    help = 'Generate maintenance activities from existing schedules'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days-ahead',
            type=int,
            default=30,
            help='Number of days ahead to generate activities (default: 30)'
        )
        parser.add_argument(
            '--equipment-id',
            type=int,
            help='Generate activities for specific equipment ID only'
        )
        parser.add_argument(
            '--activity-type-id',
            type=int,
            help='Generate activities for specific activity type ID only'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be generated without creating activities'
        )

    def handle(self, *args, **options):
        self.stdout.write('🚀 Starting scheduled maintenance activity generation...')
        
        try:
            days_ahead = options['days_ahead']
            dry_run = options['dry_run']
            
            # Build query for schedules
            schedules = MaintenanceSchedule.objects.filter(is_active=True, auto_generate=True)
            
            if options.get('equipment_id'):
                schedules = schedules.filter(equipment_id=options['equipment_id'])
                self.stdout.write(f'📋 Filtering by equipment ID: {options["equipment_id"]}')
            
            if options.get('activity_type_id'):
                schedules = schedules.filter(activity_type_id=options['activity_type_id'])
                self.stdout.write(f'📋 Filtering by activity type ID: {options["activity_type_id"]}')
            
            total_schedules = schedules.count()
            self.stdout.write(f'📋 Processing {total_schedules} active schedules...')
            self.stdout.write(f'📅 Generating activities for next {days_ahead} days...')
            
            if dry_run:
                self.stdout.write('🔍 DRY RUN MODE - No activities will be created')
            
            generated_count = 0
            skipped_count = 0
            
            for schedule in schedules:
                self.stdout.write(f'   Processing schedule: {schedule.equipment.name} - {schedule.activity_type.name}')
                
                # Generate activities for this schedule
                activities_generated = self._generate_activities_for_schedule(
                    schedule, days_ahead, dry_run
                )
                
                if activities_generated > 0:
                    generated_count += activities_generated
                    self.stdout.write(f'     ✅ Generated {activities_generated} activities')
                else:
                    skipped_count += 1
                    self.stdout.write(f'     ⚠️  No activities needed')
            
            self.stdout.write('')
            if dry_run:
                self.stdout.write(
                    self.style.SUCCESS(f'🔍 DRY RUN COMPLETED')
                )
                self.stdout.write(f'   Would generate: {generated_count} activities')
                self.stdout.write(f'   Would skip: {skipped_count} schedules')
            else:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Activity generation completed!')
                )
                self.stdout.write(f'   Generated: {generated_count} activities')
                self.stdout.write(f'   Skipped: {skipped_count} schedules')

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Activity generation failed: {str(e)}')
            )
            raise

    def _generate_activities_for_schedule(self, schedule, days_ahead, dry_run):
        """Generate activities for a specific schedule."""
        from maintenance.models import MaintenanceActivity
        
        generated_count = 0
        target_date = timezone.now().date() + timedelta(days=days_ahead)
        
        # Get next due date
        next_date = schedule.get_next_due_date()
        if not next_date:
            return 0
        
        # Generate activities until we exceed the target date
        while next_date <= target_date:
            # Check if activity already exists for this date
            existing = MaintenanceActivity.objects.filter(
                equipment=schedule.equipment,
                activity_type=schedule.activity_type,
                scheduled_start__date=next_date
            ).exists()
            
            if existing:
                # Activity already exists, move to next occurrence
                next_date = next_date + timedelta(days=schedule.get_frequency_in_days())
                continue
            
            if not dry_run:
                # Create the maintenance activity
                activity = MaintenanceActivity.objects.create(
                    equipment=schedule.equipment,
                    activity_type=schedule.activity_type,
                    title=f"{schedule.activity_type.name} - {schedule.equipment.name}",
                    description=schedule.activity_type.description,
                    scheduled_start=timezone.datetime.combine(
                        next_date, 
                        timezone.datetime.min.time()
                    ).replace(tzinfo=timezone.get_current_timezone()),
                    scheduled_end=timezone.datetime.combine(
                        next_date, 
                        timezone.datetime.min.time()
                    ).replace(tzinfo=timezone.get_current_timezone()) + 
                    timedelta(hours=schedule.activity_type.estimated_duration_hours),
                    status='scheduled',
                    priority='medium' if schedule.activity_type.is_mandatory else 'low',
                    created_by=schedule.created_by,
                )
                
                # Create corresponding calendar event
                try:
                    from events.models import CalendarEvent
                    calendar_event = CalendarEvent.objects.create(
                        title=f"Maintenance: {activity.title}",
                        description=activity.description,
                        event_type='maintenance',
                        equipment=activity.equipment,
                        maintenance_activity=activity,
                        event_date=activity.scheduled_start.date(),
                        start_time=activity.scheduled_start.time(),
                        end_time=activity.scheduled_end.time() if activity.scheduled_end else None,
                        assigned_to=activity.assigned_to,
                        priority=activity.priority,
                        created_by=activity.created_by
                    )
                except Exception as e:
                    self.stdout.write(f'     ⚠️  Warning: Could not create calendar event: {str(e)}')
                
                # Update last generated date
                schedule.last_generated = next_date
                schedule.save()
            
            generated_count += 1
            
            # Calculate next occurrence
            next_date = next_date + timedelta(days=schedule.get_frequency_in_days())
            
            # Check if we've exceeded the end date
            if schedule.end_date and next_date > schedule.end_date:
                break
        
        return generated_count
