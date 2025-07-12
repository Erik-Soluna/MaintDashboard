"""
Core views for monitoring and health checks.
"""

import json
import time
import psutil
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponse
from django.core.cache import cache
from django.db import connection
from django.conf import settings
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.management import call_command
from io import StringIO
import logging

logger = logging.getLogger(__name__)


def is_staff_or_superuser(user):
    """Check if user is staff or superuser for monitoring access."""
    return user.is_staff or user.is_superuser


@login_required
@user_passes_test(is_staff_or_superuser)
def monitoring_dashboard(request):
    """Display monitoring dashboard."""
    try:
        # Get system metrics
        system_metrics = get_system_metrics()
        
        # Get endpoint metrics
        endpoint_metrics = get_endpoint_metrics()
        
        # Get database health
        db_health = check_database_health()
        
        # Get cache health
        cache_health = check_cache_health()
        
        context = {
            'system_metrics': system_metrics,
            'endpoint_metrics': endpoint_metrics,
            'db_health': db_health,
            'cache_health': cache_health,
            'monitoring_enabled': getattr(settings, 'MONITORING_ENABLED', True)
        }
        
        return render(request, 'core/monitoring_dashboard.html', context)
        
    except Exception as e:
        logger.error(f"Error in monitoring dashboard: {str(e)}")
        return render(request, 'core/monitoring_dashboard.html', {
            'error': str(e),
            'monitoring_enabled': getattr(settings, 'MONITORING_ENABLED', True)
        })


@csrf_exempt
@require_http_methods(["GET"])
def health_check_api(request):
    """API endpoint for health checks."""
    try:
        # Basic health check
        health_data = {
            'timestamp': timezone.now().isoformat(),
            'status': 'healthy',
            'system_metrics': get_system_metrics(),
            'database_health': check_database_health(),
            'cache_health': check_cache_health(),
        }
        
        # Determine overall status
        overall_status = 'healthy'
        
        if health_data['database_health'].get('status') == 'unhealthy':
            overall_status = 'critical'
        elif health_data['cache_health'].get('status') == 'unhealthy':
            overall_status = 'warning'
        
        health_data['overall_status'] = overall_status
        
        return JsonResponse(health_data)
        
    except Exception as e:
        logger.error(f"Error in health check API: {str(e)}")
        return JsonResponse({
            'timestamp': timezone.now().isoformat(),
            'status': 'error',
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def endpoint_metrics_api(request):
    """API endpoint for endpoint metrics."""
    try:
        endpoint_metrics = get_endpoint_metrics()
        return JsonResponse({
            'timestamp': timezone.now().isoformat(),
            'endpoint_metrics': endpoint_metrics
        })
    except Exception as e:
        logger.error(f"Error in endpoint metrics API: {str(e)}")
        return JsonResponse({
            'timestamp': timezone.now().isoformat(),
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def toggle_monitoring(request):
    """Toggle monitoring on/off."""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Insufficient permissions'}, status=403)
    
    try:
        data = json.loads(request.body)
        enabled = data.get('enabled', True)
        
        # Store monitoring state in cache
        cache.set('monitoring_enabled', enabled, timeout=86400)  # 24 hours
        
        return JsonResponse({
            'status': 'success',
            'monitoring_enabled': enabled
        })
        
    except Exception as e:
        logger.error(f"Error toggling monitoring: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@user_passes_test(is_staff_or_superuser)
def run_health_check(request):
    """Run comprehensive health check."""
    try:
        # Capture management command output
        output = StringIO()
        call_command('health_check', stdout=output, stderr=output)
        
        health_output = output.getvalue()
        
        return HttpResponse(health_output, content_type='text/plain')
        
    except Exception as e:
        logger.error(f"Error running health check: {str(e)}")
        return HttpResponse(f"Error running health check: {str(e)}", 
                          content_type='text/plain', status=500)


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