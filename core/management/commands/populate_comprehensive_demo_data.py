"""
Comprehensive demo data population command.
This command populates demo data for every model in the system.
"""

from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
from datetime import datetime, timedelta
import random
import logging

from core.models import Customer, EquipmentCategory, Location, UserProfile
from equipment.models import Equipment, EquipmentDocument, EquipmentComponent
from maintenance.models import (
    ActivityTypeCategory, ActivityTypeTemplate, MaintenanceActivityType,
    MaintenanceActivity, MaintenanceSchedule
)
from events.models import CalendarEvent, EventComment, EventAttachment, EventReminder
from core.rbac import Role, Permission

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Populate comprehensive demo data for all models in the system'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Clear existing data before populating (use with caution)',
        )
        parser.add_argument(
            '--users',
            type=int,
            default=10,
            help='Number of demo users to create (default: 10)',
        )
        parser.add_argument(
            '--equipment',
            type=int,
            default=50,
            help='Number of demo equipment items to create (default: 50)',
        )
        parser.add_argument(
            '--activities',
            type=int,
            default=100,
            help='Number of demo maintenance activities to create (default: 100)',
        )
        parser.add_argument(
            '--events',
            type=int,
            default=75,
            help='Number of demo calendar events to create (default: 75)',
        )
        parser.add_argument(
            '--skip-existing',
            action='store_true',
            help='Skip populating data that already exists',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating data',
        )

    def handle(self, *args, **options):
        if options['dry_run']:
            self.stdout.write(
                self.style.SUCCESS('DRY RUN: Would populate comprehensive demo data with:')
            )
            self.stdout.write(f'  - Users: {options["users"]}')
            self.stdout.write(f'  - Equipment: {options["equipment"]}')
            self.stdout.write(f'  - Maintenance Activities: {options["activities"]}')
            self.stdout.write(f'  - Calendar Events: {options["events"]}')
            if options['reset']:
                self.stdout.write('  - Reset existing data: YES')
            return
            
        self.stdout.write(
            self.style.SUCCESS('Starting comprehensive demo data population...')
        )
        
        try:
            with transaction.atomic():
                if options['reset']:
                    self.stdout.write('Clearing existing data...')
                    self.clear_existing_data()
                
                # Step 1: Call existing management commands
                self.stdout.write('Calling existing management commands...')
                self.call_existing_commands()
                
                # Step 2: Populate missing data
                self.stdout.write('Populating additional demo data...')
                self.populate_additional_data(options)
                
                # Step 3: Create relationships and associations
                self.stdout.write('Creating relationships and associations...')
                self.create_relationships(options)
                
                self.stdout.write(
                    self.style.SUCCESS('Comprehensive demo data population completed successfully!')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error during demo data population: {str(e)}')
            )
            raise CommandError(f'Demo data population failed: {str(e)}')

    def clear_existing_data(self):
        """Clear existing demo data while preserving system data."""
        # Clear user-created data but preserve system users
        EquipmentDocument.objects.all().delete()
        EquipmentComponent.objects.all().delete()
        Equipment.objects.all().delete()
        MaintenanceActivity.objects.all().delete()
        MaintenanceSchedule.objects.all().delete()
        CalendarEvent.objects.all().delete()
        EventComment.objects.all().delete()
        EventAttachment.objects.all().delete()
        EventReminder.objects.all().delete()
        
        # Clear locations but preserve system locations
        Location.objects.filter(is_site=False).delete()
        
        # Clear customers but preserve system customers
        Customer.objects.filter(name__startswith='Demo').delete()

    def call_existing_commands(self):
        """Call existing management commands for basic data."""
        commands = [
            'init_rbac',
            'setup_default_locations',
            'populate_activity_types',
            'populate_sample_data',
            'populate_maintenance_data',
            'populate_timeline_entries',
        ]
        
        for command in commands:
            try:
                self.stdout.write(f'Running {command}...')
                call_command(command, verbosity=0)
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'Warning: {command} failed: {str(e)}')
                )

    def populate_additional_data(self, options):
        """Populate additional demo data for all models."""
        # Create demo users
        self.create_demo_users(options['users'])
        
        # Create demo customers
        self.create_demo_customers()
        
        # Create demo equipment categories
        self.create_demo_equipment_categories()
        
        # Create demo locations
        self.create_demo_locations()
        
        # Create demo equipment
        self.create_demo_equipment(options['equipment'])
        
        # Create demo maintenance activities
        self.create_demo_maintenance_activities(options['activities'])
        
        # Create demo calendar events
        self.create_demo_calendar_events(options['events'])
        
        # Create demo components
        self.create_demo_components()

    def create_demo_users(self, count):
        """Create demo users with different roles."""
        if User.objects.filter(username__startswith='demo_').exists():
            self.stdout.write('Demo users already exist, skipping...')
            return
            
        roles = Role.objects.all()
        if not roles.exists():
            self.stdout.write('No roles found, creating basic roles...')
            call_command('init_rbac', verbosity=0)
            roles = Role.objects.all()
        
        for i in range(count):
            username = f'demo_user_{i+1}'
            email = f'demo{i+1}@example.com'
            
            user = User.objects.create_user(
                username=username,
                email=email,
                password='demo123',
                first_name=f'Demo{i+1}',
                last_name='User'
            )
            
            # Assign random role
            role = random.choice(roles)
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.role = role
            profile.theme_preference = random.choice(['dark', 'light'])
            profile.notifications_enabled = random.choice([True, False])
            profile.save()
            
        self.stdout.write(f'Created {count} demo users')

    def create_demo_customers(self):
        """Create demo customers."""
        if Customer.objects.filter(name__startswith='Demo').exists():
            self.stdout.write('Demo customers already exist, skipping...')
            return
            
        customers_data = [
            {'name': 'Demo Manufacturing Corp', 'code': 'DEMO_MFG', 'contact_email': 'contact@demomfg.com'},
            {'name': 'Demo Energy Solutions', 'code': 'DEMO_ENERGY', 'contact_email': 'info@demoenergy.com'},
            {'name': 'Demo Industrial Ltd', 'code': 'DEMO_INDUST', 'contact_email': 'support@demoindustrial.com'},
            {'name': 'Demo Power Systems', 'code': 'DEMO_POWER', 'contact_email': 'help@demopower.com'},
            {'name': 'Demo Utilities Co', 'code': 'DEMO_UTIL', 'contact_email': 'service@demoutilities.com'},
        ]
        
        for data in customers_data:
            Customer.objects.create(**data)
            
        self.stdout.write(f'Created {len(customers_data)} demo customers')

    def create_demo_equipment_categories(self):
        """Create demo equipment categories."""
        if EquipmentCategory.objects.filter(name__startswith='Demo').exists():
            self.stdout.write('Demo equipment categories already exist, skipping...')
            return
            
        categories_data = [
            {'name': 'Demo Transformers', 'description': 'Demo power transformers'},
            {'name': 'Demo Switchgear', 'description': 'Demo electrical switchgear'},
            {'name': 'Demo Protection Relays', 'description': 'Demo protection equipment'},
            {'name': 'Demo Circuit Breakers', 'description': 'Demo circuit breakers'},
            {'name': 'Demo Control Systems', 'description': 'Demo control and automation'},
        ]
        
        for data in categories_data:
            EquipmentCategory.objects.create(**data)
            
        self.stdout.write(f'Created {len(categories_data)} demo equipment categories')

    def create_demo_locations(self):
        """Create demo locations with hierarchy."""
        if Location.objects.filter(name__startswith='Demo Site').exists():
            self.stdout.write('Demo locations already exist, skipping...')
            return
            
        customers = list(Customer.objects.all())
        
        # Create demo sites
        for i in range(3):
            site = Location.objects.create(
                name=f'Demo Site {i+1}',
                is_site=True,
                customer=random.choice(customers) if customers else None,
                latitude=random.uniform(-90, 90),
                longitude=random.uniform(-180, 180),
                address=f'Demo Address {i+1}, Demo City, Demo State'
            )
            
            # Create pods for each site
            for j in range(random.randint(3, 8)):
                pod = Location.objects.create(
                    name=f'Demo Pod {i+1}-{j+1}',
                    parent_location=site,
                    is_site=False,
                    latitude=site.latitude + random.uniform(-0.01, 0.01),
                    longitude=site.longitude + random.uniform(-0.01, 0.01)
                )
                
                # Create sub-locations for each pod
                for k in range(random.randint(2, 5)):
                    Location.objects.create(
                        name=f'Demo Area {i+1}-{j+1}-{k+1}',
                        parent_location=pod,
                        is_site=False,
                        latitude=pod.latitude + random.uniform(-0.005, 0.005),
                        longitude=pod.longitude + random.uniform(-0.005, 0.005)
                    )
                    
        self.stdout.write('Created demo locations with hierarchy')

    def create_demo_equipment(self, count):
        """Create demo equipment items."""
        if Equipment.objects.filter(name__startswith='Demo Equipment').exists():
            self.stdout.write('Demo equipment already exists, skipping...')
            return
            
        categories = list(EquipmentCategory.objects.all())
        locations = list(Location.objects.filter(is_site=False))
        
        if not categories or not locations:
            self.stdout.write('No categories or locations available for equipment creation')
            return
            
        equipment_types = [
            'Transformer', 'Switchgear', 'Relay', 'Breaker', 'Controller',
            'Panel', 'Motor', 'Generator', 'Pump', 'Compressor'
        ]
        
        for i in range(count):
            equipment_type = random.choice(equipment_types)
            equipment = Equipment.objects.create(
                name=f'Demo Equipment {equipment_type} {i+1}',
                category=random.choice(categories),
                location=random.choice(locations),
                manufacturer_serial=f'DEMO-{equipment_type.upper()}-{i+1:04d}',
                asset_tag=f'DEMO-{i+1:04d}',
                manufacturer=f'Demo Manufacturer {random.randint(1, 5)}',
                model_number=f'DEMO-{equipment_type.upper()}-{random.randint(100, 999)}',
                status=random.choice(['active', 'active', 'active', 'maintenance', 'inactive']),
                power_ratings=f'{random.randint(100, 1000)}kW',
                trip_setpoints=f'{random.randint(50, 200)}A',
                dga_due_date=timezone.now().date() + timedelta(days=random.randint(30, 365)),
                next_maintenance_date=timezone.now().date() + timedelta(days=random.randint(7, 180)),
                commissioning_date=timezone.now().date() - timedelta(days=random.randint(100, 1000)),
                warranty_expiry_date=timezone.now().date() + timedelta(days=random.randint(100, 1000))
            )
            
        self.stdout.write(f'Created {count} demo equipment items')

    def create_demo_maintenance_activities(self, count):
        """Create demo maintenance activities."""
        if MaintenanceActivity.objects.filter(title__startswith='Demo Activity').exists():
            self.stdout.write('Demo maintenance activities already exist, skipping...')
            return
            
        equipment_list = list(Equipment.objects.all())
        activity_types = list(MaintenanceActivityType.objects.all())
        users = list(User.objects.filter(username__startswith='demo_'))
        
        if not equipment_list or not activity_types:
            self.stdout.write('No equipment or activity types available for maintenance creation')
            return
            
        statuses = ['scheduled', 'in_progress', 'completed', 'cancelled']
        priorities = ['low', 'medium', 'high', 'critical']
        
        created_count = 0
        for i in range(count):
            try:
                equipment = random.choice(equipment_list)
                activity_type = random.choice(activity_types)
                status = random.choice(statuses)
                
                # Calculate dates
                start_date = timezone.now() + timedelta(days=random.randint(-30, 90))
                end_date = start_date + timedelta(hours=random.randint(2, 8))
                
                activity = MaintenanceActivity.objects.create(
                    equipment=equipment,
                    activity_type=activity_type,
                    title=f'Demo Activity {i+1} - {activity_type.name}',
                    description=f'Demo maintenance activity for {equipment.name}',
                    status=status,
                    priority=random.choice(priorities),
                    scheduled_start=start_date,
                    scheduled_end=end_date,
                    assigned_to=random.choice(users) if users else None,
                    tools_required='Demo tools required for this activity',
                    parts_required='Demo parts required for this activity',
                    safety_notes='Demo safety considerations for this activity'
                )
                
                # Verify scheduled_start was set correctly
                if not activity.scheduled_start:
                    self.stdout.write(f'Warning: Activity {activity.id} created without scheduled_start')
                else:
                    self.stdout.write(f'Created activity {activity.id} with scheduled_start: {activity.scheduled_start}')
                
                # Set actual dates for completed activities
                if status == 'completed':
                    activity.actual_start = start_date
                    activity.actual_end = end_date
                    activity.completion_notes = 'Demo completion notes'
                    activity.save()
                    
                created_count += 1
                
            except Exception as e:
                self.stdout.write(f'Error creating maintenance activity {i+1}: {str(e)}')
                continue
                
        self.stdout.write(f'Created {created_count} demo maintenance activities')

    def create_demo_calendar_events(self, count):
        """Create demo calendar events."""
        if CalendarEvent.objects.filter(title__startswith='Demo Event').exists():
            self.stdout.write('Demo calendar events already exist, skipping...')
            return
            
        equipment_list = list(Equipment.objects.all())
        users = list(User.objects.filter(username__startswith='demo_'))
        
        if not equipment_list:
            self.stdout.write('No equipment available for calendar events')
            return
            
        event_types = ['maintenance', 'inspection', 'calibration', 'outage', 'upgrade', 'testing']
        priorities = ['low', 'medium', 'high', 'critical']
        
        for i in range(count):
            equipment = random.choice(equipment_list)
            event_type = random.choice(event_types)
            
            # Calculate dates
            event_date = timezone.now().date() + timedelta(days=random.randint(-30, 90))
            start_time = datetime.strptime(f'{random.randint(8, 17)}:{random.randint(0, 59):02d}', '%H:%M').time()
            end_time = datetime.strptime(f'{start_time.hour + random.randint(1, 4)}:{random.randint(0, 59):02d}', '%H:%M').time()
            
            event = CalendarEvent.objects.create(
                title=f'Demo Event {i+1} - {event_type.title()}',
                description=f'Demo {event_type} event for {equipment.name}',
                event_type=event_type,
                equipment=equipment,
                event_date=event_date,
                start_time=start_time,
                end_time=end_time,
                all_day=random.choice([True, False]),
                priority=random.choice(priorities),
                assigned_to=random.choice(users) if users else None,
                is_completed=random.choice([True, False])
            )
            
            # Create comments for some events
            if random.choice([True, False]):
                EventComment.objects.create(
                    event=event,
                    comment=f'Demo comment for {event.title}',
                    is_internal=random.choice([True, False])
                )
                
        self.stdout.write(f'Created {count} demo calendar events')

    def create_demo_components(self):
        """Create demo components for equipment."""
        equipment_list = list(Equipment.objects.all())
        
        if not equipment_list:
            self.stdout.write('No equipment available for documents and components')
            return
            
        # Create demo components
        component_types = ['Sensor', 'Relay', 'Switch', 'Fuse', 'Connector', 'Terminal', 'Filter', 'Pump', 'Motor', 'Valve']
        
        for equipment in random.sample(equipment_list, min(20, len(equipment_list))):
            for i in range(random.randint(1, 3)):
                component_name = f'Demo {random.choice(component_types)} {i+1}'
                if EquipmentComponent.objects.filter(equipment=equipment, name=component_name).exists():
                    self.stdout.write(f'Warning: Component "{component_name}" for equipment id={equipment.id} already exists, skipping.')
                    continue
                EquipmentComponent.objects.create(
                    equipment=equipment,
                    name=component_name,
                    part_number=f'DEMO-PART-{random.randint(100, 999)}',
                    description=f'Demo component for {equipment.name}',
                    quantity=random.randint(1, 5),
                    replacement_date=timezone.now().date() - timedelta(days=random.randint(100, 1000)),
                    next_replacement_date=timezone.now().date() + timedelta(days=random.randint(100, 1000)),
                    is_critical=random.choice([True, False])
                )
        
        # Note: EquipmentDocument requires a file field, so we skip creating demo documents
        # to avoid file handling complexity in demo data generation
        self.stdout.write('Skipping EquipmentDocument creation (requires file upload)')
                
        self.stdout.write('Created demo components')

    def create_relationships(self, options):
        """Create relationships between different models."""
        # Link maintenance activities to calendar events
        maintenance_activities = MaintenanceActivity.objects.filter(
            title__startswith='Demo Activity'
        ).select_related('equipment')
        
        calendar_events = CalendarEvent.objects.filter(
            title__startswith='Demo Event',
            event_type='maintenance'
        ).select_related('equipment')
        
        linked_count = 0
        for activity in maintenance_activities[:min(20, len(maintenance_activities))]:
            try:
                # Ensure activity has scheduled_start
                if not activity.scheduled_start:
                    self.stdout.write(f'Warning: Activity {activity.id} has no scheduled_start, skipping...')
                    continue
                    
                # Find matching calendar event
                matching_events = calendar_events.filter(
                    equipment=activity.equipment,
                    event_date=activity.scheduled_start.date()
                )
                if matching_events.exists():
                    event = matching_events.first()
                    event.maintenance_activity = activity
                    event.save()
                    linked_count += 1
                    
            except Exception as e:
                self.stdout.write(f'Warning: Error linking activity {activity.id}: {str(e)}')
                continue
                
        self.stdout.write(f'Linked {linked_count} maintenance activities to calendar events')
                
        # Create event reminders
        events = CalendarEvent.objects.filter(title__startswith='Demo Event')
        users = list(User.objects.filter(username__startswith='demo_'))
        
        reminder_count = 0
        for event in random.sample(list(events), min(20, len(events))):
            try:
                if users:
                    # Calculate reminder time based on event_date and start_time
                    reminder_datetime = datetime.combine(event.event_date, event.start_time or datetime.min.time())
                    reminder_datetime = timezone.make_aware(reminder_datetime)
                    reminder_datetime = reminder_datetime - timedelta(hours=random.randint(1, 24))
                    
                    EventReminder.objects.create(
                        event=event,
                        reminder_type=random.choice(['email', 'dashboard']),
                        user=random.choice(users),
                        reminder_time=reminder_datetime,
                        message=f'Reminder: {event.title} is scheduled for {event.event_date}'
                    )
                    reminder_count += 1
                    
            except Exception as e:
                self.stdout.write(f'Warning: Error creating reminder for event {event.id}: {str(e)}')
                continue
                
        self.stdout.write(f'Created {reminder_count} event reminders')
        self.stdout.write('Created relationships between models') 