"""Shared helpers and module globals for the views package."""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth.models import User
from equipment.models import Equipment
from maintenance.models import MaintenanceActivity
from events.models import CalendarEvent
from core.models import Location, EquipmentCategory, Role, Permission, UserProfile, Customer, BrandingSettings, DashboardSettings, CSSCustomization
from core.forms import LocationForm, EquipmentCategoryForm, CustomerForm, UserForm, BrandingSettingsForm, BrandingBasicForm, BrandingNavigationForm, BrandingAppearanceForm, CSSCustomizationForm, CSSPreviewForm, DashboardSettingsForm
from django.utils import timezone
from django.db.models import Q, Count
from datetime import datetime, timedelta, date
from django.http import JsonResponse, HttpResponseRedirect, HttpResponse
from django.core.paginator import Paginator
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST, require_GET
from django.core.management import call_command
from django.core.cache import cache
from django.db import connection
from django.conf import settings
from io import StringIO
import json
import csv
import re
import time
import psutil
import logging
import shutil
import redis
from django_celery_beat.models import PeriodicTask
import requests
from django.test import RequestFactory
from django.contrib.admin.views.decorators import staff_member_required
import hmac
import hashlib
import os
import shutil
import redis
from django_celery_beat.models import PeriodicTask
from django.utils import timezone

logger = logging.getLogger(__name__)
HEALTH_LOG_FILE = os.path.join(os.path.dirname(__file__), '../health_failures.log')



def natural_sort_key(text):
    """Generate a key for natural sorting (handles numbers in strings correctly)."""
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r'(\d+)', str(text))]


def is_staff_or_superuser(user):
    """Check if user is staff or superuser."""
    return user.is_staff or user.is_superuser


def invalidate_dashboard_cache(user_id=None, site_id=None):
    """Invalidate dashboard cache for specific user and/or site."""
    from django.core.cache import cache
    
    if user_id:
        # Invalidate cache for specific user
        if site_id == 'all':
            # For 'all' sites, clear the 'all' cache for this user
            cache_key = f"dashboard_data_all_{user_id}"
            cache.delete(cache_key)
        elif site_id:
            # Invalidate cache for specific user and site
            cache_key = f"dashboard_data_{site_id}_{user_id}"
            cache.delete(cache_key)
            # Also clear the 'all' cache since it might contain this site's data
            cache_key = f"dashboard_data_all_{user_id}"
            cache.delete(cache_key)
        else:
            # Invalidate all dashboard caches for this specific user only
            # Clear the 'all' cache and common site-specific caches for this user
            cache.delete(f"dashboard_data_all_{user_id}")
            # Clear site-specific caches for this user (limit to reasonable range)
            for site_id_val in range(1, 100):  # Reasonable upper limit for site IDs
                cache.delete(f"dashboard_data_{site_id_val}_{user_id}")
    else:
        # Invalidate all dashboard caches (use with caution - can be slow)
        # Since Django cache doesn't support pattern deletion, we'll clear common cache keys
        # This is expensive, so prefer passing user_id when possible
        for i in range(100):  # Reasonable upper limit for user IDs
            cache.delete(f"dashboard_data_all_{i}")
            # Also clear some common site-specific caches
            for site_id_val in range(1, 100):  # Reasonable upper limit for site IDs
                cache.delete(f"dashboard_data_{site_id_val}_{i}")


