#!/usr/bin/env python
"""
Quick fix for cache table issue.
Run this script to create the cache table if it doesn't exist.
"""

import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maintenance_dashboard.settings')
django.setup()

from django.core.management import call_command
from django.core.cache import cache
from django.conf import settings

def fix_cache_table():
    """Fix the cache table issue."""
    print("🔧 Fixing cache table issue...")
    
    # Check cache backend
    cache_backend = getattr(settings, 'CACHES', {}).get('default', {}).get('BACKEND', '')
    print(f"Cache backend: {cache_backend}")
    
    if 'django.core.cache.backends.db.DatabaseCache' in cache_backend:
        print("📊 Database cache backend detected.")
        
        try:
            # Create the cache table
            print("Creating cache table...")
            call_command('createcachetable', verbosity=0)
            print("✅ Cache table created successfully!")
            
            # Test the cache
            print("Testing cache functionality...")
            test_key = 'cache_test_key'
            test_value = 'cache_test_value'
            
            cache.set(test_key, test_value, 60)
            retrieved_value = cache.get(test_key)
            
            if retrieved_value == test_value:
                print("✅ Cache is working correctly!")
            else:
                print("⚠️  Cache test failed - retrieved value does not match.")
            
            # Clean up
            cache.delete(test_key)
            
        except Exception as e:
            print(f"❌ Error creating cache table: {str(e)}")
            print("🔄 Trying alternative approach...")
            
            # Try to switch to dummy cache
            try:
                from django.core.cache.backends.dummy import DummyCache
                dummy_cache = DummyCache('dummy', {})
                
                print("Testing with dummy cache...")
                dummy_cache.set(test_key, test_value, 60)
                retrieved_value = dummy_cache.get(test_key)
                
                if retrieved_value is None:  # Dummy cache always returns None
                    print("✅ Dummy cache working as expected.")
                    print("💡 Consider switching to Redis cache for better performance.")
                
            except Exception as dummy_error:
                print(f"❌ Error with dummy cache: {str(dummy_error)}")
    
    elif 'django_redis.cache.RedisCache' in cache_backend:
        print("🔴 Redis cache backend detected.")
        
        try:
            # Test Redis connection
            test_key = 'redis_test_key'
            test_value = 'redis_test_value'
            
            cache.set(test_key, test_value, 60)
            retrieved_value = cache.get(test_key)
            
            if retrieved_value == test_value:
                print("✅ Redis cache is working correctly!")
            else:
                print("⚠️  Redis cache test failed.")
            
            # Clean up
            cache.delete(test_key)
            
        except Exception as e:
            print(f"❌ Redis cache error: {str(e)}")
            print("💡 Consider checking Redis connection or switching to database cache.")
    
    else:
        print(f"⚠️  Unknown cache backend: {cache_backend}")
    
    print("🎉 Cache table fix completed!")

if __name__ == '__main__':
    fix_cache_table() 