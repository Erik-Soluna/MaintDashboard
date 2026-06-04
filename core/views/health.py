"""health views (split from the original monolithic views.py)."""
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
from .helpers import *  # noqa: F401,F403 (shared helpers + globals)
from .profile_settings import settings  # noqa: F401 - intentional shadow: preserves pre-split behavior where the `settings` view function shadowed django.conf.settings in monitoring_dashboard/debug


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
            'error': str(e),
            'status': 'error',
            'timestamp': timezone.now().isoformat()
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


def health_check(request):
    """Comprehensive health check endpoint that returns JSON with detailed status."""
    checks = []
    status = 'ok'
    # DB check
    try:
        from django.db import connection
        connection.ensure_connection()
        checks.append({'name': 'Database', 'status': 'ok', 'message': 'Connected'})
    except Exception as e:
        checks.append({'name': 'Database', 'status': 'error', 'message': str(e)})
        log_health_failure('Database', str(e))
        status = 'error'
    # Redis check
    try:
        from django.conf import settings
        if getattr(settings, 'USE_REDIS', True):
            r = redis.Redis.from_url(settings.REDIS_URL)
            r.ping()
            checks.append({'name': 'Redis', 'status': 'ok', 'message': 'Connected'})
        else:
            checks.append({'name': 'Redis', 'status': 'info', 'message': 'Redis disabled for development'})
    except Exception as e:
        checks.append({'name': 'Redis', 'status': 'error', 'message': str(e)})
        log_health_failure('Redis', str(e))
        status = 'error'
    # Celery check (beat task heartbeat)
    try:
        from django_celery_beat.models import PeriodicTask
        enabled_tasks = PeriodicTask.objects.filter(enabled=True)
        if not enabled_tasks.exists():
            msg = 'No periodic tasks enabled'
            checks.append({'name': 'Celery Beat', 'status': 'info', 'message': msg})
        else:
            recent = None
            for task in enabled_tasks:
                if task.last_run_at and (recent is None or task.last_run_at > recent):
                    recent = task.last_run_at
            if recent:
                seconds_since = (timezone.now() - recent).total_seconds()
                if seconds_since < 600:
                    checks.append({'name': 'Celery Beat', 'status': 'ok', 'message': f'Recent heartbeat ({int(seconds_since)}s ago)'})
                else:
                    msg = f'No recent heartbeat (last was {int(seconds_since//60)} min ago)'
                    checks.append({'name': 'Celery Beat', 'status': 'warning', 'message': msg})
                    log_health_failure('Celery Beat', msg)
                    if status != 'error':
                        status = 'warning'
            else:
                msg = 'No periodic tasks have ever run'
                checks.append({'name': 'Celery Beat', 'status': 'warning', 'message': msg})
                log_health_failure('Celery Beat', msg)
                if status != 'error':
                    status = 'warning'
    except Exception as e:
        checks.append({'name': 'Celery Beat', 'status': 'error', 'message': str(e)})
        log_health_failure('Celery Beat', str(e))
        status = 'error'
    # Disk space check
    try:
        total, used, free = shutil.disk_usage('/')
        percent_free = free / total * 100
        if percent_free < 10:
            msg = f'Low disk space: {percent_free:.1f}% free'
            checks.append({'name': 'Disk Space', 'status': 'warning', 'message': msg})
            log_health_failure('Disk Space', msg)
            if status != 'error':
                status = 'warning'
        else:
            checks.append({'name': 'Disk Space', 'status': 'ok', 'message': f'{percent_free:.1f}% free'})
    except Exception as e:
        checks.append({'name': 'Disk Space', 'status': 'error', 'message': str(e)})
        log_health_failure('Disk Space', str(e))
        status = 'error'
    # Add more checks as needed
    return JsonResponse({
        'status': status,
        'checks': checks,
        'last_failure_log': get_recent_health_failures(10)
    })


