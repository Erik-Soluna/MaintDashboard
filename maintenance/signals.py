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
                event_type='maintenance',
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
    except Exception as e:
        logger.error(f"Error deleting calendar event for maintenance activity {instance.id}: {str(e)}")
