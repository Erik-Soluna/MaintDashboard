#!/usr/bin/env python3
"""
Test Redis connectivity and provide troubleshooting information.
"""

import os
import sys
import socket
import subprocess
from urllib.parse import urlparse

def test_redis_connection(host='redis', port=6379, timeout=5):
    """Test if Redis is reachable."""
    try:
        # Test basic socket connection
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            print(f"✅ Redis connection to {host}:{port} successful")
            return True
        else:
            print(f"❌ Redis connection to {host}:{port} failed (error code: {result})")
            return False
    except Exception as e:
        print(f"❌ Redis connection test failed: {e}")
        return False

def test_dns_resolution(hostname):
    """Test DNS resolution for a hostname."""
    try:
        ip = socket.gethostbyname(hostname)
        print(f"✅ DNS resolution for '{hostname}' successful: {ip}")
        return True
    except socket.gaierror as e:
        print(f"❌ DNS resolution for '{hostname}' failed: {e}")
        return False

def check_docker_status():
    """Check if Docker is running and containers are up."""
    try:
        # Check if Docker is running
        result = subprocess.run(['docker', 'ps'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ Docker is running")
            
            # Check for Redis container
            if 'redis' in result.stdout.lower():
                print("✅ Redis container found in Docker")
                return True
            else:
                print("⚠️  Redis container not found in running containers")
                return False
        else:
            print("❌ Docker is not running or not accessible")
            return False
    except FileNotFoundError:
        print("❌ Docker command not found. Is Docker installed?")
        return False
    except subprocess.TimeoutExpired:
        print("❌ Docker command timed out")
        return False
    except Exception as e:
        print(f"❌ Error checking Docker status: {e}")
        return False

def check_environment_variables():
    """Check Redis-related environment variables."""
    redis_vars = {
        'REDIS_HOST': os.environ.get('REDIS_HOST', 'Not set (default: redis)'),
        'REDIS_PORT': os.environ.get('REDIS_PORT', 'Not set (default: 6379)'),
        'REDIS_PASSWORD': os.environ.get('REDIS_PASSWORD', 'Not set'),
        'CELERY_BROKER_URL': os.environ.get('CELERY_BROKER_URL', 'Not set'),
        'CELERY_RESULT_BACKEND': os.environ.get('CELERY_RESULT_BACKEND', 'Not set'),
    }
    
    print("\n📋 Environment Variables:")
    for var, value in redis_vars.items():
        if 'PASSWORD' in var and value != 'Not set':
            print(f"  {var}: {'*' * len(value)}")
        else:
            print(f"  {var}: {value}")

def provide_troubleshooting_steps():
    """Provide troubleshooting steps for Redis connection issues."""
    print("\n🔧 Troubleshooting Steps:")
    print("1. Start Docker Desktop if not running")
    print("2. Check if Redis container is running:")
    print("   docker ps | grep redis")
    print("3. Start Redis container if needed:")
    print("   docker-compose up -d redis")
    print("4. Check Redis logs:")
    print("   docker logs <redis-container-name>")
    print("5. Test Redis connection manually:")
    print("   docker exec -it <redis-container-name> redis-cli ping")
    print("6. If using local Redis, ensure Redis server is running:")
    print("   redis-server --daemonize yes")
    print("7. Check network connectivity:")
    print("   ping redis")
    print("   telnet redis 6379")

def main():
    """Main function to test Redis connectivity."""
    print("🔍 Redis Connectivity Test")
    print("=" * 50)
    
    # Check environment variables
    check_environment_variables()
    
    # Get Redis host and port from environment or use defaults
    redis_host = os.environ.get('REDIS_HOST', 'redis')
    redis_port = int(os.environ.get('REDIS_PORT', 6379))
    
    print(f"\n🌐 Testing Redis connection to {redis_host}:{redis_port}")
    
    # Test DNS resolution
    dns_ok = test_dns_resolution(redis_host)
    
    # Test Redis connection
    redis_ok = test_redis_connection(redis_host, redis_port)
    
    # Check Docker status
    docker_ok = check_docker_status()
    
    print("\n📊 Summary:")
    print(f"  DNS Resolution: {'✅' if dns_ok else '❌'}")
    print(f"  Redis Connection: {'✅' if redis_ok else '❌'}")
    print(f"  Docker Status: {'✅' if docker_ok else '❌'}")
    
    if not redis_ok:
        provide_troubleshooting_steps()
        
        print("\n💡 Quick Fixes:")
        print("1. For local development, set REDIS_HOST=localhost")
        print("2. For Docker, ensure Redis container is running")
        print("3. For production, check Redis server status and network connectivity")
        
        # Suggest alternative configurations
        print("\n🔧 Alternative Configurations:")
        print("1. Use localhost for local development:")
        print("   export REDIS_HOST=localhost")
        print("2. Use database cache instead of Redis:")
        print("   export USE_REDIS=false")
        print("3. Use dummy cache for testing:")
        print("   export USE_REDIS=false")
    
    return redis_ok

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 