def simple_health_check(request):
    """Simple health check endpoint for Docker health checks - returns 200 OK."""
    try:
        # Basic database connection check with timeout
        from django.db import connection
        from django.db.utils import OperationalError
        import time
        
        start_time = time.time()
        
        # Quick database ping
        try:
            connection.ensure_connection()
            db_time = time.time() - start_time
            logger.debug(f"Database health check completed in {db_time:.3f}s")
        except OperationalError as db_error:
            logger.error(f"Database health check failed: {db_error}")
            return JsonResponse({'status': 'error', 'message': 'Database connection failed'}, status=500)
        
        # Basic Redis check (only if enabled and Redis is available)
        from django.conf import settings
        redis_status = "disabled"
        if getattr(settings, 'USE_REDIS', True):
            try:
                import redis
                r = redis.Redis.from_url(
                    getattr(settings, 'REDIS_URL', 'redis://redis:6379'), 
                    socket_connect_timeout=1, 
                    socket_timeout=1
                )
                r.ping()
                redis_status = "healthy"
                logger.debug("Redis health check completed successfully")
            except Exception as redis_error:
                # Log the Redis error but don't fail the health check
                logger.warning(f"Redis connection failed: {redis_error}. Health check continuing...")
                redis_status = "unavailable"
        
        # Return success response
        response_data = {
            'status': 'ok',
            'timestamp': time.time(),
            'database': 'healthy',
            'redis': redis_status,
            'response_time': time.time() - start_time
        }
        
        logger.debug(f"Health check completed successfully in {response_data['response_time']:.3f}s")
        return JsonResponse(response_data, status=200)
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        return JsonResponse({
            'status': 'error', 
            'message': str(e),
            'timestamp': time.time()
        }, status=500)


@require_POST
def clear_health_logs(request):
    """Clear the recent health failure log (from cache and file)."""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    cache.delete('health_failure_log')
    # Also clear the log file
    try:
        if os.path.exists(HEALTH_LOG_FILE):
            with open(HEALTH_LOG_FILE, 'w') as f:
                f.truncate(0)
    except Exception as e:
        return JsonResponse({'error': f'Failed to clear log file: {str(e)}'}, status=500)
    return JsonResponse({'success': True})


@login_required
def api_explorer(request):
    """Dynamic API Explorer — reflects the live /api/v1/ model registry so it
    never goes stale as the schema evolves. Backed by the `api` app registry."""
    from api.registry import exposed_models, model_key, field_metadata

    models = []
    for m in exposed_models():
        try:
            count = m.objects.count()
        except Exception:
            count = None
        models.append({
            'key': model_key(m),
            'app': m._meta.app_label,
            'model': m._meta.model_name,
            'verbose_name': str(m._meta.verbose_name),
            'verbose_name_plural': str(m._meta.verbose_name_plural),
            'count': count,
            'fields': field_metadata(m),
            'list_path': f'/api/v1/data/{model_key(m)}/',
        })

    apps_grouped = {}
    for entry in models:
        apps_grouped.setdefault(entry['app'], []).append(entry)
    apps_grouped = [
        {'app': app, 'models': sorted(group, key=lambda x: x['model'])}
        for app, group in sorted(apps_grouped.items())
    ]

    context = {
        'apps_grouped': apps_grouped,
        'total_models': len(models),
        'total_fields': sum(len(m['fields']) for m in models),
        'api_base': '/api/v1/',
        'diagnostics': [
            {'name': 'System Health', 'path': '/api/v1/diagnostics/health/',
             'description': 'Comprehensive system health (db, cache, celery, email, system)'},
            {'name': 'Diagnostics Summary', 'path': '/api/v1/diagnostics/summary/',
             'description': 'Open/critical issues, overdue maintenance, equipment-by-status'},
        ],
        'last_updated': timezone.now(),
    }
    return render(request, 'core/api_explorer.html', context)



