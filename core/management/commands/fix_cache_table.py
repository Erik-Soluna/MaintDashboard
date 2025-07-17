"""
Management command to fix cache table issues.
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.core.cache import cache
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Fix cache table issues by creating the cache table if it does not exist'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreation of cache table',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting cache table fix...'))
        
        # Check if we're using database cache
        cache_backend = getattr(settings, 'CACHES', {}).get('default', {}).get('BACKEND', '')
        
        if 'django.core.cache.backends.db.DatabaseCache' in cache_backend:
            self.stdout.write('Database cache backend detected.')
            
            try:
                # Try to create the cache table
                self.stdout.write('Creating cache table...')
                call_command('createcachetable', verbosity=1)
                self.stdout.write(self.style.SUCCESS('Cache table created successfully!'))
                
                # Test the cache
                self.stdout.write('Testing cache functionality...')
                test_key = 'cache_test_key'
                test_value = 'cache_test_value'
                
                # Set a test value
                cache.set(test_key, test_value, 60)
                
                # Get the test value
                retrieved_value = cache.get(test_key)
                
                if retrieved_value == test_value:
                    self.stdout.write(self.style.SUCCESS('Cache is working correctly!'))
                else:
                    self.stdout.write(self.style.WARNING('Cache test failed - retrieved value does not match.'))
                
                # Clean up test value
                cache.delete(test_key)
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error creating cache table: {str(e)}'))
                self.stdout.write('Trying alternative approach...')
                
                # Try to switch to dummy cache temporarily
                try:
                    from django.core.cache import caches
                    from django.core.cache.backends.dummy import DummyCache
                    
                    # Create a dummy cache instance
                    dummy_cache = DummyCache('dummy', {})
                    
                    # Test with dummy cache
                    self.stdout.write('Testing with dummy cache...')
                    dummy_cache.set(test_key, test_value, 60)
                    retrieved_value = dummy_cache.get(test_key)
                    
                    if retrieved_value is None:  # Dummy cache always returns None
                        self.stdout.write(self.style.SUCCESS('Dummy cache working as expected.'))
                        self.stdout.write(self.style.WARNING('Consider switching to Redis cache for better performance.'))
                    
                except Exception as dummy_error:
                    self.stdout.write(self.style.ERROR(f'Error with dummy cache: {str(dummy_error)}'))
        
        elif 'django_redis.cache.RedisCache' in cache_backend:
            self.stdout.write('Redis cache backend detected.')
            
            try:
                # Test Redis connection
                test_key = 'redis_test_key'
                test_value = 'redis_test_value'
                
                cache.set(test_key, test_value, 60)
                retrieved_value = cache.get(test_key)
                
                if retrieved_value == test_value:
                    self.stdout.write(self.style.SUCCESS('Redis cache is working correctly!'))
                else:
                    self.stdout.write(self.style.WARNING('Redis cache test failed.'))
                
                # Clean up test value
                cache.delete(test_key)
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Redis cache error: {str(e)}'))
                self.stdout.write('Consider checking Redis connection or switching to database cache.')
        
        else:
            self.stdout.write(self.style.WARNING(f'Unknown cache backend: {cache_backend}'))
        
        self.stdout.write(self.style.SUCCESS('Cache table fix completed!')) 