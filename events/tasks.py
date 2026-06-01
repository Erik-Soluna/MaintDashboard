"""
Celery tasks for events app.
"""

from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


@shared_task
def send_event_reminders():
    """Send reminders for upcoming events."""
    from .models import CalendarEvent
    from maintenance.utils import local_date_tomorrow, DEFAULT_ACTIVITY_TIMEZONE
    from datetime import timedelta

    # event_date is stored in the activity's local timezone, so query a small
    # window in UTC-date terms and then match the exact local "tomorrow" per event.
    now = timezone.now()
    candidate_events = CalendarEvent.objects.filter(
        event_date__gte=(now - timedelta(days=1)).date(),
        event_date__lte=(now + timedelta(days=2)).date(),
        is_completed=False,
        assigned_to__isnull=False
    ).select_related('assigned_to', 'equipment', 'maintenance_activity')

    reminders_sent = 0
    for event in candidate_events:
        try:
            event_tz = (event.maintenance_activity.timezone
                        if event.maintenance_activity else DEFAULT_ACTIVITY_TIMEZONE)
            if event.event_date != local_date_tomorrow(event_tz):
                continue
            if event.assigned_to.email:
                send_mail(
                    subject=f"Event Reminder: {event.title}",
                    message=f"You have an event scheduled for tomorrow:\n\n"
                           f"Title: {event.title}\n"
                           f"Equipment: {event.equipment.name}\n"
                           f"Date: {event.event_date}\n"
                           f"Type: {event.get_event_type_display()}\n",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[event.assigned_to.email],
                    fail_silently=False,
                )
                reminders_sent += 1
                logger.info(f"Sent event reminder to {event.assigned_to.email} for {event.title}")
        except Exception as e:
            logger.error(f"Error sending event reminder for event {event.id}: {str(e)}")
    
    logger.info(f"Sent {reminders_sent} event reminders")
    return reminders_sent


@shared_task
def cleanup_old_events():
    """Clean up old completed events and orphaned calendar events.
    
    Orphaned calendar events are those with maintenance_activity=None, which can occur
    when maintenance activities are deleted but the calendar event deletion fails or
    when calendar events are created without proper linking.
    """
    from .models import CalendarEvent
    from datetime import timedelta
    
    # Remove completed events older than 1 year
    cutoff_date = timezone.now().date() - timedelta(days=365)
    old_events = CalendarEvent.objects.filter(
        event_date__lt=cutoff_date,
        is_completed=True
    )
    
    deleted_count = old_events.count()
    old_events.delete()
    
    # Clean up orphaned calendar events (those with maintenance_activity=None)
    # These are "ghost" events left behind when maintenance activities were deleted
    orphaned_events = CalendarEvent.objects.filter(maintenance_activity__isnull=True)
    orphaned_count = orphaned_events.count()
    orphaned_events.delete()
    
    total_deleted = deleted_count + orphaned_count
    logger.info(f"Cleaned up {deleted_count} old completed events and {orphaned_count} orphaned calendar events (total: {total_deleted})")
    return total_deleted


@shared_task  
def generate_maintenance_events():
    """Generate calendar events from maintenance activities."""
    from .models import CalendarEvent
    from maintenance.models import MaintenanceActivity
    
    created_count = 0
    
    # Find maintenance activities without corresponding calendar events
    activities = MaintenanceActivity.objects.filter(
        calendar_events__isnull=True,
        status='scheduled'
    ).select_related('equipment')
    
    for activity in activities:
        try:
            event = CalendarEvent(
                title=f"Maintenance: {activity.title}",
                description=activity.description,
                event_type='maintenance',
                equipment=activity.equipment,
                maintenance_activity=activity,
                assigned_to=activity.assigned_to,
                priority=activity.priority,
                created_by_id=1  # System user
            )
            # Project the activity's UTC times into the activity's local timezone.
            event.set_times_from_activity(activity)
            event.save()
            created_count += 1
            logger.info(f"Created calendar event for maintenance activity: {activity.title}")
        except Exception as e:
            logger.error(f"Error creating calendar event for activity {activity.id}: {str(e)}")
    
    logger.info(f"Generated {created_count} calendar events from maintenance activities")
    return created_count