@login_required
def system_health(request):
    """System health/diagnostics page for superusers/admins."""
    if not request.user.is_superuser:
        return redirect('core:dashboard')
    return render(request, 'core/system_health.html')


@login_required
def debug(request):
    """Debug and diagnostics page with collapsible sections."""
    if not request.user.is_superuser:
        return redirect('core:dashboard')
    
    try:
        # Trigger log collection if requested
        if request.GET.get('collect_logs') == 'true':
            # Direct log collection without Celery
            from .services.log_streaming_service import LogStreamingService
            log_service = LogStreamingService()
            
            # Collect logs directly
            try:
                # Create logs directory
                import os
                logs_dir = '/app/logs'
                os.makedirs(logs_dir, exist_ok=True)
                
                # Get containers and collect logs from accessible sources
                containers = log_service.get_available_containers()
                collected_count = 0
                
                for container in containers:
                    try:
                        log_file = container.get('log_file')
                        if log_file and os.path.exists(log_file):
                            # Read from accessible log file
                            with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                                content = f.read()
                            
                            # Write to our logs directory
                            output_file = os.path.join(logs_dir, f"{container['name']}.log")
                            with open(output_file, 'w', encoding='utf-8') as f:
                                f.write(f"# Source: {container['name']}\n")
                                f.write(f"# Type: {container.get('image', 'Unknown')}\n")
                                f.write(f"# Path: {log_file}\n")
                                f.write(f"# Collected at: {timezone.now().isoformat()}\n")
                                f.write("#" * 80 + "\n")
                                f.write(content)
                            
                            collected_count += 1
                            logger.info(f"Collected logs from {container['name']}: {len(content)} characters")
                        else:
                            logger.warning(f"No accessible log file for {container['name']}")
                    except Exception as e:
                        logger.warning(f"Error collecting logs for {container['name']}: {e}")
                
                logger.info(f"Direct log collection completed: {collected_count} containers")
                
            except Exception as e:
                logger.error(f"Error in direct log collection: {e}")
        
        # Get available containers for log streaming
        from .services.log_streaming_service import LogStreamingService
        log_service = LogStreamingService()
        containers = log_service.get_available_containers()
        
        context = {
            'containers': containers,
            'docker_logs_enabled': getattr(settings, 'DOCKER_LOGS_ENABLED', False),
            'docker_logs_debug_only': getattr(settings, 'DOCKER_LOGS_DEBUG_ONLY', False),
        }
        
        return render(request, 'core/debug.html', context)
    except Exception as e:
        import traceback
        logger.error(f"Error in debug view: {str(e)}")
        logger.error(traceback.format_exc())
        # Return a simple error page instead of 500
        return render(request, 'core/debug.html', {
            'error': f'Debug page error: {str(e)}',
            'traceback': traceback.format_exc() if request.user.is_superuser else None
        })


@require_GET
def test_health(request):
    """Minimal health check endpoint for debug page AJAX."""
    import psutil
    try:
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent
        return JsonResponse({
            'status': 'ok',
            'cpu': cpu,
            'memory': mem,
            'disk': disk
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'error': str(e)}, status=500)


@require_GET
def test_database(request):
    """Database health check endpoint for debug page AJAX."""
    try:
        from django.db import connection
        from django.db.utils import OperationalError
        
        # Test database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
        
        # Get database stats
        from django.contrib.auth.models import User
        from core.models import Location, Customer
        from equipment.models import Equipment
        from maintenance.models import MaintenanceActivity
        
        stats = {
            'users': User.objects.count(),
            'locations': Location.objects.count(),
            'customers': Customer.objects.count(),
            'equipment': Equipment.objects.count(),
            'maintenance_activities': MaintenanceActivity.objects.count(),
        }
        
        return JsonResponse({
            'status': 'ok',
            'connection': 'healthy',
            'stats': stats
        })
    except OperationalError as e:
        return JsonResponse({
            'status': 'error',
            'error': f'Database connection failed: {str(e)}'
        }, status=500)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        }, status=500)