def get_system_metrics():
    """Get current system metrics."""
    try:
        return {
            'cpu_percent': psutil.cpu_percent(interval=0.1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent,
            'load_average': psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None,
            'process_count': len(psutil.pids()),
            'timestamp': timezone.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting system metrics: {str(e)}")
        return {'error': str(e)}


def get_endpoint_metrics():
    """Get endpoint performance metrics from cache."""
    try:
        # Get all endpoint metrics from cache
        all_keys = cache.keys('endpoint_metrics:*')
        endpoint_metrics = {}
        
        for key in all_keys:
            if isinstance(key, str) and key.startswith('endpoint_metrics:'):
                endpoint_name = key.replace('endpoint_metrics:', '')
                metrics = cache.get(key)
                if metrics:
                    endpoint_metrics[endpoint_name] = metrics
        
        return endpoint_metrics
    except Exception as e:
        logger.error(f"Error getting endpoint metrics: {str(e)}")
        return {'error': str(e)}


def check_database_health():
    """Check database connection and performance."""
    try:
        start_time = time.time()
        
        # Test connection
        connection.ensure_connection()
        
        # Test query performance
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        
        response_time = time.time() - start_time
        
        return {
            'status': 'healthy',
            'response_time': response_time,
            'timestamp': timezone.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return {
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }


def check_cache_health():
    """Check cache functionality."""
    try:
        test_key = 'health_check_test'
        test_value = 'test_value'
        
        start_time = time.time()
        
        # Test cache write
        cache.set(test_key, test_value, 60)
        
        # Test cache read
        cached_value = cache.get(test_key)
        
        # Clean up
        cache.delete(test_key)
        
        response_time = time.time() - start_time
        
        if cached_value == test_value:
            return {
                'status': 'healthy',
                'response_time': response_time,
                'timestamp': timezone.now().isoformat()
            }
        else:
            return {
                'status': 'unhealthy',
                'error': 'Cache read/write mismatch',
                'timestamp': timezone.now().isoformat()
            }
    except Exception as e:
        logger.error(f"Cache health check failed: {str(e)}")
        return {
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }


def log_health_failure(component, message):
    with open(HEALTH_LOG_FILE, 'a') as f:
        f.write(f"{timezone.now().isoformat()} | {component} | {message}\n")


def get_recent_health_failures(limit=10):
    if not os.path.exists(HEALTH_LOG_FILE):
        return []
    with open(HEALTH_LOG_FILE, 'r') as f:
        lines = f.readlines()[-limit:]
    return [
        dict(zip(['timestamp', 'component', 'message'], line.strip().split(' | ', 2)))
        for line in lines
    ]


def get_comprehensive_system_health():
    """Get comprehensive system health (no Docker/container status)."""
    health_data = {
        'timestamp': timezone.now().isoformat(),
        'overall_status': 'healthy',
        'components': {}
    }
    
    # Database health
    db_health = check_database_health()
    health_data['components']['database'] = db_health
    
    # Cache health
    cache_health = check_cache_health()
    health_data['components']['cache'] = cache_health
    
    # Celery worker health
    celery_health = check_celery_worker_health()
    health_data['components']['celery_worker'] = celery_health
    
    # Celery beat health
    celery_beat_health = check_celery_beat_health()
    health_data['components']['celery_beat'] = celery_beat_health
    
    # System metrics
    try:
        system_metrics = get_system_metrics()
        health_data['components']['system'] = system_metrics
    except Exception as e:
        health_data['components']['system'] = {'error': str(e)}
    
    # Determine overall status
    if db_health.get('status') == 'unhealthy':
        health_data['overall_status'] = 'critical'
    elif cache_health.get('status') == 'unhealthy':
        health_data['overall_status'] = 'warning'
    elif celery_health.get('status') == 'unhealthy' or celery_beat_health.get('status') == 'unhealthy':
        health_data['overall_status'] = 'warning'
    
    return health_data


def check_celery_worker_health():
    """Check Celery worker health by running inspect ping."""
    try:
        import subprocess
        result = subprocess.run([
            'celery', '-A', 'maintenance_dashboard', 'inspect', 'ping'
        ], capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and 'pong' in result.stdout:
            return {'status': 'healthy', 'output': result.stdout}
        else:
            return {'status': 'unhealthy', 'output': result.stdout + result.stderr}
    except Exception as e:
        return {'status': 'unhealthy', 'error': str(e)}


def check_celery_beat_health():
    """Check Celery beat health by checking last run of periodic tasks."""
    try:
        from django_celery_beat.models import PeriodicTask
        from django.utils import timezone
        enabled_tasks = PeriodicTask.objects.filter(enabled=True)
        if not enabled_tasks.exists():
            return {'status': 'warning', 'message': 'No periodic tasks enabled'}
        recent = None
        for task in enabled_tasks:
            if task.last_run_at and (recent is None or task.last_run_at > recent):
                recent = task.last_run_at
        if recent:
            seconds_since = (timezone.now() - recent).total_seconds()
            if seconds_since < 600:
                return {'status': 'healthy', 'message': f'Recent heartbeat ({int(seconds_since)}s ago)'}
            else:
                return {'status': 'warning', 'message': f'No recent heartbeat (last was {int(seconds_since//60)} min ago)'}
        else:
            return {'status': 'warning', 'message': 'No periodic tasks have ever run'}
    except Exception as e:
        return {'status': 'unhealthy', 'error': str(e)}


def trigger_portainer_stack_update():
    """Trigger a stack update by calling the webhook URL."""
    logger.info("=== TRIGGER PORTAINER STACK UPDATE STARTED ===")
    try:
        from .models import PortainerConfig
        config = PortainerConfig.get_config()
        
        webhook_url = config.portainer_url
        webhook_secret = config.webhook_secret
        image_tag = config.image_tag or 'latest'  # Default to 'latest' if not specified
        
        logger.info(f"Config loaded - Webhook URL: '{webhook_url}'")
        logger.info(f"Webhook secret exists: {bool(webhook_secret)}")
        logger.info(f"Image tag: '{image_tag}'")
        
        if not webhook_url:
            logger.error("Configuration incomplete - missing webhook URL")
            return 'Configuration incomplete - missing webhook URL'
        
        # Prepare headers with webhook secret if available
        headers = {}
        if webhook_secret:
            headers['X-Webhook-Secret'] = webhook_secret
            logger.info("Added webhook secret to headers")
        
        # Build webhook URL with tag parameter
        webhook_url_with_tag = f"{webhook_url}?tag={image_tag}"
        logger.info(f"Calling webhook URL with tag: {webhook_url_with_tag}")
        
        webhook_response = requests.post(
            webhook_url_with_tag,
            headers=headers,
            json={'action': 'update_stack', 'timestamp': time.time()},
            timeout=30
        )
        
        logger.info(f"Webhook response status: {webhook_response.status_code}")
        logger.info(f"Webhook response content: {webhook_response.text[:200]}...")
        
        if webhook_response.status_code in [200, 202, 204]:
            logger.info("Webhook call successful")
            return 'Stack update triggered successfully via webhook'
        else:
            logger.error(f"Webhook call failed with status: {webhook_response.status_code}")
            return f'Webhook call failed: {webhook_response.status_code}'
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error in webhook call: {str(e)}")
        return f'Network error: {str(e)}'
    except Exception as e:
        logger.error(f"Unexpected error in webhook call: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return f'Error: {str(e)}'


def test_portainer_connection():
    """Test connection to webhook URL."""
    logger.info("=== TEST WEBHOOK CONNECTION STARTED ===")
    try:
        from .models import PortainerConfig
        config = PortainerConfig.get_config()
        
        webhook_url = config.portainer_url
        webhook_secret = config.webhook_secret
        
        logger.info(f"Config loaded - Webhook URL: '{webhook_url}'")
        logger.info(f"Webhook secret exists: {bool(webhook_secret)}")
        
        if not webhook_url:
            logger.error("Configuration incomplete - missing webhook URL")
            return 'Configuration incomplete - missing webhook URL'
        
        # Test webhook URL with a simple GET request
        logger.info(f"Testing webhook URL: {webhook_url}")
        test_response = requests.get(
            webhook_url,
            timeout=10
        )
        
        logger.info(f"Test response status: {test_response.status_code}")
        logger.info(f"Test response content: {test_response.text[:200]}...")
        
        if test_response.status_code in [200, 202, 404, 405]:
            # 404/405 are expected for GET requests to webhook endpoints
            logger.info("Webhook URL is reachable")
            return 'Webhook URL is reachable and responding'
        else:
            logger.error(f"Webhook test failed with status: {test_response.status_code}")
            return f'Webhook test failed: {test_response.status_code}'
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error in webhook test: {str(e)}")
        return f'Network error: {str(e)}'
    except Exception as e:
        logger.error(f"Unexpected error in webhook test: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return f'Error: {str(e)}'


__all__ = ["HEALTH_LOG_FILE", "check_cache_health", "check_celery_beat_health", "check_celery_worker_health", "check_database_health", "get_comprehensive_system_health", "get_endpoint_metrics", "get_recent_health_failures", "get_system_metrics", "invalidate_dashboard_cache", "is_staff_or_superuser", "log_health_failure", "logger", "natural_sort_key", "test_portainer_connection", "trigger_portainer_stack_update"]
