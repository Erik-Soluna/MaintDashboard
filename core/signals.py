"""
Django signals for core app.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile
import logging

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