@require_GET
def test_cache(request):
    """Cache health check endpoint for debug page AJAX."""
    try:
        from django.core.cache import cache
        from django.conf import settings
        
        # Test cache connection
        test_key = 'debug_cache_test'
        test_value = 'test_value_123'
        
        # Set a test value
        cache.set(test_key, test_value, 60)
        
        # Get the test value
        retrieved_value = cache.get(test_key)
        
        # Clean up
        cache.delete(test_key)
        
        if retrieved_value == test_value:
            cache_status = 'healthy'
        else:
            cache_status = 'unhealthy'
        
        return JsonResponse({
            'status': 'ok',
            'cache': cache_status,
            'backend': getattr(settings, 'CACHES', {}).get('default', {}).get('BACKEND', 'unknown')
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def comprehensive_health_check(request):
    """Comprehensive health check including container status."""
    try:
        health_data = get_comprehensive_system_health()
        return JsonResponse(health_data)
    except Exception as e:
        logger.error(f"Error in comprehensive health check: {str(e)}")
        return JsonResponse({
            'error': str(e),
            'status': 'error',
            'timestamp': timezone.now().isoformat()
        }, status=500)


@login_required
@user_passes_test(is_staff_or_superuser)
@require_http_methods(["GET"])
def database_stats(request):
    """Get database statistics and information."""
    try:
        from django.db import connection
        from django.db.models import Count
        from core.models import Location, Customer
        from equipment.models import Equipment
        from maintenance.models import MaintenanceActivity
        from events.models import CalendarEvent
        
        # Get basic counts
        stats = {
            'locations': {
                'total': Location.objects.count(),
                'sites': Location.objects.filter(is_site=True).count(),
                'sub_locations': Location.objects.filter(is_site=False).count(),
                'active': Location.objects.filter(is_active=True).count(),
            },
            'customers': {
                'total': Customer.objects.count(),
                'active': Customer.objects.filter(is_active=True).count(),
            },
            'equipment': {
                'total': Equipment.objects.count(),
                'active': Equipment.objects.filter(is_active=True).count(),
            },
            'maintenance': {
                'total': MaintenanceActivity.objects.count(),
                'completed': MaintenanceActivity.objects.filter(status='completed').count(),
                'pending': MaintenanceActivity.objects.filter(status='pending').count(),
            },
            'events': {
                'total': CalendarEvent.objects.count(),
                'recent': CalendarEvent.objects.filter(created_at__gte=timezone.now() - timezone.timedelta(days=7)).count(),
            }
        }
        
        # Get database size info
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    pg_size_pretty(pg_database_size(current_database())) as db_size,
                    pg_size_pretty(pg_total_relation_size('core_location')) as locations_size,
                    pg_size_pretty(pg_total_relation_size('core_customer')) as customers_size,
                    pg_size_pretty(pg_total_relation_size('equipment_equipment')) as equipment_size
            """)
            db_info = cursor.fetchone()
            
        stats['database'] = {
            'total_size': db_info[0] if db_info else 'Unknown',
            'locations_table_size': db_info[1] if db_info else 'Unknown',
            'customers_table_size': db_info[2] if db_info else 'Unknown',
            'equipment_table_size': db_info[3] if db_info else 'Unknown',
        }
        
        return JsonResponse({
            'success': True,
            'stats': stats,
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@user_passes_test(is_staff_or_superuser)
@require_http_methods(["POST"])
def backup_database(request):
    """Create a database backup."""
    try:
        from django.core.management import call_command
        from io import StringIO
        import os
        from django.conf import settings
        
        # Create backup directory if it doesn't exist
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        # Generate backup filename with timestamp
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'backup_{timestamp}.json'
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # Capture command output
        output = StringIO()
        
        # Call the dumpdata command
        call_command('dumpdata', 
                    '--exclude', 'contenttypes',
                    '--exclude', 'auth.Permission',
                    '--exclude', 'sessions',
                    '--indent', '2',
                    '--output', backup_path,
                    stdout=output,
                    verbosity=2)
        
        result = output.getvalue()
        output.close()
        
        # Get file size
        file_size = os.path.getsize(backup_path) if os.path.exists(backup_path) else 0
        
        return JsonResponse({
            'success': True,
            'message': f'Database backup created successfully: {backup_filename}',
            'filename': backup_filename,
            'file_size': file_size,
            'file_size_pretty': f'{file_size / 1024 / 1024:.2f} MB' if file_size > 0 else '0 B',
            'output': result
        })
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return JsonResponse({
            'success': False,
            'error': f'Error creating database backup: {str(e)}',
            'details': error_details
        }, status=500)


@login_required
@user_passes_test(is_staff_or_superuser)
@require_http_methods(["POST"])
def populate_sample_data(request):
    """Populate the database with sample data."""
    try:
        from django.core.management import call_command
        from io import StringIO
        
        # Capture command output
        output = StringIO()
        
        # Call the populate sample data command
        call_command('populate_sample_data', stdout=output, verbosity=2)
        
        result = output.getvalue()
        output.close()
        
        # Parse the output to extract counts
        created_count = 0
        
        # Look for patterns in the output
        import re
        created_matches = re.findall(r'Created (\d+)', result)
        
        if created_matches:
            created_count = sum(int(x) for x in created_matches)
        
        return JsonResponse({
            'success': True,
            'message': f'Sample data populated successfully! Created: {created_count} items',
            'created_count': created_count,
            'output': result
        })
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return JsonResponse({
            'success': False,
            'error': f'Error populating sample data: {str(e)}',
            'details': error_details
        }, status=500)


@login_required
def invalidate_cache_api(request):
    """API endpoint to invalidate dashboard cache for the current user."""
    try:
        import json
        
        # Get the site_id from the request body
        data = json.loads(request.body)
        site_id = data.get('site_id')
        
        # Update the session with the new site selection
        if site_id == 'all':
            request.session['selected_site_id'] = 'all'
        elif site_id:
            request.session['selected_site_id'] = site_id
        else:
            request.session['selected_site_id'] = 'all'
        
        # Invalidate cache for this user and site
        invalidate_dashboard_cache(user_id=request.user.id, site_id=site_id)
        
        return JsonResponse({
            'status': 'success',
            'message': 'Cache invalidated successfully',
            'site_id': site_id
        })
    except Exception as e:
        logger.error(f"Error invalidating cache: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f'Error invalidating cache: {str(e)}'
        }, status=500)


@login_required
@user_passes_test(is_staff_or_superuser)
def database_stats_api(request):
    """API endpoint to get database statistics."""
    try:
        from django.db import connection
        from equipment.models import Equipment, EquipmentConnection
        from maintenance.models import MaintenanceActivity, MaintenanceSchedule, MaintenanceActivityType
        from events.models import CalendarEvent
        
        tables = {}
        
        # Get row counts for key tables - handle each one individually to avoid total failure
        def safe_count(model_class, model_name):
            try:
                return model_class.objects.count()
            except Exception as e:
                logger.warning(f"Error counting {model_name}: {str(e)}")
                return 'Error'
        
        tables['Equipment'] = {'count': safe_count(Equipment, 'Equipment')}
        tables['Equipment Connections'] = {'count': safe_count(EquipmentConnection, 'EquipmentConnection')}
        tables['Locations'] = {'count': safe_count(Location, 'Location')}
        tables['Customers'] = {'count': safe_count(Customer, 'Customer')}
        tables['Maintenance Activities'] = {'count': safe_count(MaintenanceActivity, 'MaintenanceActivity')}
        tables['Maintenance Schedules'] = {'count': safe_count(MaintenanceSchedule, 'MaintenanceSchedule')}
        tables['Activity Types'] = {'count': safe_count(MaintenanceActivityType, 'MaintenanceActivityType')}
        tables['Calendar Events'] = {'count': safe_count(CalendarEvent, 'CalendarEvent')}
        tables['Users'] = {'count': safe_count(User, 'User')}
        
        # Get database size (PostgreSQL specific)
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT pg_size_pretty(pg_database_size(current_database())) as size;
                """)
                row = cursor.fetchone()
                db_size = row[0] if row else 'Unknown'
        except Exception as e:
            logger.warning(f"Error getting database size: {str(e)}")
            db_size = 'N/A'
        
        return JsonResponse({
            'status': 'success',
            'tables': tables,
            'database_size': db_size,
            'database_name': connection.settings_dict.get('NAME', 'Unknown')
        })
        
    except Exception as e:
        logger.error(f"Error getting database stats: {str(e)}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'message': f'Error getting database stats: {str(e)}'
        }, status=500)


