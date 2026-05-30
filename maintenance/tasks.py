"""
Celery tasks for maintenance app.
"""

from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


@shared_task
def generate_scheduled_maintenance():
    """Generate maintenance activities from schedules."""
    from .models import MaintenanceSchedule
    
    generated_count = 0
    schedules = MaintenanceSchedule.objects.filter(
        is_active=True,
        auto_generate=True
    )
    
    for schedule in schedules:
        try:
            activity = schedule.generate_next_activity()
            if activity:
                generated_count += 1
                logger.info(f"Generated maintenance activity: {activity.title}")
        except Exception as e:
            logger.error(f"Error generating activity for schedule {schedule.id}: {str(e)}")
    
    logger.info(f"Generated {generated_count} maintenance activities")
    return generated_count


@shared_task
def send_maintenance_reminders():
    """Send reminders for upcoming maintenance activities."""
    from .models import MaintenanceActivity
    from .utils import local_date_tomorrow
    from datetime import timedelta

    # scheduled_start is UTC; "tomorrow" must be evaluated in each activity's
    # local timezone. Query a small UTC window, then match the local date.
    now = timezone.now()
    candidate_activities = MaintenanceActivity.objects.filter(
        scheduled_start__gte=now - timedelta(days=1),
        scheduled_start__lt=now + timedelta(days=2),
        status='scheduled',
        assigned_to__isnull=False
    ).select_related('assigned_to', 'equipment')

    reminders_sent = 0
    for activity in candidate_activities:
        try:
            start_local = activity.get_scheduled_start_in_timezone()
            if not start_local or start_local.date() != local_date_tomorrow(activity.timezone):
                continue
            if activity.assigned_to.email:
                send_mail(
                    subject=f"Maintenance Reminder: {activity.title}",
                    message=f"You have a maintenance activity scheduled for tomorrow:\n\n"
                           f"Title: {activity.title}\n"
                           f"Equipment: {activity.equipment.name}\n"
                           f"Scheduled: {start_local.strftime('%Y-%m-%d %I:%M %p')} ({activity.timezone})\n",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[activity.assigned_to.email],
                    fail_silently=False,
                )
                reminders_sent += 1
                logger.info(f"Sent reminder to {activity.assigned_to.email} for {activity.title}")
        except Exception as e:
            logger.error(f"Error sending reminder for activity {activity.id}: {str(e)}")
    
    logger.info(f"Sent {reminders_sent} maintenance reminders")
    return reminders_sent


@shared_task
def check_overdue_maintenance():
    """Check for overdue maintenance and create alerts."""
    from .models import MaintenanceActivity
    
    overdue_activities = MaintenanceActivity.objects.filter(
        scheduled_end__lt=timezone.now(),
        status__in=['scheduled', 'pending', 'in_progress']
    ).select_related('equipment', 'assigned_to')
    
    overdue_count = overdue_activities.count()
    
    if overdue_count > 0:
        logger.warning(f"Found {overdue_count} overdue maintenance activities")
        # Here you could send notifications to supervisors, create alerts, etc.
    
    return overdue_count