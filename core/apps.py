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
        """Ensure all required database tables exist on startup."""
        try:
            from django.core.management import call_command
            from django.core.cache import cache
            from django.conf import settings
            import logging
            
            logger = logging.getLogger(__name__)
            
            # Check if we're in a management command (avoid running during migrations)
            import sys
            if 'manage.py' in sys.argv and any('migrate' in arg for arg in sys.argv):
                return
            
            # Check cache backend
            cache_backend = getattr(settings, 'CACHES', {}).get('default', {}).get('BACKEND', '')
            
            # If using database cache, ensure cache table exists
            if 'django.core.cache.backends.db.DatabaseCache' in cache_backend:
                try:
                    # Test cache functionality (silent test)
                    test_key = 'startup_cache_test'
                    cache.set(test_key, 'test', 10)
                    cache.get(test_key)
                    cache.delete(test_key)
                    # Only log once per process to avoid repetition
                    if not hasattr(self, '_startup_checks_done'):
                        logger.debug("Cache functionality verified on startup")
                        self._startup_checks_done = True
                except Exception as e:
                    logger.warning(f"Cache table may be missing, attempting to create: {e}")
                    try:
                        call_command('createcachetable', verbosity=0)
                        logger.info("Cache table created successfully on startup")
                    except Exception as create_error:
                        logger.error(f"Failed to create cache table on startup: {create_error}")
            
            # Only log once per process to avoid repetition
            if not hasattr(self, '_startup_checks_done'):
                logger.debug("Database tables check completed on startup")
                self._startup_checks_done = True
            
        except Exception as e:
            # Don't fail the app startup if database check fails
            logger.warning(f"Database tables check failed on startup: {e}")