"""
Django signals for events app.
"""

from django.db.models.signals import post_delete
from django.dispatch import receiver
from .models import CalendarEvent
import logging

logger = logging.getLogger(__name__)


@receiver(post_delete, sender=CalendarEvent)
def invalidate_dashboard_cache_on_event_delete(sender, instance, **kwargs):
    """Invalidate dashboard cache when a calendar event is deleted."""
    try:
        from core.views import invalidate_dashboard_cache
        
        # Invalidate dashboard cache for all users since calendar events affect dashboard data
        invalidate_dashboard_cache()
        logger.info(f"Invalidated dashboard cache after deleting calendar event {instance.id}")
        
    except Exception as e:
        logger.warning(f"Could not invalidate dashboard cache after deleting calendar event {instance.id}: {str(e)}")
