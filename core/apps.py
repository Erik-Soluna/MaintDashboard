from django.apps import AppConfig
from django.db import connection
from django.db.utils import OperationalError


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'Core Functionality'

    def ready(self):
        """Import signals and initialize RBAC when the app is ready."""
        import core.signals
        
        # Initialize permissions on startup (only after migrations)
        try:
            # Check if the database is ready by checking if our models are available
            from django.db import models
            from core.models import Permission
            
            # Try to access the Permission model to see if tables exist
            Permission.objects.exists()
            
            # Database tables exist, safe to initialize permissions
            self._initialize_permissions()
        except (OperationalError, Exception):
            # Database not ready or other error, skip initialization
            pass

    def _initialize_permissions(self):
        """Initialize default permissions."""
        try:
            from core.rbac import initialize_default_permissions
            initialize_default_permissions()
        except Exception as e:
            # Don't fail the app startup if permission initialization fails
            print(f"Warning: Could not initialize permissions: {e}")