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
            
            # Run comprehensive database check on startup
            self._ensure_database_tables()
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

    def _ensure_database_tables(self):
        """Ensure all required database tables exist on startup (optimized)."""
        try:
            from django.core.management import call_command
            from django.core.cache import cache
            from django.conf import settings
            import logging
            
            logger = logging.getLogger(__name__)
            
            # Skip if already checked in this process
            if hasattr(self, '_startup_checks_done'):
                return
            
            # Check if we're in a management command (avoid running during migrations)
            import sys
            if 'manage.py' in sys.argv and any('migrate' in arg for arg in sys.argv):
                return
            
            # Check cache backend
            cache_backend = getattr(settings, 'CACHES', {}).get('default', {}).get('BACKEND', '')
            
            # If using database cache, ensure cache table exists (quick check)
            if 'django.core.cache.backends.db.DatabaseCache' in cache_backend:
                try:
                    # Quick test - don't log success to reduce noise
                    cache.set('_boot_check', '1', 1)
                    cache.delete('_boot_check')
                except Exception:
                    # Only create if test fails
                    try:
                        call_command('createcachetable', verbosity=0)
                        logger.info("Cache table created")
                    except Exception as e:
                        logger.error(f"Cache table creation failed: {e}")
            
            self._startup_checks_done = True
            
        except Exception as e:
            # Don't fail the app startup if database check fails
            pass