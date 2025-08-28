"""
Django signals for maintenance app.
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from .models import MaintenanceActivity
from events.models import CalendarEvent
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=MaintenanceActivity)
def create_or_update_calendar_event(sender, instance, created, **kwargs):
    """Create or update a calendar event when a maintenance activity is created or updated."""
    try:
        if created:
            # Create new calendar event
            calendar_event = CalendarEvent.objects.create(
                title=instance.title,
                description=instance.description or f"Maintenance activity: {instance.title}",
                event_date=instance.scheduled_start.date() if instance.scheduled_start else timezone.now().date(),
                start_time=instance.scheduled_start.time() if instance.scheduled_start else None,
                end_time=instance.scheduled_end.time() if instance.scheduled_end else None,
                event_type=f'activity_{instance.activity_type.id}',
                equipment=instance.equipment,
                assigned_to=instance.assigned_to,
                created_by=instance.created_by,
                all_day=False,
                # Store reference to maintenance activity
                maintenance_activity=instance
            )
            logger.info(f"Created calendar event {calendar_event.id} for maintenance activity {instance.id}")
        else:
            # Update existing calendar event
            try:
                calendar_event = CalendarEvent.objects.get(maintenance_activity=instance)
                calendar_event.title = instance.title
                calendar_event.description = instance.description or f"Maintenance activity: {instance.title}"
                calendar_event.event_date = instance.scheduled_start.date() if instance.scheduled_start else timezone.now().date()
                calendar_event.start_time = instance.scheduled_start.time() if instance.scheduled_start else None
                calendar_event.end_time = instance.scheduled_end.time() if instance.scheduled_end else None
                calendar_event.event_type = f'activity_{instance.activity_type.id}'
                calendar_event.equipment = instance.equipment
                calendar_event.assigned_to = instance.assigned_to
                calendar_event.save()
                logger.info(f"Updated calendar event {calendar_event.id} for maintenance activity {instance.id}")
            except CalendarEvent.DoesNotExist:
                # If no calendar event exists, create one
                create_or_update_calendar_event(sender, instance, True, **kwargs)
                
    except Exception as e:
        logger.error(f"Error creating/updating calendar event for maintenance activity {instance.id}: {str(e)}")


@receiver(post_delete, sender=MaintenanceActivity)
def delete_calendar_event(sender, instance, **kwargs):
    """Delete the associated calendar event when a maintenance activity is deleted."""
    try:
        calendar_event = CalendarEvent.objects.filter(maintenance_activity=instance).first()
        if calendar_event:
            calendar_event.delete()
            logger.info(f"Deleted calendar event {calendar_event.id} for maintenance activity {instance.id}")
        
        # Invalidate dashboard cache for all users since maintenance activities affect dashboard data
        try:
            from core.views import invalidate_dashboard_cache
            invalidate_dashboard_cache()  # Invalidate all dashboard caches
        except Exception as cache_error:
            logger.warning(f"Could not invalidate dashboard cache: {cache_error}")
            
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
            
            MaintenanceTimelineEntry.objects.create(
                activity=instance,
                entry_type='status_change',
                title=f'Status Changed to {status_display}',
                description=f'Activity status changed from {old_status_display} to {status_display}',
                created_by=instance.updated_by or instance.created_by
            )
        
        # Check for actual start changes
        old_actual_start = getattr(instance, '_old_actual_start', None)
        if old_actual_start is None and instance.actual_start:
            MaintenanceTimelineEntry.objects.create(
                activity=instance,
                entry_type='started',
                title='Activity Started',
                description=f'Maintenance activity started at {instance.actual_start.strftime("%Y-%m-%d %H:%M")}',
                created_by=instance.updated_by or instance.created_by
            )
        
        # Check for actual end changes
        old_actual_end = getattr(instance, '_old_actual_end', None)
        if old_actual_end is None and instance.actual_end:
            MaintenanceTimelineEntry.objects.create(
                activity=instance,
                entry_type='completed',
                title='Activity Completed',
                description=f'Maintenance activity completed at {instance.actual_end.strftime("%Y-%m-%d %H:%M")}',
                created_by=instance.updated_by or instance.created_by
            )
        
        # Check for assignment changes
        old_assigned_to = getattr(instance, '_old_assigned_to', None)
        if old_assigned_to != instance.assigned_to:
            if instance.assigned_to:
                MaintenanceTimelineEntry.objects.create(
                    activity=instance,
                    entry_type='assigned',
                    title='Activity Assigned',
                    description=f'Activity assigned to {instance.assigned_to.get_full_name() or instance.assigned_to.username}',
                    created_by=instance.updated_by or instance.created_by
                )
            else:
                MaintenanceTimelineEntry.objects.create(
                    activity=instance,
                    entry_type='unassigned',
                    title='Activity Unassigned',
                    description='Activity assignment was removed',
                    created_by=instance.updated_by or instance.created_by
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
