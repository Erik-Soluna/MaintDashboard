"""
Django signals for maintenance app.
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from .models import MaintenanceActivity, MaintenanceActivityType, MaintenanceSchedule
from events.models import CalendarEvent
import logging

logger = logging.getLogger(__name__)


# DISABLED: Calendar events are no longer used - only maintenance activities are used
# @receiver(post_save, sender=MaintenanceActivity)
# def create_or_update_calendar_event(sender, instance, created, **kwargs):
#     """Create or update a calendar event when a maintenance activity is created or updated."""
#     try:
#         if created:
#             # Create new calendar event
#             calendar_event = CalendarEvent.objects.create(
#                 title=instance.title,
#                 description=instance.description or f"Maintenance activity: {instance.title}",
#                 event_date=instance.scheduled_start.date() if instance.scheduled_start else timezone.now().date(),
#                 start_time=instance.scheduled_start.time() if instance.scheduled_start else None,
#                 end_time=instance.scheduled_end.time() if instance.scheduled_end else None,
#                 event_type=f'activity_{instance.activity_type.id}',
#                 equipment=instance.equipment,
#                 assigned_to=instance.assigned_to,
#                 created_by=instance.created_by,
#                 all_day=False,
#                 # Store reference to maintenance activity
#                 maintenance_activity=instance
#             )
#             logger.info(f"Created calendar event {calendar_event.id} for maintenance activity {instance.id}")
#         else:
#             # Update existing calendar event
#             try:
#                 calendar_event = CalendarEvent.objects.get(maintenance_activity=instance)
#                 calendar_event.title = instance.title
#                 calendar_event.description = instance.description or f"Maintenance activity: {instance.title}"
#                 calendar_event.event_date = instance.scheduled_start.date() if instance.scheduled_start else timezone.now().date()
#                 calendar_event.start_time = instance.scheduled_start.time() if instance.scheduled_start else None
#                 calendar_event.end_time = instance.scheduled_end.time() if instance.scheduled_end else None
#                 calendar_event.event_type = f'activity_{instance.activity_type.id}'
#                 calendar_event.equipment = instance.equipment
#                 calendar_event.assigned_to = instance.assigned_to
#                 calendar_event.save()
#                 logger.info(f"Updated calendar event {calendar_event.id} for maintenance activity {instance.id}")
#             except CalendarEvent.DoesNotExist:
#                 # If no calendar event exists, create one
#                 create_or_update_calendar_event(sender, instance, True, **kwargs)
#                 
#     except Exception as e:
#         logger.error(f"Error creating/updating calendar event for maintenance activity {instance.id}: {str(e)}")


@receiver(post_delete, sender=MaintenanceActivity)
def delete_calendar_event(sender, instance, **kwargs):
    """Delete the associated calendar event when a maintenance activity is deleted."""
    try:
        # Use get() instead of filter().first() for better performance
        # If calendar event doesn't exist, that's fine - it may have been deleted already
        try:
            calendar_event = CalendarEvent.objects.get(maintenance_activity=instance)
            calendar_event.delete()
            logger.info(f"Deleted calendar event {calendar_event.id} for maintenance activity {instance.id}")
        except CalendarEvent.DoesNotExist:
            # Calendar event may have been deleted already or never existed
            pass
        
        # Note: Cache invalidation is handled in the view for better performance
        # (targeted to specific user rather than all users)
            
    except Exception as e:
        logger.error(f"Error deleting calendar event for maintenance activity {instance.id}: {str(e)}")

"""
Signals for maintenance app to automatically create timeline entries.
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import MaintenanceActivity, MaintenanceTimelineEntry, MaintenanceReport


@receiver(pre_save, sender=MaintenanceActivity)
def maintenance_activity_pre_save(sender, instance, **kwargs):
    """Track changes before saving maintenance activity."""
    if instance.pk:  # Only for existing instances
        try:
            old_instance = MaintenanceActivity.objects.get(pk=instance.pk)
            instance._old_status = old_instance.status
            instance._old_actual_start = old_instance.actual_start
            instance._old_actual_end = old_instance.actual_end
            instance._old_assigned_to = old_instance.assigned_to
        except MaintenanceActivity.DoesNotExist:
            pass


