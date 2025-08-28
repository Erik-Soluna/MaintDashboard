"""
Management command to create maintenance schedules for existing activity types and equipment.
This command can be used to retroactively create schedules for existing data.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from maintenance.models import MaintenanceActivityType, MaintenanceSchedule
from equipment.models import Equipment
from datetime import date
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Create maintenance schedules for existing activity types and equipment'

    def add_arguments(self, parser):
        parser.add_argument(
            '--activity-type',
            type=str,
            help='Specific activity type name to process (optional)'
        )
        parser.add_argument(
            '--equipment-category',
            type=str,
            help='Specific equipment category name to process (optional)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating anything'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force creation even if schedules already exist'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']
        activity_type_name = options['activity_type']
        equipment_category_name = options['equipment_category']

        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )

        # Get activity types to process
        if activity_type_name:
            try:
                activity_types = [MaintenanceActivityType.objects.get(name=activity_type_name)]
                self.stdout.write(f'Processing specific activity type: {activity_type_name}')
            except MaintenanceActivityType.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Activity type "{activity_type_name}" not found')
                )
                return
        else:
            activity_types = MaintenanceActivityType.objects.filter(is_active=True)
            self.stdout.write(f'Processing {activity_types.count()} active activity types')

        # Get equipment categories to process
        if equipment_category_name:
            try:
                from core.models import EquipmentCategory
                equipment_categories = [EquipmentCategory.objects.get(name=equipment_category_name)]
                self.stdout.write(f'Processing specific equipment category: {equipment_category_name}')
            except EquipmentCategory.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Equipment category "{equipment_category_name}" not found')
                )
                return
        else:
            from core.models import EquipmentCategory
            equipment_categories = EquipmentCategory.objects.filter(is_active=True)
            self.stdout.write(f'Processing {equipment_categories.count()} active equipment categories')

        total_created = 0
        total_updated = 0
        total_skipped = 0

        with transaction.atomic():
            for activity_type in activity_types:
                self.stdout.write(f'\nProcessing activity type: {activity_type.name}')
                
                # Get applicable equipment for this activity type
                if equipment_category_name:
                    # Filter by specific category if specified
                    applicable_equipment = Equipment.objects.filter(
                        category__in=equipment_categories,
                        category__in=activity_type.applicable_equipment_categories.all(),
                        is_active=True
                    )
                else:
                    # Get all applicable equipment
                    applicable_equipment = Equipment.objects.filter(
                        category__in=activity_type.applicable_equipment_categories.all(),
                        is_active=True
                    )

                self.stdout.write(f'  Found {applicable_equipment.count()} applicable equipment items')

                for equipment in applicable_equipment:
                    # Check if schedule already exists
                    existing_schedule = MaintenanceSchedule.objects.filter(
                        equipment=equipment,
                        activity_type=activity_type
                    ).first()

                    if existing_schedule and not force:
                        self.stdout.write(
                            f'    Skipping {equipment.name} - schedule already exists'
                        )
                        total_skipped += 1
                        continue

                    # Convert frequency_days to frequency choice
                    frequency = 'custom'
                    if activity_type.frequency_days == 1:
                        frequency = 'daily'
                    elif activity_type.frequency_days == 7:
                        frequency = 'weekly'
                    elif activity_type.frequency_days == 30:
                        frequency = 'monthly'
                    elif activity_type.frequency_days == 90:
                        frequency = 'quarterly'
                    elif activity_type.frequency_days == 180:
                        frequency = 'semi_annual'
                    elif activity_type.frequency_days == 365:
                        frequency = 'annual'

                    if existing_schedule:
                        # Update existing schedule
                        if not dry_run:
                            existing_schedule.frequency = frequency
                            existing_schedule.frequency_days = activity_type.frequency_days
                            existing_schedule.save()
                        
                        self.stdout.write(
                            f'    Updated schedule for {equipment.name} - {activity_type.name}'
                        )
                        total_updated += 1
                    else:
                        # Create new schedule
                        if not dry_run:
                            schedule = MaintenanceSchedule.objects.create(
                                equipment=equipment,
                                activity_type=activity_type,
                                frequency=frequency,
                                frequency_days=activity_type.frequency_days,
                                start_date=date.today(),
                                auto_generate=True,
                                advance_notice_days=7,
                                is_active=True,
                                created_by=activity_type.created_by
                            )
                        
                        self.stdout.write(
                            f'    Created schedule for {equipment.name} - {activity_type.name}'
                        )
                        total_created += 1

        # Summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write('SUMMARY')
        self.stdout.write('='*50)
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'DRY RUN - Would create {total_created} schedules')
            )
            self.stdout.write(
                self.style.WARNING(f'DRY RUN - Would update {total_updated} schedules')
            )
            self.stdout.write(
                self.style.WARNING(f'DRY RUN - Would skip {total_skipped} existing schedules')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Created {total_created} new schedules')
            )
            self.stdout.write(
                self.style.SUCCESS(f'Updated {total_updated} existing schedules')
            )
            self.stdout.write(
                self.style.WARNING(f'Skipped {total_skipped} existing schedules')
            )

        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS('\nMaintenance schedules created/updated successfully!')
            )
        else:
            self.stdout.write(
                self.style.WARNING('\nRun without --dry-run to actually create the schedules')
            )
