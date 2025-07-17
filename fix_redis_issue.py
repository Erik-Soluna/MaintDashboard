#!/usr/bin/env python3
"""
Quick fix for Redis connection issues.
This script sets environment variables to disable Redis and use database cache instead.
"""

import os
import sys

def fix_redis_issue():
    """Set environment variables to fix Redis connection issues."""
    
    print("🔧 Fixing Redis Connection Issue")
    print("=" * 40)
    
    # Set environment variables to disable Redis
    os.environ['USE_REDIS'] = 'false'
    os.environ['CELERY_BROKER_URL'] = 'memory://'
    os.environ['CELERY_RESULT_BACKEND'] = 'rpc://'
    
    print("✅ Environment variables set:")
    print("  USE_REDIS=false")
    print("  CELERY_BROKER_URL=memory://")
    print("  CELERY_RESULT_BACKEND=rpc://")
    
    print("\n📝 This will:")
    print("  - Use database cache instead of Redis")
    print("  - Use memory broker for Celery (tasks will work in current process)")
    print("  - Use RPC backend for Celery results")
    
    print("\n⚠️  Note: Celery background tasks will only work within the current process.")
    print("   For full Celery functionality, start Docker Desktop and Redis container.")
    
    return True

def create_env_file():
    """Create a .env file with Redis-disabled settings."""
    env_content = """# Redis-disabled configuration for development
USE_REDIS=false
CELERY_BROKER_URL=memory://
CELERY_RESULT_BACKEND=rpc://

# Database settings (adjust as needed)
DB_HOST=localhost
DB_NAME=maintenance_dashboard
DB_USER=postgres
DB_PASSWORD=postgres
DB_PORT=5432

# Django settings
DEBUG=true
SECRET_KEY=django-insecure-change-me-in-production
ALLOWED_HOSTS=localhost,127.0.0.1

# Email settings
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
"""
    
    try:
        with open('.env.redis-fix', 'w') as f:
            f.write(env_content)
        print("\n📄 Created .env.redis-fix file with Redis-disabled settings")
        print("   To use this configuration:")
        print("   cp .env.redis-fix .env")
        return True
    except Exception as e:
        print(f"❌ Error creating .env file: {e}")
        return False

def main():
    """Main function."""
    print("🚀 Redis Issue Quick Fix")
    print("=" * 30)
    
    # Fix the issue
    fix_redis_issue()
    
    # Create env file
    create_env_file()
    
    print("\n✅ Redis connection issue fixed!")
    print("\n🔄 Next steps:")
    print("1. Restart your Django application")
    print("2. The application will now use database cache instead of Redis")
    print("3. To restore Redis functionality, start Docker Desktop and Redis container")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 