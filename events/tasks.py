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
    from datetime import timedelta
    
    tomorrow = timezone.now().date() + timedelta(days=1)
    upcoming_events = CalendarEvent.objects.filter(
        event_date=tomorrow,
        is_completed=False,
        assigned_to__isnull=False
    ).select_related('assigned_to', 'equipment')
    
    reminders_sent = 0
    for event in upcoming_events:
        try:
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
    """Clean up old completed events."""
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
    
    logger.info(f"Cleaned up {deleted_count} old completed events")
    return deleted_count


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
            event = CalendarEvent.objects.create(
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
                created_by_id=1  # System user
            )
            created_count += 1
            logger.info(f"Created calendar event for maintenance activity: {activity.title}")
        except Exception as e:
            logger.error(f"Error creating calendar event for activity {activity.id}: {str(e)}")
    
    logger.info(f"Generated {created_count} calendar events from maintenance activities")
    return created_count