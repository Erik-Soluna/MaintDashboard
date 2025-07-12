"""
Management command for system health checks and monitoring.
"""

import json
import time
import psutil
from datetime import datetime
from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.db import connection
from django.conf import settings
from django.utils import timezone
from django.http import JsonResponse
from django.test import Client
from django.urls import reverse


class Command(BaseCommand):
    help = 'Perform system health checks and monitoring'

    def add_arguments(self, parser):
        parser.add_argument(
            '--endpoint',
            type=str,
            help='Specific endpoint to test (optional)',
        )
        parser.add_argument(
            '--output',
            type=str,
            default='console',
            choices=['console', 'json', 'file'],
            help='Output format',
        )
        parser.add_argument(
            '--file',
            type=str,
            help='Output file path (required if output=file)',
        )
        parser.add_argument(
            '--continuous',
            action='store_true',
            help='Run continuously with 30-second intervals',
        )

    def handle(self, *args, **options):
        if options['continuous']:
            self.run_continuous_monitoring()
        else:
            self.run_single_check(options)

    def run_continuous_monitoring(self):
        """Run continuous monitoring."""
        self.stdout.write('Starting continuous monitoring (Ctrl+C to stop)...')
        
        try:
            while True:
                health_data = self.perform_health_check()
                self.display_health_data(health_data, format='console')
                time.sleep(30)  # Wait 30 seconds between checks
        except KeyboardInterrupt:
            self.stdout.write('\nMonitoring stopped.')

    def run_single_check(self, options):
        """Run a single health check."""
        health_data = self.perform_health_check(options.get('endpoint'))
        
        output_format = options['output']
        if output_format == 'file':
            if not options['file']:
                self.stderr.write('Error: --file is required when output=file')
                return
            self.save_to_file(health_data, options['file'])
        else:
            self.display_health_data(health_data, output_format)

    def perform_health_check(self, specific_endpoint=None):
        """Perform comprehensive health check."""
        health_data = {
            'timestamp': timezone.now().isoformat(),
            'system_metrics': self.get_system_metrics(),
            'database_health': self.check_database_health(),
            'cache_health': self.check_cache_health(),
            'endpoint_metrics': self.get_endpoint_metrics(),
            'critical_endpoints': self.test_critical_endpoints(specific_endpoint),
            'disk_space': self.check_disk_space(),
            'overall_status': 'healthy'
        }
        
        # Determine overall status
        health_data['overall_status'] = self.determine_overall_status(health_data)
        
        return health_data

    def get_system_metrics(self):
        """Get current system metrics."""
        try:
            return {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_usage': psutil.disk_usage('/').percent,
                'load_average': psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None,
                'process_count': len(psutil.pids()),
                'boot_time': psutil.boot_time(),
                'network_io': dict(psutil.net_io_counters()._asdict()) if psutil.net_io_counters() else None
            }
        except Exception as e:
            return {'error': str(e)}

    def check_database_health(self):
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
                'connection_queries': connection.queries_logged if hasattr(connection, 'queries_logged') else 0
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }

    def check_cache_health(self):
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
                    'response_time': response_time
                }
            else:
                return {
                    'status': 'unhealthy',
                    'error': 'Cache read/write mismatch'
                }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }

    def get_endpoint_metrics(self):
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
            return {'error': str(e)}

    def test_critical_endpoints(self, specific_endpoint=None):
        """Test critical application endpoints."""
        critical_endpoints = [
            '/',
            '/maintenance/',
            '/maintenance/add/',
            '/equipment/',
            '/events/',
        ]
        
        if specific_endpoint:
            critical_endpoints = [specific_endpoint]
        
        client = Client()
        endpoint_results = {}
        
        for endpoint in critical_endpoints:
            try:
                start_time = time.time()
                response = client.get(endpoint)
                response_time = time.time() - start_time
                
                endpoint_results[endpoint] = {
                    'status_code': response.status_code,
                    'response_time': response_time,
                    'status': 'healthy' if response.status_code < 400 else 'unhealthy'
                }
            except Exception as e:
                endpoint_results[endpoint] = {
                    'status': 'unhealthy',
                    'error': str(e)
                }
        
        return endpoint_results

    def check_disk_space(self):
        """Check disk space usage."""
        try:
            disk_usage = psutil.disk_usage('/')
            return {
                'total': disk_usage.total,
                'used': disk_usage.used,
                'free': disk_usage.free,
                'percent': (disk_usage.used / disk_usage.total) * 100
            }
        except Exception as e:
            return {'error': str(e)}

    def determine_overall_status(self, health_data):
        """Determine overall system status."""
        # Check for critical issues
        if health_data['database_health'].get('status') == 'unhealthy':
            return 'critical'
        
        if health_data['cache_health'].get('status') == 'unhealthy':
            return 'warning'
        
        # Check system metrics
        system_metrics = health_data['system_metrics']
        if isinstance(system_metrics, dict) and 'error' not in system_metrics:
            if system_metrics.get('cpu_percent', 0) > 90:
                return 'critical'
            if system_metrics.get('memory_percent', 0) > 95:
                return 'critical'
            if system_metrics.get('disk_usage', 0) > 95:
                return 'critical'
        
        # Check critical endpoints
        critical_endpoints = health_data['critical_endpoints']
        unhealthy_endpoints = [
            endpoint for endpoint, data in critical_endpoints.items()
            if data.get('status') == 'unhealthy'
        ]
        
        if unhealthy_endpoints:
            return 'warning'
        
        return 'healthy'

    def display_health_data(self, health_data, format='console'):
        """Display health data in specified format."""
        if format == 'json':
            self.stdout.write(json.dumps(health_data, indent=2))
        else:
            self.display_console_format(health_data)

    def display_console_format(self, health_data):
        """Display health data in console format."""
        status = health_data['overall_status']
        status_color = {
            'healthy': self.style.SUCCESS,
            'warning': self.style.WARNING,
            'critical': self.style.ERROR
        }.get(status, self.style.SUCCESS)
        
        self.stdout.write(f"\n{'='*50}")
        self.stdout.write(f"System Health Check - {health_data['timestamp']}")
        self.stdout.write(f"{'='*50}")
        self.stdout.write(f"Overall Status: {status_color(status.upper())}")
        
        # System metrics
        self.stdout.write(f"\n--- System Metrics ---")
        system_metrics = health_data['system_metrics']
        if 'error' in system_metrics:
            self.stdout.write(f"Error: {system_metrics['error']}")
        else:
            self.stdout.write(f"CPU Usage: {system_metrics.get('cpu_percent', 0):.1f}%")
            self.stdout.write(f"Memory Usage: {system_metrics.get('memory_percent', 0):.1f}%")
            self.stdout.write(f"Disk Usage: {system_metrics.get('disk_usage', 0):.1f}%")
            self.stdout.write(f"Process Count: {system_metrics.get('process_count', 0)}")
        
        # Database health
        self.stdout.write(f"\n--- Database Health ---")
        db_health = health_data['database_health']
        if db_health.get('status') == 'healthy':
            self.stdout.write(f"Status: {self.style.SUCCESS('HEALTHY')}")
            self.stdout.write(f"Response Time: {db_health.get('response_time', 0):.3f}s")
        else:
            self.stdout.write(f"Status: {self.style.ERROR('UNHEALTHY')}")
            self.stdout.write(f"Error: {db_health.get('error', 'Unknown')}")
        
        # Cache health
        self.stdout.write(f"\n--- Cache Health ---")
        cache_health = health_data['cache_health']
        if cache_health.get('status') == 'healthy':
            self.stdout.write(f"Status: {self.style.SUCCESS('HEALTHY')}")
            self.stdout.write(f"Response Time: {cache_health.get('response_time', 0):.3f}s")
        else:
            self.stdout.write(f"Status: {self.style.ERROR('UNHEALTHY')}")
            self.stdout.write(f"Error: {cache_health.get('error', 'Unknown')}")
        
        # Critical endpoints
        self.stdout.write(f"\n--- Critical Endpoints ---")
        for endpoint, data in health_data['critical_endpoints'].items():
            if data.get('status') == 'healthy':
                self.stdout.write(f"{endpoint}: {self.style.SUCCESS('HEALTHY')} ({data.get('response_time', 0):.3f}s)")
            else:
                self.stdout.write(f"{endpoint}: {self.style.ERROR('UNHEALTHY')} - {data.get('error', 'Unknown')}")
        
        # Endpoint metrics summary
        self.stdout.write(f"\n--- Endpoint Metrics Summary ---")
        endpoint_metrics = health_data['endpoint_metrics']
        if endpoint_metrics and 'error' not in endpoint_metrics:
            for endpoint, metrics in endpoint_metrics.items():
                self.stdout.write(
                    f"{endpoint}: {metrics.get('total_requests', 0)} requests, "
                    f"avg {metrics.get('avg_response_time', 0):.3f}s, "
                    f"{metrics.get('error_count', 0)} errors"
                )
        
        self.stdout.write(f"\n{'='*50}")

    def save_to_file(self, health_data, filepath):
        """Save health data to file."""
        try:
            with open(filepath, 'w') as f:
                json.dump(health_data, f, indent=2)
            self.stdout.write(f"Health data saved to {filepath}")
        except Exception as e:
            self.stderr.write(f"Error saving to file: {str(e)}")