@receiver(post_save, sender=MaintenanceActivity)
def maintenance_activity_post_save(sender, instance, created, **kwargs):
    """Create timeline entries for maintenance activity changes."""
    if created:
        # Create initial timeline entry for new activity
        MaintenanceTimelineEntry.objects.create(
            activity=instance,
            entry_type='created',
            title='Activity Created',
            description=f'Maintenance activity "{instance.title}" was created and scheduled for {instance.scheduled_start.strftime("%Y-%m-%d %H:%M")}',
            created_by=instance.created_by
        )
    else:
        # Check for status changes
        old_status = getattr(instance, '_old_status', None)
        if old_status and old_status != instance.status:
            status_display = instance.get_status_display()
            old_status_display = dict(MaintenanceActivity.STATUS_CHOICES).get(old_status, old_status)
            
            # Use get_or_create to prevent duplicates if the same status change happens multiple times
            MaintenanceTimelineEntry.objects.get_or_create(
                activity=instance,
                entry_type='status_change',
                title=f'Status Changed to {status_display}',
                defaults={
                    'description': f'Activity status changed from {old_status_display} to {status_display}',
                    'created_by': instance.updated_by or instance.created_by
                }
            )
        
        # Check for actual start changes
        old_actual_start = getattr(instance, '_old_actual_start', None)
        if old_actual_start is None and instance.actual_start:
            # Use get_or_create to prevent duplicates
            MaintenanceTimelineEntry.objects.get_or_create(
                activity=instance,
                entry_type='started',
                defaults={
                    'title': 'Activity Started',
                    'description': f'Maintenance activity started at {instance.actual_start.strftime("%Y-%m-%d %H:%M")}',
                    'created_by': instance.updated_by or instance.created_by
                }
            )
        
        # Check for actual end changes
        old_actual_end = getattr(instance, '_old_actual_end', None)
        if old_actual_end is None and instance.actual_end:
            # Use get_or_create to prevent duplicates
            MaintenanceTimelineEntry.objects.get_or_create(
                activity=instance,
                entry_type='completed',
                defaults={
                    'title': 'Activity Completed',
                    'description': f'Maintenance activity completed at {instance.actual_end.strftime("%Y-%m-%d %H:%M")}',
                    'created_by': instance.updated_by or instance.created_by
                }
            )
        
        # Check for assignment changes
        old_assigned_to = getattr(instance, '_old_assigned_to', None)
        if old_assigned_to != instance.assigned_to:
            if instance.assigned_to:
                # Use get_or_create to prevent duplicates
                MaintenanceTimelineEntry.objects.get_or_create(
                    activity=instance,
                    entry_type='assigned',
                    defaults={
                        'title': 'Activity Assigned',
                        'description': f'Activity assigned to {instance.assigned_to.get_full_name() or instance.assigned_to.username}',
                        'created_by': instance.updated_by or instance.created_by
                    }
                )
            else:
                # Use get_or_create to prevent duplicates
                MaintenanceTimelineEntry.objects.get_or_create(
                    activity=instance,
                    entry_type='unassigned',
                    defaults={
                        'title': 'Activity Unassigned',
                        'description': 'Activity assignment was removed',
                        'created_by': instance.updated_by or instance.created_by
                    }
                )


@receiver(post_save, sender=MaintenanceReport)
def maintenance_report_post_save(sender, instance, created, **kwargs):
    """Create timeline entry when maintenance report is uploaded."""
    if created:
        MaintenanceTimelineEntry.objects.create(
            activity=instance.maintenance_activity,
            entry_type='report_uploaded',
            title=f'{instance.get_report_type_display()} Uploaded',
            description=f'Report "{instance.title}" was uploaded by {instance.created_by.get_full_name() or instance.created_by.username}',
            created_by=instance.created_by
        )


# Signals for MaintenanceActivityType to auto-populate schedules
@receiver(post_save, sender=MaintenanceActivityType)
def create_maintenance_schedules_for_activity_type(sender, instance, created, **kwargs):
    """Automatically create maintenance schedules when a new activity type is created."""
    if created and instance.is_active:
        try:
            from equipment.models import Equipment
            from datetime import date
            
            # Get all equipment in the applicable categories
            applicable_equipment = Equipment.objects.filter(
                category__in=instance.applicable_equipment_categories.all(),
                is_active=True
            )
            
            created_schedules = []
            for equipment in applicable_equipment:
                # Check if schedule already exists for this equipment and activity type
                existing_schedule = MaintenanceSchedule.objects.filter(
                    equipment=equipment,
                    activity_type=instance
                ).first()
                
                if not existing_schedule:
                    # Convert frequency_days to frequency choice
                    frequency = 'custom'
                    if instance.frequency_days == 1:
                        frequency = 'daily'
                    elif instance.frequency_days == 7:
                        frequency = 'weekly'
                    elif instance.frequency_days == 30:
                        frequency = 'monthly'
                    elif instance.frequency_days == 90:
                        frequency = 'quarterly'
                    elif instance.frequency_days == 180:
                        frequency = 'semi_annual'
                    elif instance.frequency_days == 365:
                        frequency = 'annual'
                    
                    # Create the schedule
                    schedule = MaintenanceSchedule.objects.create(
                        equipment=equipment,
                        activity_type=instance,
                        frequency=frequency,
                        frequency_days=instance.frequency_days,
                        start_date=date.today(),
                        auto_generate=True,
                        advance_notice_days=7,
                        is_active=True,
                        created_by=instance.created_by
                    )
                    created_schedules.append(schedule)
                    logger.info(f"Created maintenance schedule for {equipment.name} - {instance.name}")
            
            if created_schedules:
                logger.info(f"Created {len(created_schedules)} maintenance schedules for activity type {instance.name}")
                
        except Exception as e:
            logger.error(f"Error creating maintenance schedules for activity type {instance.id}: {str(e)}")


