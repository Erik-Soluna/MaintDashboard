"""
Django signals for core app.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile
import logging
from events.models import CalendarEvent
from maintenance.models import MaintenanceActivity, MaintenanceActivityType
from django.db import transaction
from datetime import datetime
from django.utils import timezone

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """Create or update a UserProfile when a User is created or updated."""
    try:
        if created:
            # User was just created, create a new UserProfile
            UserProfile.objects.get_or_create(user=instance)
            logger.info(f"Created UserProfile for new user: {instance.username}")
        else:
            # User was updated, ensure UserProfile exists
            profile, profile_created = UserProfile.objects.get_or_create(user=instance)
            if profile_created:
                logger.info(f"Created missing UserProfile for existing user: {instance.username}")
    except Exception as e:
        logger.error(f"Error creating/updating UserProfile for user {instance.username}: {str(e)}")


@receiver(post_save, sender=CalendarEvent)
def sync_maintenance_activity_from_event(sender, instance, created, **kwargs):
    """Ensure every CalendarEvent of type 'maintenance' has a linked MaintenanceActivity."""
    if instance.event_type != 'maintenance':
        return
    # Avoid recursion: if already linked, update the activity
    if instance.maintenance_activity:
        activity = instance.maintenance_activity
        activity.title = instance.title
        activity.description = instance.description
        activity.equipment = instance.equipment
        activity.scheduled_start = (
            instance.event_date if instance.start_time is None else
            timezone.make_aware(datetime.combine(instance.event_date, instance.start_time))
        )
        activity.scheduled_end = (
            instance.event_date if instance.end_time is None else
            timezone.make_aware(datetime.combine(instance.event_date, instance.end_time))
        )
        activity.priority = instance.priority
        activity.assigned_to = instance.assigned_to
        activity.status = 'completed' if instance.is_completed else 'scheduled'
        activity.save()
    else:
        # Find a default activity type (or create one if needed)
        activity_type = MaintenanceActivityType.objects.filter(is_active=True).first()
        if not activity_type:
            activity_type = MaintenanceActivityType.objects.create(
                name='Default',
                category=MaintenanceActivityType._meta.get_field('category').related_model.objects.first(),
                description='Default maintenance activity type',
                frequency_days=365,
            )
        activity = MaintenanceActivity.objects.create(
            title=instance.title,
            description=instance.description,
            equipment=instance.equipment,
            activity_type=activity_type,
            scheduled_start=(
                instance.event_date if instance.start_time is None else
                timezone.make_aware(datetime.combine(instance.event_date, instance.start_time))
            ),
            scheduled_end=(
                instance.event_date if instance.end_time is None else
                timezone.make_aware(datetime.combine(instance.event_date, instance.end_time))
            ),
            priority=instance.priority,
            assigned_to=instance.assigned_to,
            status='completed' if instance.is_completed else 'scheduled',
            created_by=instance.created_by if hasattr(instance, 'created_by') else None,
        )
        # Link the event to the activity
        with transaction.atomic():
            instance.maintenance_activity = activity
            instance.save(update_fields=['maintenance_activity'])