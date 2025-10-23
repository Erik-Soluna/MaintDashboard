"""
Management command to generate initial maintenance schedules for existing equipment.
This command creates maintenance schedules for all equipment using the default activity types.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date, timedelta
from equipment.models import Equipment
from maintenance.models import MaintenanceActivityType, MaintenanceSchedule


class Command(BaseCommand):
    help = 'Generate initial maintenance schedules for existing equipment'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreation of schedules even if they already exist'
        )
        parser.add_argument(
            '--equipment-id',
            type=int,
            help='Generate schedules for specific equipment ID only'
        )
        parser.add_argument(
            '--start-date',
            type=str,
            help='Start date for schedules (YYYY-MM-DD format, defaults to today)'
        )

    def handle(self, *args, **options):
        self.stdout.write('🚀 Starting initial maintenance schedule generation...')
        
        try:
            # Get admin user for created_by field
            admin_user = User.objects.filter(is_superuser=True).first()
            if not admin_user:
                admin_user = User.objects.filter(is_staff=True).first()
            if not admin_user:
                self.stdout.write(
                    self.style.ERROR('❌ No admin user found for creating schedules')
                )
                return

            # Get start date
            start_date = options.get('start_date')
            if start_date:
                try:
                    start_date = date.fromisoformat(start_date)
                except ValueError:
                    self.stdout.write(
                        self.style.ERROR('❌ Invalid start date format. Use YYYY-MM-DD')
                    )
                    return
            else:
                start_date = date.today()

            # Get equipment to process
            if options.get('equipment_id'):
                equipment_list = Equipment.objects.filter(id=options['equipment_id'])
                if not equipment_list.exists():
                    self.stdout.write(
                        self.style.ERROR(f'❌ Equipment with ID {options["equipment_id"]} not found')
                    )
                    return
            else:
                equipment_list = Equipment.objects.all()

            # Get active activity types
            activity_types = MaintenanceActivityType.objects.filter(is_active=True)
            
            if not activity_types.exists():
                self.stdout.write(
                    self.style.WARNING('⚠️  No active activity types found. Please create activity types first.')
                )
                return

            self.stdout.write(f'📋 Processing {equipment_list.count()} equipment items...')
            self.stdout.write(f'📋 Using {activity_types.count()} activity types...')
            self.stdout.write(f'📅 Start date: {start_date}')

            created_count = 0
            skipped_count = 0

            for equipment in equipment_list:
                self.stdout.write(f'   Processing equipment: {equipment.name}')
                
                for activity_type in activity_types:
                    # Check if schedule already exists
                    existing_schedule = MaintenanceSchedule.objects.filter(
                        equipment=equipment,
                        activity_type=activity_type
                    ).first()
                    
                    if existing_schedule and not options['force']:
                        self.stdout.write(f'     ⚠️  Schedule already exists for {activity_type.name}, skipping...')
                        skipped_count += 1
                        continue
                    
                    # Calculate appropriate start date based on frequency
                    schedule_start_date = self._calculate_schedule_start_date(
                        activity_type, start_date
                    )
                    
                    # Create or update schedule
                    schedule, created = MaintenanceSchedule.objects.get_or_create(
                        equipment=equipment,
                        activity_type=activity_type,
                        defaults={
                            'frequency': self._get_frequency_from_days(activity_type.frequency_days),
                            'frequency_days': activity_type.frequency_days,
                            'start_date': schedule_start_date,
                            'auto_generate': True,
                            'advance_notice_days': 7,
                            'is_active': True,
                            'created_by': admin_user,
                        }
                    )
                    
                    if created:
                        self.stdout.write(f'     ✅ Created schedule: {activity_type.name}')
                        created_count += 1
                    else:
                        # Update existing schedule if force option is used
                        if options['force']:
                            schedule.start_date = schedule_start_date
                            schedule.frequency = self._get_frequency_from_days(activity_type.frequency_days)
                            schedule.frequency_days = activity_type.frequency_days
                            schedule.save()
                            self.stdout.write(f'     🔄 Updated schedule: {activity_type.name}')
                            created_count += 1

            self.stdout.write('')
            self.stdout.write(
                self.style.SUCCESS(f'✅ Schedule generation completed!')
            )
            self.stdout.write(f'   Created/Updated: {created_count} schedules')
            self.stdout.write(f'   Skipped: {skipped_count} schedules')
            
            # Generate initial activities for the schedules
            self.stdout.write('')
            self.stdout.write('🔄 Generating initial maintenance activities...')
            self._generate_initial_activities(equipment_list, activity_types, admin_user)

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Schedule generation failed: {str(e)}')
            )
            raise

    def _calculate_schedule_start_date(self, activity_type, base_start_date):
        """Calculate appropriate start date for a schedule based on activity type frequency."""
        if activity_type.frequency_days <= 0:
            # No frequency set, use base start date
            return base_start_date
        
        # For activities with frequency, start from the base date
        # but ensure it's not in the past
        if base_start_date < date.today():
            # If base date is in the past, calculate next occurrence
            days_since_base = (date.today() - base_start_date).days
            if days_since_base > 0:
                cycles_passed = days_since_base // activity_type.frequency_days
                return base_start_date + timedelta(days=(cycles_passed + 1) * activity_type.frequency_days)
        
        return base_start_date

    def _get_frequency_from_days(self, frequency_days):
        """Convert frequency days to frequency choice."""
        if frequency_days <= 0:
            return 'custom'
        elif frequency_days == 1:
            return 'daily'
        elif frequency_days == 7:
            return 'weekly'
        elif frequency_days == 30:
            return 'monthly'
        elif frequency_days == 90:
            return 'quarterly'
        elif frequency_days == 180:
            return 'semi_annual'
        elif frequency_days == 365:
            return 'annual'
        else:
            return 'custom'

    def _generate_initial_activities(self, equipment_list, activity_types, admin_user):
        """Generate initial maintenance activities for the created schedules."""
        from maintenance.models import MaintenanceActivity
        
        generated_count = 0
        
        for equipment in equipment_list:
            for activity_type in activity_types:
                # Get the schedule
                schedule = MaintenanceSchedule.objects.filter(
                    equipment=equipment,
                    activity_type=activity_type
                ).first()
                
                if not schedule:
                    continue
                
                # Check if activities already exist
                existing_activities = MaintenanceActivity.objects.filter(
                    equipment=equipment,
                    activity_type=activity_type
                ).count()
                
                if existing_activities > 0:
                    self.stdout.write(f'     ⚠️  Activities already exist for {equipment.name} - {activity_type.name}, skipping...')
                    continue
                
                # Generate initial activity
                next_date = schedule.get_next_due_date()
                if next_date:
                    activity = MaintenanceActivity.objects.create(
                        equipment=equipment,
                        activity_type=activity_type,
                        title=f"{activity_type.name} - {equipment.name}",
                        description=activity_type.description,
                        scheduled_start=timezone.datetime.combine(
                            next_date, 
                            timezone.datetime.min.time()
                        ).replace(tzinfo=timezone.get_current_timezone()),
                        scheduled_end=timezone.datetime.combine(
                            next_date, 
                            timezone.datetime.min.time()
                        ).replace(tzinfo=timezone.get_current_timezone()) + 
                        timedelta(hours=activity_type.estimated_duration_hours),
                        status='scheduled',
                        priority='medium' if activity_type.is_mandatory else 'low',
                        created_by=admin_user,
                    )
                    
                    self.stdout.write(f'     ✅ Generated activity: {activity.title} for {next_date}')
                    generated_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'   Generated {generated_count} initial maintenance activities')
        )
