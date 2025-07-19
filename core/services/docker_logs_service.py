"""
Docker Logs Service
Provides secure access to Docker container logs with toggle support and security measures.
"""

import logging
import re
import time
import subprocess
import os
from typing import Optional, Dict, List, Any
from django.conf import settings
from django.core.cache import cache
from django.contrib.auth.models import User
from django.utils import timezone


logger = logging.getLogger(__name__)


class DockerLogsService:
    """
    Service for managing Docker container logs access with security controls.
    """
    
    def __init__(self):
        """Initialize the service with configuration from settings."""
        self.config = getattr(settings, 'DOCKER_LOGS_CONFIG', {
            'enabled': False,
            'debug_only': True,
            'max_lines': 1000,
            'rate_limit': 10,
            'timeout': 30,
            'require_superuser': True,
        })
        self.logger = logging.getLogger(__name__)
    
    def is_enabled(self) -> bool:
        """Check if Docker logs functionality is enabled."""
        return self.config.get('enabled', False)
    
    def is_debug_only(self) -> bool:
        """Check if Docker logs are restricted to debug mode only."""
        return self.config.get('debug_only', True)
    
    def can_access(self, user: User) -> bool:
        """
        Check if user can access Docker logs functionality.
        
        Args:
            user: Django user object
            
        Returns:
            bool: True if user can access, False otherwise
        """
        if not self.is_enabled():
            self.logger.warning(f"Docker logs access denied for user {user.username}: feature disabled")
            return False
        
        if self.config.get('require_superuser', True) and not user.is_superuser:
            self.logger.warning(f"Docker logs access denied for user {user.username}: not superuser")
            return False
        
        return True
    
    def sanitize_container_name(self, name: str) -> Optional[str]:
        """
        Sanitize container name to prevent command injection.
        
        Args:
            name: Raw container name from user input
            
        Returns:
            Optional[str]: Sanitized container name or None if invalid
        """
        if not name or not isinstance(name, str):
            return None
        
        # Limit length
        if len(name) > 100:
            self.logger.warning(f"Container name too long: {len(name)} characters")
            return None
        
        # Only allow alphanumeric, hyphens, underscores, and dots
        # This prevents command injection while allowing valid container names
        if not re.match(r'^[a-zA-Z0-9._-]+$', name):
            self.logger.warning(f"Invalid container name format: {name}")
            return None
        
        return name
    
    def check_rate_limit(self, user_id: int) -> bool:
        """
        Check if user has exceeded rate limit for Docker logs requests.
        
        Args:
            user_id: User ID to check rate limit for
            
        Returns:
            bool: True if within rate limit, False if exceeded
        """
        cache_key = f"docker_logs_rate_limit:{user_id}"
        request_count = cache.get(cache_key, 0)
        rate_limit = self.config.get('rate_limit', 10)
        
        if request_count >= rate_limit:
            self.logger.warning(f"Rate limit exceeded for user {user_id}: {request_count} requests")
            return False
        
        # Increment counter and set expiry
        cache.set(cache_key, request_count + 1, 60)  # 1 minute expiry
        return True
    
    def log_access(self, user: User, container: str, success: bool, method: str = "unknown", error: str = None):
        """
        Log Docker logs access for audit purposes.
        
        Args:
            user: Django user object
            container: Container name accessed
            success: Whether the access was successful
            method: Method used to access logs
            error: Error message if access failed
        """
        log_data = {
            'user_id': user.id,
            'username': user.username,
            'container_name': container,
            'success': success,
            'method': method,
            'timestamp': timezone.now().isoformat(),
            'ip_address': getattr(user, 'last_login_ip', 'unknown'),
        }
        
        if error:
            log_data['error'] = error
        
        if success:
            self.logger.info(f"Docker logs access: {log_data}")
        else:
            self.logger.warning(f"Docker logs access failed: {log_data}")
    
    def get_containers(self, user: User) -> Dict[str, Any]:
        """
        Get list of available Docker containers using log streaming service.
        
        Args:
            user: Django user object
            
        Returns:
            Dict containing containers list and any warnings
        """
        if not self.can_access(user):
            return {
                'success': False,
                'error': 'Access denied',
                'containers': []
            }
        
        if not self.check_rate_limit(user.id):
            return {
                'success': False,
                'error': 'Rate limit exceeded',
                'containers': []
            }
        
        try:
            # Use the log streaming service to get containers
            from core.services.log_streaming_service import LogStreamingService
            streaming_service = LogStreamingService()
            
            containers = streaming_service.get_available_containers()
            
            # Format containers for API response
            formatted_containers = []
            for container in containers:
                formatted_containers.append({
                    'name': container['name'],
                    'image': container.get('image', 'Unknown'),
                    'status': container.get('status', 'Unknown'),
                    'ports': 'N/A',
                    'source': container.get('source', 'unknown'),
                    'log_file': container.get('log_file')
                })
            
            # Log successful access
            self.log_access(user, "container_list", True, "get_containers")
            
            return {
                'success': True,
                'containers': formatted_containers,
                'warning': None
            }
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.log_access(user, "container_list", False, "get_containers", error_msg)
            return {
                'success': False,
                'error': error_msg,
                'containers': []
            }
    
    def get_logs(self, user: User, container_name: str, lines: int = 100, follow: bool = False) -> Dict[str, Any]:
        """
        Get logs for a specific Docker container using log streaming service.
        
        Args:
            user: Django user object
            container_name: Name of the container
            lines: Number of lines to retrieve
            follow: Whether to follow logs in real-time
            
        Returns:
            Dict containing logs and status information
        """
        if not self.can_access(user):
            return {
                'success': False,
                'error': 'Access denied'
            }
        
        if not self.check_rate_limit(user.id):
            return {
                'success': False,
                'error': 'Rate limit exceeded'
            }
        
        # Sanitize inputs
        sanitized_container = self.sanitize_container_name(container_name)
        if not sanitized_container:
            error_msg = "Invalid container name"
            self.log_access(user, container_name, False, "get_logs", error_msg)
            return {
                'success': False,
                'error': error_msg
            }
        
        # Validate lines parameter
        max_lines = self.config.get('max_lines', 1000)
        if lines > max_lines:
            lines = max_lines
        
        try:
            # Use the log streaming service
            from core.services.log_streaming_service import LogStreamingService
            streaming_service = LogStreamingService()
            
            # Get logs for the container
            logs_content = streaming_service.get_container_logs(sanitized_container, lines)
            
            if logs_content and not logs_content.startswith("Container '") and not logs_content.startswith("Logs for "):
                self.log_access(user, sanitized_container, True, "log_streaming")
                return {
                    'success': True,
                    'logs': logs_content,
                    'container': sanitized_container,
                    'lines_returned': len(logs_content.splitlines()),
                    'method': 'log_streaming'
                }
            else:
                error_msg = f'Could not retrieve logs for container "{sanitized_container}"'
                self.log_access(user, sanitized_container, False, "log_streaming", error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'suggestion': 'Container logs may not be accessible or the container may not exist.'
                }
                
        except Exception as e:
            error_msg = f'Unexpected error: {str(e)}'
            self.log_access(user, sanitized_container, False, "log_streaming", error_msg)
            return {
                'success': False,
                'error': error_msg
            } 