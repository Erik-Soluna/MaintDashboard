#!/usr/bin/env python3
"""
Test script to verify debug and system health functionality.
"""

import requests
import json
import time

BASE_URL = "http://localhost:4405"

def test_health_endpoints():
    """Test all health endpoints."""
    print("🔍 Testing Health Endpoints...")
    
    # Test simple health check
    try:
        response = requests.get(f"{BASE_URL}/core/health/simple/")
        print(f"✅ Simple Health Check: {response.status_code}")
    except Exception as e:
        print(f"❌ Simple Health Check Failed: {e}")
    
    # Test comprehensive health check
    try:
        response = requests.get(f"{BASE_URL}/core/health-check/comprehensive/")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Comprehensive Health Check: {data['overall_status']}")
            print(f"   Database: {data['components']['database']['status']}")
            print(f"   Cache: {data['components']['cache']['status']}")
            print(f"   System CPU: {data['components']['system']['cpu_percent']}%")
        else:
            print(f"❌ Comprehensive Health Check Failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Comprehensive Health Check Error: {e}")

def test_debug_endpoints():
    """Test debug-related endpoints."""
    print("\n🔍 Testing Debug Endpoints...")
    
    # Test test health endpoint
    try:
        response = requests.get(f"{BASE_URL}/core/api/test-health/")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Test Health API: {data['status']}")
        else:
            print(f"❌ Test Health API Failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Test Health API Error: {e}")

def test_container_status():
    """Test container status from host."""
    print("\n🔍 Testing Container Status...")
    
    try:
        import subprocess
        result = subprocess.run(['docker', 'ps', '--format', 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ Docker containers status:")
            lines = result.stdout.strip().split('\n')
            for line in lines[1:]:  # Skip header
                if line.strip():
                    print(f"   {line}")
        else:
            print(f"❌ Docker command failed: {result.stderr}")
    except Exception as e:
        print(f"❌ Container status check failed: {e}")

def main():
    """Main test function."""
    print("🚀 Testing Debug and System Health Functionality")
    print("=" * 50)
    
    # Wait a moment for services to be ready
    print("⏳ Waiting for services to be ready...")
    time.sleep(2)
    
    test_health_endpoints()
    test_debug_endpoints()
    test_container_status()
    
    print("\n" + "=" * 50)
    print("🎉 Debug functionality test completed!")
    print("\n📋 Next Steps:")
    print("1. Open http://localhost:4405 in your browser")
    print("2. Login with admin/temppass123")
    print("3. Navigate to Settings > Debug & Diagnostics")
    print("4. Test the following features:")
    print("   - System Health & Diagnostics (should show container status)")
    print("   - Test All Components (should show debug messages)")
    print("   - Clear Database (should show confirmation modal)")
    print("   - Populate Demo Data (should show progress)")
    print("   - Generate PODs (should show results)")
    print("   - Playwright Debug (should handle undefined responses)")

if __name__ == "__main__":
    main() 