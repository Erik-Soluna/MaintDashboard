"""
Django signals for core app.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in
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
                
            # Check if password was changed and clear force_password_change flag
            if hasattr(instance, '_password_changed') and instance._password_changed:
                if hasattr(instance, 'userprofile') and instance.userprofile:
                    instance.userprofile.clear_force_password_change()
                    logger.info(f"Cleared force_password_change for user: {instance.username}")
                    
    except Exception as e:
        logger.error(f"Error creating/updating UserProfile for user {instance.username}: {str(e)}")


@receiver(user_logged_in)
def handle_user_login(sender, request, user, **kwargs):
    """Handle user login and update last_login, clear force_password_change if needed."""
    try:
        # Ensure user profile exists
        profile, created = UserProfile.objects.get_or_create(user=user)
        
        # If this is the first login and user has changed password, clear the flag
        if user.last_login is None and not getattr(profile, 'force_password_change', False):
            # User has successfully logged in for the first time
            logger.info(f"First login completed for user: {user.username}")
            
    except Exception as e:
        logger.error(f"Error handling login for user {user.username}: {str(e)}")