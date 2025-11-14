"""
Middleware for handling database connection issues and monitoring.
"""

import logging
import time
import traceback
from django.db import connection, OperationalError
from django.http import JsonResponse
from django.core.cache import cache
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from django.utils import timezone

# Try to import psutil, but handle gracefully if not available
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

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
                
        except (OperationalError, Exception) as e:
            logger.error(f"Database connection error: {str(e)}")
            # Close and reconnect
            connection.close()
            try:
                connection.connect()
            except Exception as reconnect_error:
                logger.error(f"Failed to reconnect to database: {str(reconnect_error)}")
                # Only return JSON error for API requests
                if request.path.startswith('/api/') or request.headers.get('Accept', '').startswith('application/json'):
                    return JsonResponse({
                        'error': 'Database connection issue',
                        'message': 'Please try again in a moment'
                    }, status=503)
        
        return None
    
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
    Optimized to reduce CPU overhead by sampling requests and caching metrics.
    """
    def __init__(self, get_response):
        super().__init__(get_response)
        self.monitoring_enabled = getattr(settings, 'MONITORING_ENABLED', True) and PSUTIL_AVAILABLE
        # Cache metrics to avoid expensive CPU measurement on every request
        self._metrics_cache = {}
        self._cache_timeout = 5.0  # Cache metrics for 5 seconds
        self._sample_rate = 0.1  # Only measure on 10% of requests to reduce overhead
        import random
        self._random = random
    
    def process_request(self, request):
        """Record request start time and system metrics."""
        if not self.monitoring_enabled:
            return None
        
        request.start_time = time.time()
        
        # Only collect metrics on a sample of requests to reduce overhead
        # Skip metrics collection for most requests to reduce CPU usage
        if self._random.random() < self._sample_rate:
            # Record system metrics (cached to avoid expensive calls)
            try:
                system_metrics = self._get_system_metrics_cached()
                request.system_metrics_start = system_metrics
            except Exception as e:
                logger.error(f"Error collecting system metrics: {str(e)}")
        
        return None
    
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
    
    def _get_system_metrics_cached(self):
        """Get current system metrics with caching to reduce CPU overhead."""
        if not PSUTIL_AVAILABLE:
            return {}
        
        current_time = time.time()
        cache_key = 'system_metrics'
        
        # Check cache first
        if cache_key in self._metrics_cache:
            cached_metrics, cached_time = self._metrics_cache[cache_key]
            if current_time - cached_time < self._cache_timeout:
                return cached_metrics
        
        # Cache expired or doesn't exist - get fresh metrics
        try:
            # Use interval=0 to get non-blocking CPU measurement (uses last measurement)
            # This is much faster than interval=0.1 which blocks for 100ms
            metrics = {
                'cpu_percent': psutil.cpu_percent(interval=0),  # Non-blocking
                'memory_percent': psutil.virtual_memory().percent,
                'disk_usage': psutil.disk_usage('/').percent,
                'timestamp': timezone.now().isoformat()
            }
            # Cache the metrics
            self._metrics_cache[cache_key] = (metrics, current_time)
            return metrics
        except Exception as e:
            logger.error(f"Error getting system metrics: {str(e)}")
            return {}
    
    def _get_system_metrics(self):
        """Get current system metrics (legacy method, uses cached version)."""
        return self._get_system_metrics_cached()
    
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
            slow_threshold = getattr(settings, 'MONITORING_SLOW_REQUEST_THRESHOLD', 5.0)
            if response_time > slow_threshold:
                logger.warning(f"Slow request detected: {endpoint_key} took {response_time:.2f}s")
                
        except Exception as e:
            logger.error(f"Error recording endpoint metrics: {str(e)}")
    
    def _check_performance_thresholds(self, request, response_time):
        """Check if performance thresholds are exceeded."""
        if not PSUTIL_AVAILABLE:
            return
            
        try:
            # Only check thresholds on sampled requests to reduce overhead
            if not hasattr(request, 'system_metrics_start'):
                return
            
            # Use cached metrics instead of fetching new ones
            current_metrics = request.system_metrics_start if hasattr(request, 'system_metrics_start') else self._get_system_metrics_cached()
            
            # Get thresholds from settings
            cpu_threshold = getattr(settings, 'MONITORING_CPU_THRESHOLD', 80.0)
            memory_threshold = getattr(settings, 'MONITORING_MEMORY_THRESHOLD', 80.0)
            disk_threshold = getattr(settings, 'MONITORING_DISK_THRESHOLD', 90.0)
            
            # High CPU usage (only log if significantly high to reduce log spam)
            if current_metrics.get('cpu_percent', 0) > cpu_threshold:
                logger.warning(f"High CPU usage detected: {current_metrics['cpu_percent']:.1f}%")
            
            # High memory usage
            if current_metrics.get('memory_percent', 0) > memory_threshold:
                logger.warning(f"High memory usage detected: {current_metrics['memory_percent']:.1f}%")
            
            # High disk usage
            if current_metrics.get('disk_usage', 0) > disk_threshold:
                logger.warning(f"High disk usage detected: {current_metrics['disk_usage']:.1f}%")
            
            # Check response time thresholds
            very_slow_threshold = getattr(settings, 'MONITORING_VERY_SLOW_REQUEST_THRESHOLD', 10.0)
            if response_time > very_slow_threshold:
                logger.error(f"Very slow request: {request.path} took {response_time:.2f}s")
                
        except Exception as e:
            logger.error(f"Error checking performance thresholds: {str(e)}")


# ForcePasswordChangeMiddleware removed due to import conflicts
# This functionality can be implemented in views or decorators if needed