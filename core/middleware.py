"""
Middleware for handling database connection issues and monitoring.
"""

import logging
import time
import psutil
import traceback
from django.db import connection
from django.http import JsonResponse
from django.core.cache import cache
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class DatabaseConnectionMiddleware(MiddlewareMixin):
    """
    Middleware to handle database connection issues gracefully.
    """
    
    def process_request(self, request):
        """Ensure database connection is healthy before processing request."""
        try:
            # Test database connection
            connection.ensure_connection()
            
            # If connection is closed, reconnect
            if connection.connection is None:
                connection.connect()
                
        except Exception as e:
            logger.error(f"Database connection error: {str(e)}")
            # Close and reconnect
            connection.close()
            try:
                connection.connect()
            except Exception as reconnect_error:
                logger.error(f"Failed to reconnect to database: {str(reconnect_error)}")
                return JsonResponse({
                    'error': 'Database connection issue',
                    'message': 'Please try again in a moment'
                }, status=503)
    
    def process_response(self, request, response):
        """Clean up database connections after response."""
        try:
            # Close any lingering connections
            connection.close_if_unusable_or_obsolete()
        except Exception as e:
            logger.error(f"Error closing database connection: {str(e)}")
        
        return response


class SystemMonitoringMiddleware(MiddlewareMixin):
    """
    Middleware to monitor system resources and endpoint performance.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.monitoring_enabled = getattr(settings, 'MONITORING_ENABLED', True)
        super().__init__(get_response)
    
    def process_request(self, request):
        """Record request start time and system metrics."""
        if not self.monitoring_enabled:
            return
        
        request.start_time = time.time()
        
        # Record system metrics
        try:
            system_metrics = self._get_system_metrics()
            request.system_metrics_start = system_metrics
        except Exception as e:
            logger.error(f"Error collecting system metrics: {str(e)}")
    
    def process_response(self, request, response):
        """Record response time and system metrics."""
        if not self.monitoring_enabled:
            return response
        
        try:
            # Calculate response time
            if hasattr(request, 'start_time'):
                response_time = time.time() - request.start_time
                
                # Store metrics
                self._record_endpoint_metrics(request, response, response_time)
                
                # Check for performance issues
                self._check_performance_thresholds(request, response_time)
                
        except Exception as e:
            logger.error(f"Error recording endpoint metrics: {str(e)}")
        
        return response
    
    def _get_system_metrics(self):
        """Get current system metrics."""
        try:
            return {
                'cpu_percent': psutil.cpu_percent(interval=0.1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_usage': psutil.disk_usage('/').percent,
                'timestamp': timezone.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting system metrics: {str(e)}")
            return {}
    
    def _record_endpoint_metrics(self, request, response, response_time):
        """Record endpoint performance metrics."""
        try:
            endpoint_key = f"{request.method}:{request.path}"
            
            # Store in cache for recent metrics
            cache_key = f"endpoint_metrics:{endpoint_key}"
            metrics = cache.get(cache_key, {
                'total_requests': 0,
                'total_time': 0,
                'error_count': 0,
                'last_request': None
            })
            
            metrics['total_requests'] += 1
            metrics['total_time'] += response_time
            metrics['last_request'] = timezone.now().isoformat()
            
            if response.status_code >= 400:
                metrics['error_count'] += 1
            
            # Calculate average response time
            metrics['avg_response_time'] = metrics['total_time'] / metrics['total_requests']
            
            # Store for 1 hour
            cache.set(cache_key, metrics, 3600)
            
            # Log slow requests
            if response_time > 5.0:  # 5 seconds threshold
                logger.warning(f"Slow request detected: {endpoint_key} took {response_time:.2f}s")
                
        except Exception as e:
            logger.error(f"Error recording endpoint metrics: {str(e)}")
    
    def _check_performance_thresholds(self, request, response_time):
        """Check if performance thresholds are exceeded."""
        try:
            # Check system resource thresholds
            if hasattr(request, 'system_metrics_start'):
                current_metrics = self._get_system_metrics()
                
                # High CPU usage
                if current_metrics.get('cpu_percent', 0) > 80:
                    logger.warning(f"High CPU usage detected: {current_metrics['cpu_percent']:.1f}%")
                
                # High memory usage
                if current_metrics.get('memory_percent', 0) > 80:
                    logger.warning(f"High memory usage detected: {current_metrics['memory_percent']:.1f}%")
                
                # High disk usage
                if current_metrics.get('disk_usage', 0) > 90:
                    logger.warning(f"High disk usage detected: {current_metrics['disk_usage']:.1f}%")
            
            # Check response time thresholds
            if response_time > 10.0:  # 10 seconds threshold
                logger.error(f"Very slow request: {request.path} took {response_time:.2f}s")
                
        except Exception as e:
            logger.error(f"Error checking performance thresholds: {str(e)}")


class ForcePasswordChangeMiddleware(MiddlewareMixin):
    """
    Middleware to force password change for users with default passwords.
    """
    
    def process_request(self, request):
        """Check if user needs to change password."""
        if request.user.is_authenticated:
            # Check if user has default password or needs to change it
            if hasattr(request.user, 'userprofile') and request.user.userprofile.force_password_change:
                if request.path not in ['/auth/change-password/', '/auth/logout/']:
                    from django.shortcuts import redirect
                    return redirect('change_password')
        
        return None