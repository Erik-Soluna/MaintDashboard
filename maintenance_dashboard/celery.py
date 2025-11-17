"""
Celery configuration for maintenance_dashboard project.
"""

import os
import logging
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maintenance_dashboard.settings')

app = Celery('maintenance_dashboard')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Configure Celery to handle Redis connection failures gracefully
def configure_celery_broker():
    """Configure Celery broker with fallback options."""
    broker_url = getattr(settings, 'CELERY_BROKER_URL', None)
    if not broker_url:
        # Build Redis URL from settings
        redis_url = getattr(settings, 'REDIS_URL', 'redis://redis:6379')
        broker_url = f'{redis_url}/0'
    
    # If Redis is disabled or we're in development without Redis
    if broker_url.startswith('memory://') or broker_url.startswith('rpc://'):
        app.conf.update(
            broker_url=broker_url,
            result_backend=getattr(settings, 'CELERY_RESULT_BACKEND', 'rpc://'),
            task_always_eager=True,  # Execute tasks synchronously
            task_eager_propagates=True,
        )
        logging.info("Celery configured with memory/RPC broker for development")
    else:
        # Try to configure Redis broker
        try:
            import redis
            # Test Redis connection
            redis_url = broker_url.replace('/0', '')  # Remove database number for connection test
            r = redis.Redis.from_url(redis_url, socket_connect_timeout=2, socket_timeout=2)
            r.ping()
            logging.info("Redis connection successful, using Redis broker")
        except Exception as e:
            logging.warning(f"Redis connection failed: {e}. Falling back to memory broker.")
            app.conf.update(
                broker_url='memory://',
                result_backend='rpc://',
                task_always_eager=True,
                task_eager_propagates=True,
            )

# Configure broker on startup
configure_celery_broker()

# Close database connections after each task to prevent connection issues
# This is especially important when running worker + beat in the same process
from celery.signals import task_postrun, beat_init

@task_postrun.connect
def close_db_after_task(sender=None, **kwargs):
    """Close database connections after each task completes."""
    from django.db import connections
    for conn in connections.all():
        conn.close_if_unusable_or_obsolete()

@beat_init.connect
def close_db_on_beat_init(sender=None, **kwargs):
    """Ensure database connections are fresh when beat scheduler starts."""
    from django.db import connections
    for conn in connections.all():
        conn.close()

@app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery setup."""
    print(f'Request: {self.request!r}')