@receiver(post_save, sender=MaintenanceActivityType)
def update_maintenance_schedules_for_activity_type(sender, instance, created, **kwargs):
    """Update maintenance schedules when an activity type is modified."""
    if not created and instance.is_active:
        try:
            from equipment.models import Equipment
            from datetime import date
            
            # Get current applicable equipment categories
            current_categories = set(instance.applicable_equipment_categories.all())
            
            # Get all equipment in the current applicable categories
            applicable_equipment = Equipment.objects.filter(
                category__in=current_categories,
                is_active=True
            )
            
            # Create schedules for equipment that doesn't have them yet
            created_schedules = []
            for equipment in applicable_equipment:
                existing_schedule = MaintenanceSchedule.objects.filter(
                    equipment=equipment,
                    activity_type=instance
                ).first()
                
                if not existing_schedule:
                    # Convert frequency_days to frequency choice
                    frequency = 'custom'
                    if instance.frequency_days == 1:
                        frequency = 'daily'
                    elif instance.frequency_days == 7:
                        frequency = 'weekly'
                    elif instance.frequency_days == 30:
                        frequency = 'monthly'
                    elif instance.frequency_days == 90:
                        frequency = 'quarterly'
                    elif instance.frequency_days == 180:
                        frequency = 'semi_annual'
                    elif instance.frequency_days == 365:
                        frequency = 'annual'
                    
                    # Create the schedule
                    schedule = MaintenanceSchedule.objects.create(
                        equipment=equipment,
                        activity_type=instance,
                        frequency=frequency,
                        frequency_days=instance.frequency_days,
                        start_date=date.today(),
                        auto_generate=True,
                        advance_notice_days=7,
                        is_active=True,
                        created_by=instance.updated_by or instance.created_by
                    )
                    created_schedules.append(schedule)
                    logger.info(f"Created maintenance schedule for {equipment.name} - {instance.name}")
            
            # Update existing schedules with new frequency information
            updated_schedules = []
            existing_schedules = MaintenanceSchedule.objects.filter(activity_type=instance)
            for schedule in existing_schedules:
                # Convert frequency_days to frequency choice
                frequency = 'custom'
                if instance.frequency_days == 1:
                    frequency = 'daily'
                elif instance.frequency_days == 7:
                    frequency = 'weekly'
                elif instance.frequency_days == 30:
                    frequency = 'monthly'
                elif instance.frequency_days == 90:
                    frequency = 'quarterly'
                elif instance.frequency_days == 180:
                    frequency = 'semi_annual'
                elif instance.frequency_days == 365:
                    frequency = 'annual'
                
                # Update frequency if it changed
                if schedule.frequency != frequency or schedule.frequency_days != instance.frequency_days:
                    schedule.frequency = frequency
                    schedule.frequency_days = instance.frequency_days
                    schedule.updated_by = instance.updated_by or instance.created_by
                    schedule.save()
                    updated_schedules.append(schedule)
                    logger.info(f"Updated maintenance schedule for {schedule.equipment.name} - {instance.name}")
            
            if created_schedules or updated_schedules:
                logger.info(f"Updated {len(created_schedules)} new and {len(updated_schedules)} existing maintenance schedules for activity type {instance.name}")
                
        except Exception as e:
            logger.error(f"Error updating maintenance schedules for activity type {instance.id}: {str(e)}")


# Signal for Equipment to create schedules when equipment is added to applicable categories
@receiver(post_save, sender='equipment.Equipment')
def create_maintenance_schedules_for_equipment(sender, instance, created, **kwargs):
    """Create maintenance schedules when equipment is added to a category with applicable activity types."""
    if created and instance.is_active and instance.category:
        try:
            from maintenance.models import MaintenanceActivityType
            
            # Get all active activity types that apply to this equipment's category
            applicable_activity_types = MaintenanceActivityType.objects.filter(
                applicable_equipment_categories=instance.category,
                is_active=True
            )
            
            created_schedules = []
            for activity_type in applicable_activity_types:
                # Check if schedule already exists
                existing_schedule = MaintenanceSchedule.objects.filter(
                    equipment=instance,
                    activity_type=activity_type
                ).first()
                
                if not existing_schedule:
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
                    
                    # Create the schedule
                    schedule = MaintenanceSchedule.objects.create(
                        equipment=instance,
                        activity_type=activity_type,
                        frequency=frequency,
                        frequency_days=activity_type.frequency_days,
                        start_date=timezone.now().date(),
                        auto_generate=True,
                        advance_notice_days=7,
                        is_active=True,
                        created_by=instance.created_by
                    )
                    created_schedules.append(schedule)
                    logger.info(f"Created maintenance schedule for {instance.name} - {activity_type.name}")
            
            if created_schedules:
                logger.info(f"Created {len(created_schedules)} maintenance schedules for new equipment {instance.name}")
                
        except Exception as e:
            logger.error(f"Error creating maintenance schedules for equipment {instance.id}: {str(e)}")
