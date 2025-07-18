"""
Management command to set up default maintenance schedules.
Creates category-based and global schedules for common maintenance activities.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import EquipmentCategory
from maintenance.models import (
    MaintenanceActivityType, ActivityTypeCategory,
    EquipmentCategorySchedule, GlobalSchedule
)


class Command(BaseCommand):
    help = 'Set up default maintenance schedules for equipment categories and global requirements'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreation of existing schedules',
        )

    def handle(self, *args, **options):
        self.stdout.write('Setting up default maintenance schedules...')
        
        # Get or create admin user
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@example.com',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        
        # Get or create activity type categories
        preventive_category, _ = ActivityTypeCategory.objects.get_or_create(
            name='Preventive',
            defaults={
                'description': 'Preventive maintenance activities',
                'color': '#28a745',
                'icon': 'fas fa-shield-alt',
                'is_global': True,
            }
        )
        
        inspection_category, _ = ActivityTypeCategory.objects.get_or_create(
            name='Inspection',
            defaults={
                'description': 'Inspection and testing activities',
                'color': '#17a2b8',
                'icon': 'fas fa-search',
                'is_global': True,
            }
        )
        
        corrective_category, _ = ActivityTypeCategory.objects.get_or_create(
            name='Corrective',
            defaults={
                'description': 'Corrective maintenance activities',
                'color': '#dc3545',
                'icon': 'fas fa-wrench',
                'is_global': True,
            }
        )
        
        # Get or create activity types
        activity_types = {}
        
        # Preventive activity types
        activity_types['annual_inspection'] = MaintenanceActivityType.objects.get_or_create(
            name='Annual Inspection',
            defaults={
                'category': preventive_category,
                'description': 'Comprehensive annual inspection and maintenance',
                'estimated_duration_hours': 4,
                'frequency_days': 365,
                'is_mandatory': True,
                'tools_required': 'Standard toolkit, measuring instruments, safety equipment',
                'safety_notes': 'Ensure equipment is de-energized and properly locked out',
                'created_by': admin_user,
            }
        )[0]
        
        activity_types['quarterly_check'] = MaintenanceActivityType.objects.get_or_create(
            name='Quarterly Check',
            defaults={
                'category': preventive_category,
                'description': 'Quarterly operational check and minor maintenance',
                'estimated_duration_hours': 2,
                'frequency_days': 90,
                'is_mandatory': True,
                'tools_required': 'Basic toolkit, cleaning supplies',
                'safety_notes': 'Follow standard safety procedures',
                'created_by': admin_user,
            }
        )[0]
        
        activity_types['monthly_inspection'] = MaintenanceActivityType.objects.get_or_create(
            name='Monthly Inspection',
            defaults={
                'category': inspection_category,
                'description': 'Monthly visual inspection and operational check',
                'estimated_duration_hours': 1,
                'frequency_days': 30,
                'is_mandatory': True,
                'tools_required': 'Flashlight, inspection checklist',
                'safety_notes': 'Visual inspection only - no physical contact required',
                'created_by': admin_user,
            }
        )[0]
        
        activity_types['weekly_check'] = MaintenanceActivityType.objects.get_or_create(
            name='Weekly Check',
            defaults={
                'category': inspection_category,
                'description': 'Weekly operational status check',
                'estimated_duration_hours': 0.5,
                'frequency_days': 7,
                'is_mandatory': False,
                'tools_required': 'None required',
                'safety_notes': 'Visual inspection only',
                'created_by': admin_user,
            }
        )[0]
        
        # Get equipment categories
        categories = EquipmentCategory.objects.filter(is_active=True)
        
        # Define category-specific schedules
        category_schedules = {
            'transformer': [
                {
                    'activity_type': activity_types['annual_inspection'],
                    'frequency': 'annual',
                    'frequency_days': 365,
                    'default_priority': 'high',
                    'default_duration_hours': 6,
                },
                {
                    'activity_type': activity_types['quarterly_check'],
                    'frequency': 'quarterly',
                    'frequency_days': 90,
                    'default_priority': 'medium',
                    'default_duration_hours': 3,
                },
                {
                    'activity_type': activity_types['monthly_inspection'],
                    'frequency': 'monthly',
                    'frequency_days': 30,
                    'default_priority': 'medium',
                    'default_duration_hours': 1,
                },
            ],
            'breaker': [
                {
                    'activity_type': activity_types['annual_inspection'],
                    'frequency': 'annual',
                    'frequency_days': 365,
                    'default_priority': 'high',
                    'default_duration_hours': 4,
                },
                {
                    'activity_type': activity_types['quarterly_check'],
                    'frequency': 'quarterly',
                    'frequency_days': 90,
                    'default_priority': 'medium',
                    'default_duration_hours': 2,
                },
            ],
            'relay': [
                {
                    'activity_type': activity_types['annual_inspection'],
                    'frequency': 'annual',
                    'frequency_days': 365,
                    'default_priority': 'high',
                    'default_duration_hours': 3,
                },
                {
                    'activity_type': activity_types['quarterly_check'],
                    'frequency': 'quarterly',
                    'frequency_days': 90,
                    'default_priority': 'medium',
                    'default_duration_hours': 1,
                },
            ],
            'motor': [
                {
                    'activity_type': activity_types['annual_inspection'],
                    'frequency': 'annual',
                    'frequency_days': 365,
                    'default_priority': 'medium',
                    'default_duration_hours': 3,
                },
                {
                    'activity_type': activity_types['quarterly_check'],
                    'frequency': 'quarterly',
                    'frequency_days': 90,
                    'default_priority': 'medium',
                    'default_duration_hours': 2,
                },
                {
                    'activity_type': activity_types['monthly_inspection'],
                    'frequency': 'monthly',
                    'frequency_days': 30,
                    'default_priority': 'low',
                    'default_duration_hours': 1,
                },
            ],
        }
        
        # Create category schedules
        for category in categories:
            category_name_lower = category.name.lower()
            
            # Find matching schedule template
            schedule_template = None
            for template_key in category_schedules:
                if template_key in category_name_lower:
                    schedule_template = category_schedules[template_key]
                    break
            
            # If no specific template, use generic
            if not schedule_template:
                schedule_template = [
                    {
                        'activity_type': activity_types['annual_inspection'],
                        'frequency': 'annual',
                        'frequency_days': 365,
                        'default_priority': 'medium',
                        'default_duration_hours': 2,
                    },
                    {
                        'activity_type': activity_types['quarterly_check'],
                        'frequency': 'quarterly',
                        'frequency_days': 90,
                        'default_priority': 'medium',
                        'default_duration_hours': 1,
                    },
                ]
            
            # Create schedules for this category
            for schedule_data in schedule_template:
                schedule, created = EquipmentCategorySchedule.objects.get_or_create(
                    equipment_category=category,
                    activity_type=schedule_data['activity_type'],
                    defaults={
                        'frequency': schedule_data['frequency'],
                        'frequency_days': schedule_data['frequency_days'],
                        'auto_generate': True,
                        'advance_notice_days': 7,
                        'is_mandatory': True,
                        'is_active': True,
                        'allow_override': True,
                        'default_priority': schedule_data['default_priority'],
                        'default_duration_hours': schedule_data['default_duration_hours'],
                        'created_by': admin_user,
                    }
                )
                
                if created:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Created category schedule: {category.name} - {schedule_data["activity_type"].name}'
                        )
                    )
                elif options['force']:
                    # Update existing schedule
                    schedule.frequency = schedule_data['frequency']
                    schedule.frequency_days = schedule_data['frequency_days']
                    schedule.default_priority = schedule_data['default_priority']
                    schedule.default_duration_hours = schedule_data['default_duration_hours']
                    schedule.save()
                    self.stdout.write(
                        self.style.WARNING(
                            f'Updated category schedule: {category.name} - {schedule_data["activity_type"].name}'
                        )
                    )
        
        # Create global schedules
        global_schedules = [
            {
                'name': 'Safety Equipment Check',
                'activity_type': activity_types['monthly_inspection'],
                'frequency': 'monthly',
                'frequency_days': 30,
                'description': 'Monthly check of safety equipment and emergency systems',
                'default_priority': 'high',
                'default_duration_hours': 1,
            },
            {
                'name': 'Emergency System Test',
                'activity_type': activity_types['quarterly_check'],
                'frequency': 'quarterly',
                'frequency_days': 90,
                'description': 'Quarterly test of emergency systems and backup equipment',
                'default_priority': 'high',
                'default_duration_hours': 2,
            },
        ]
        
        for schedule_data in global_schedules:
            schedule, created = GlobalSchedule.objects.get_or_create(
                name=schedule_data['name'],
                defaults={
                    'activity_type': schedule_data['activity_type'],
                    'frequency': schedule_data['frequency'],
                    'frequency_days': schedule_data['frequency_days'],
                    'description': schedule_data['description'],
                    'auto_generate': True,
                    'advance_notice_days': 7,
                    'is_mandatory': True,
                    'is_active': True,
                    'allow_override': True,
                    'default_priority': schedule_data['default_priority'],
                    'default_duration_hours': schedule_data['default_duration_hours'],
                    'created_by': admin_user,
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Created global schedule: {schedule_data["name"]}'
                    )
                )
            elif options['force']:
                # Update existing schedule
                schedule.frequency = schedule_data['frequency']
                schedule.frequency_days = schedule_data['frequency_days']
                schedule.default_priority = schedule_data['default_priority']
                schedule.default_duration_hours = schedule_data['default_duration_hours']
                schedule.save()
                self.stdout.write(
                    self.style.WARNING(
                        f'Updated global schedule: {schedule_data["name"]}'
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully set up default schedules! '
                f'Created {EquipmentCategorySchedule.objects.count()} category schedules and '
                f'{GlobalSchedule.objects.count()} global schedules.'
            )
        ) 