@login_required
def system_health_check(request):
    """System health check endpoint for debugging issues."""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    health_data = {
        'timestamp': timezone.now().isoformat(),
        'categories': {},
        'summary': {
            'total_checks': 0,
            'passed': 0,
            'failed': 0,
            'warnings': 0,
            'health_percentage': 0
        },
        'quick_fixes': []
    }
    
    def run_check(category, check_name, test_func, fix_suggestion=None):
        """Run a health check and record results."""
        try:
            result = test_func()
            if result:
                health_data['categories'][category]['passed'].append({
                    'name': check_name,
                    'status': 'PASS'
                })
                health_data['summary']['passed'] += 1
            else:
                health_data['categories'][category]['failed'].append({
                    'name': check_name,
                    'status': 'FAIL',
                    'fix': fix_suggestion
                })
                health_data['summary']['failed'] += 1
                if fix_suggestion:
                    health_data['quick_fixes'].append(fix_suggestion)
        except Exception as e:
            health_data['categories'][category]['failed'].append({
                'name': check_name,
                'status': 'ERROR',
                'error': str(e),
                'fix': fix_suggestion
            })
            health_data['summary']['failed'] += 1
            if fix_suggestion:
                health_data['quick_fixes'].append(fix_suggestion)
        
        health_data['summary']['total_checks'] += 1
    
    def run_warning_check(category, check_name, test_func, warning_message=None):
        """Run a warning check and record results."""
        try:
            result = test_func()
            if result:
                health_data['categories'][category]['passed'].append({
                    'name': check_name,
                    'status': 'PASS'
                })
                health_data['summary']['passed'] += 1
            else:
                health_data['categories'][category]['warnings'].append({
                    'name': check_name,
                    'status': 'WARNING',
                    'message': warning_message
                })
                health_data['summary']['warnings'] += 1
        except Exception as e:
            health_data['categories'][category]['warnings'].append({
                'name': check_name,
                'status': 'WARNING',
                'error': str(e),
                'message': warning_message
            })
            health_data['summary']['warnings'] += 1
        
        health_data['summary']['total_checks'] += 1
    
    # Initialize categories
    categories = ['CORE', 'SCHEMA', 'API', 'CALENDAR', 'MIGRATIONS', 'AUTH', 'DEPS']
    for category in categories:
        health_data['categories'][category] = {
            'passed': [],
            'failed': [],
            'warnings': []
        }
    
    # CORE APPLICATION HEALTH
    run_check('CORE', 'Django Configuration', 
              lambda: True,  # Simplified for now
              'Check Django settings and configuration')
    
    run_check('CORE', 'Database Connection',
              lambda: connection.cursor().execute('SELECT 1') is not None,
              'Check database connectivity and credentials')
    
    # DATABASE SCHEMA INTEGRITY
    run_check('SCHEMA', 'MaintenanceActivity Model',
              lambda: MaintenanceActivity.objects.count() >= 0,
              'Run: ./scripts/simple_timezone_fix.sh')
    
    run_check('SCHEMA', 'Timezone Field Exists',
              lambda: hasattr(MaintenanceActivity, 'timezone'),
              'Run: ./scripts/simple_timezone_fix.sh')
    
    try:
        from events.models import CalendarEvent
        run_check('SCHEMA', 'CalendarEvent Model',
                  lambda: CalendarEvent.objects.count() >= 0,
                  'Check events app migrations')
    except ImportError:
        health_data['categories']['SCHEMA']['failed'].append({
            'name': 'CalendarEvent Model',
            'status': 'ERROR',
            'error': 'CalendarEvent model not found',
            'fix': 'Check events app migrations'
        })
        health_data['summary']['failed'] += 1
        health_data['summary']['total_checks'] += 1
    
    # API ENDPOINTS FUNCTIONALITY
    def test_unified_events_api():
        try:
            from events.views import fetch_unified_events
            from django.test import RequestFactory
            
            factory = RequestFactory()
            test_request = factory.get('/events/api/unified/?start=2025-01-01&end=2025-12-31')
            test_request.user = request.user
            
            response = fetch_unified_events(test_request)
            return response.status_code == 200
        except Exception:
            return False
    
    run_check('API', 'fetch_unified_events API',
              test_unified_events_api,
              'Run: ./scripts/simple_timezone_fix.sh')
    
    # CALENDAR SPECIFIC ISSUES
    def test_calendar_view():
        try:
            from events.views import calendar_view
            from django.test import RequestFactory
            
            factory = RequestFactory()
            test_request = factory.get('/events/calendar/')
            test_request.user = request.user
            
            response = calendar_view(test_request)
            return response.status_code == 200
        except Exception:
            return False
    
    run_check('CALENDAR', 'Calendar View Renders',
              test_calendar_view,
              'Check calendar view and template rendering')
    
    run_warning_check('CALENDAR', 'Maintenance Activities Count',
                      lambda: MaintenanceActivity.objects.count() > 0,
                      'No maintenance activities found - calendar may appear empty')
    
    # USER AUTHENTICATION
    run_check('AUTH', 'Admin User Exists',
              lambda: User.objects.filter(is_superuser=True).exists(),
              'Create admin user: python manage.py createsuperuser')
    
    # EXTERNAL DEPENDENCIES
    def test_redis():
        try:
            from django.core.cache import cache
            cache.set('health_test', 'value')
            return cache.get('health_test') == 'value'
        except Exception:
            return False
    
    run_check('DEPS', 'Redis Connection',
              test_redis,
              'Check Redis server connectivity')
    
    # Calculate health percentage
    if health_data['summary']['total_checks'] > 0:
        health_data['summary']['health_percentage'] = round(
            (health_data['summary']['passed'] * 100) / health_data['summary']['total_checks']
        )
    
    # Determine overall health status
    if health_data['summary']['health_percentage'] >= 90:
        health_data['summary']['status'] = 'EXCELLENT'
    elif health_data['summary']['health_percentage'] >= 75:
        health_data['summary']['status'] = 'GOOD'
    elif health_data['summary']['health_percentage'] >= 50:
        health_data['summary']['status'] = 'MODERATE'
    else:
        health_data['summary']['status'] = 'CRITICAL'
    
    return JsonResponse(health_data)


@login_required
def health_check_view(request):
    """Render the health check interface."""
    if not request.user.is_superuser:
        return render(request, 'core/access_denied.html', {'message': 'Access denied'})
    
    return render(request, 'core/health_check.html')


__all__ = ["monitoring_dashboard", "health_check_api", "endpoint_metrics_api", "toggle_monitoring", "run_health_check", "health_check", "simple_health_check", "clear_health_logs", "api_explorer", "system_health", "debug", "test_health", "test_database", "test_cache", "comprehensive_health_check", "database_stats", "backup_database", "populate_sample_data", "invalidate_cache_api", "database_stats_api", "system_health_check", "health_check_view"]
