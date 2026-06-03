"""
Celery configuration for maintenance_dashboard project.
"""

import os
import logging
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maintenance_dashboard.settings')

# Configure database connection pooling for celery
# Disable persistent connections for celery to avoid "Bad file descriptor" errors
# when running worker + beat in the same process
os.environ.setdefault('DJANGO_DB_CONN_MAX_AGE', '0')

app = Celery('maintenance_dashboard')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Security: Disable superuser privileges for Celery workers
# This prevents the security warning about running with superuser privileges
app.conf.worker_disable_rate_limits = False
app.conf.worker_send_task_events = True
app.conf.task_send_sent_event = True
# Disable superuser privileges - workers should not run as root.
# os.geteuid only exists on Unix; guard so imports don't crash on Windows dev.
if hasattr(os, 'geteuid') and os.geteuid() == 0:
    logging.warning("Celery worker is running as root. This is not recommended for security.")
    # Try to switch to non-root user if available
    try:
        import pwd
        appuser = pwd.getpwnam('appuser')
        os.setgid(appuser.pw_gid)
        os.setuid(appuser.pw_uid)
        logging.info("Switched to non-root user: appuser")
    except (KeyError, OSError, ImportError):
        logging.warning("Could not switch to non-root user. Please configure container to run as non-root.")

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Broker, result backend and task_always_eager all come from settings via
# config_from_object (CELERY_BROKER_URL / CELERY_RESULT_BACKEND /
# CELERY_TASK_ALWAYS_EAGER). We deliberately do NOT auto-detect Redis and flip
# to an in-memory/eager broker on a transient ping failure — that silently ran
# tasks synchronously in the web process and masked broker misconfig. To run
# without a broker (local dev), set CELERY_TASK_ALWAYS_EAGER=True explicitly.

# Ensure Django is fully initialized before beat scheduler starts
# This is critical when running worker + beat in the same process
import django
try:
    # Check if Django apps are ready
    if not hasattr(django, 'apps') or not django.apps.apps.ready:
        django.setup()
except (AttributeError, ImportError):
    # If django.apps doesn't exist yet, setup Django
    django.setup()

# Close database connections after each task to prevent connection issues
# This is especially important when running worker + beat in the same process
from celery.signals import task_postrun, beat_init, worker_process_init

@worker_process_init.connect
def init_worker_process(sender=None, **kwargs):
    """Initialize database connections when worker process starts."""
    import django
    from django.db import connection
    
    # Ensure Django is fully initialized
    try:
        if not hasattr(django, 'apps') or not django.apps.apps.ready:
            django.setup()
    except (AttributeError, ImportError):
        django.setup()
    
    # Establish a database connection for this worker process
    try:
        connection.ensure_connection()
        logging.info("Database connection established for worker process")
    except Exception as e:
        logging.warning(f"Could not establish database connection in worker init: {e}")

@task_postrun.connect
def close_db_after_task(sender=None, **kwargs):
    """Close database connections after each task completes."""
    from django.db import connections
    for conn in connections.all():
        conn.close_if_unusable_or_obsolete()

@beat_init.connect
def init_beat_scheduler(sender=None, **kwargs):
    """Ensure database connections are ready when beat scheduler starts."""
    import time
    import django
    from django.db import connections, connection
    from django.db.utils import OperationalError
    
    # Ensure Django is fully initialized
    try:
        if not hasattr(django, 'apps') or not django.apps.apps.ready:
            django.setup()
    except (AttributeError, ImportError):
        django.setup()
    
    # Close any stale connections first
    for conn in connections.all():
        if conn.connection is not None:
            try:
                conn.close_if_unusable_or_obsolete()
            except Exception:
                pass
    
    # Wait a moment for connections to fully close
    time.sleep(0.2)
    
    # Ensure a fresh connection is established before beat scheduler queries
    max_retries = 10
    for attempt in range(max_retries):
        try:
            # Close and reconnect to ensure fresh connection
            connection.close()
            connection.ensure_connection()
            
            # Test the connection with a simple query
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            
            logging.info("Database connection established for beat scheduler")
            return
        except (OperationalError, Exception) as e:
            if attempt < max_retries - 1:
                logging.warning(f"Database connection attempt {attempt + 1}/{max_retries} failed, retrying in 0.5s...")
                time.sleep(0.5)
            else:
                logging.error(f"Failed to establish database connection for beat scheduler after {max_retries} attempts: {e}")
                # Don't raise - let beat scheduler handle the error
                pass

@app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery setup."""
    print(f'Request: {self.request!r}')