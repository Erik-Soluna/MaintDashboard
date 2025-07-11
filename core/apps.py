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
            # Check if the database is ready by checking if our tables exist
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='core_permission'
                    UNION ALL
                    SELECT tablename FROM pg_tables 
                    WHERE tablename='core_permission'
                """)
                if cursor.fetchone():
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