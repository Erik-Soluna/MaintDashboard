#!/usr/bin/env python3
"""
Simple health check script for Docker containers.
This script checks basic application health and exits with appropriate status codes.
"""

import sys
import time
import requests
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_health():
    """Check application health and return status."""
    try:
        # Get health check URL from environment or use default
        health_url = os.environ.get('HEALTH_CHECK_URL', 'http://localhost:8000/health/simple/')
        
        # Set timeout for health check
        timeout = int(os.environ.get('HEALTH_CHECK_TIMEOUT', 5))
        
        # Make health check request
        start_time = time.time()
        response = requests.get(health_url, timeout=timeout)
        response_time = time.time() - start_time
        
        # Check response status
        if response.status_code == 200:
            logger.info(f"Health check passed in {response_time:.3f}s")
            return 0
        else:
            logger.error(f"Health check failed with status {response.status_code}")
            return 1
            
    except requests.exceptions.Timeout:
        logger.error("Health check timed out")
        return 1
    except requests.exceptions.ConnectionError:
        logger.error("Health check connection failed")
        return 1
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(check_health())
