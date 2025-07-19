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
        Get list of available Docker containers.
        
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
        
        containers = []
        warning = None
        
        try:
            # Get hostname for current container
            hostname = os.environ.get('HOSTNAME', '')
            
            # Approach 1: Try using Docker Python library
            try:
                import docker
                client = docker.from_env(timeout=5)
                docker_containers = client.containers.list()
                
                for container in docker_containers:
                    try:
                        container_info = {
                            'name': container.name,
                            'image': container.image.tags[0] if container.image.tags else container.image.id,
                            'status': container.status,
                            'ports': ', '.join([f"{k}:{v[0]['HostPort']}" for k, v in container.ports.items()]) if container.ports else 'N/A'
                        }
                        containers.append(container_info)
                    except Exception as container_error:
                        self.logger.warning(f"Error getting container info: {container_error}")
                        continue
                
                # Add current container if not already present
                if hostname and not any(c['name'] == hostname for c in containers):
                    containers.insert(0, {
                        'name': hostname,
                        'image': 'Current Container',
                        'status': 'Running',
                        'ports': 'N/A'
                    })
                    
            except ImportError:
                warning = "Docker Python library not available"
            except Exception as e:
                warning = f"Docker API error: {str(e)}"
            
            # Approach 2: Fallback to docker command
            if not containers:
                try:
                    docker_socket = '/var/run/docker.sock'
                    if os.path.exists(docker_socket):
                        cmd = ['docker', '--host', 'unix:///var/run/docker.sock', 'ps', '--format', 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}']
                    else:
                        cmd = ['docker', 'ps', '--format', 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}']
                    
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    
                    if result.returncode == 0:
                        lines = result.stdout.strip().split('\n')
                        for line in lines[1:]:  # Skip header
                            if line.strip():
                                parts = line.split('\t')
                                if len(parts) >= 4:
                                    containers.append({
                                        'name': parts[0],
                                        'image': parts[1],
                                        'status': parts[2],
                                        'ports': parts[3]
                                    })
                        
                        # Add current container if not already present
                        if hostname and not any(c['name'] == hostname for c in containers):
                            containers.insert(0, {
                                'name': hostname,
                                'image': 'Current Container',
                                'status': 'Running',
                                'ports': 'N/A'
                            })
                    else:
                        warning = f'Docker command failed: {result.stderr}'
                        
                except Exception as e:
                    warning = f"Subprocess error: {str(e)}"
            
            # Approach 3: Provide fallback containers
            if not containers:
                if hostname:
                    containers.append({
                        'name': hostname,
                        'image': 'Current Container (Docker not accessible)',
                        'status': 'Running',
                        'ports': 'N/A'
                    })
                
                # Add common container names
                common_containers = [
                    'maintdashboard_web_1',
                    'maintdashboard_db_1', 
                    'maintdashboard_redis_1',
                    'maintdashboard_celery_1',
                    'maintdashboard_nginx_1'
                ]
                
                for container_name in common_containers:
                    containers.append({
                        'name': container_name,
                        'image': 'Unknown (Docker not accessible)',
                        'status': 'Unknown',
                        'ports': 'N/A'
                    })
                
                warning = 'Docker not accessible. Showing fallback container list.'
            
            # Log successful access
            self.log_access(user, "container_list", True, "get_containers")
            
            return {
                'success': True,
                'containers': containers,
                'warning': warning
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
        Get logs for a specific Docker container.
        
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
        
        logs_content = None
        error_message = None
        method_used = "unknown"
        
        try:
            # Approach 1: Try using Docker Python library
            try:
                import docker
                client = docker.from_env(timeout=self.config.get('timeout', 30))
                container = client.containers.get(sanitized_container)
                logs = container.logs(tail=lines, follow=follow, timestamps=True)
                
                if isinstance(logs, bytes):
                    logs_content = logs.decode('utf-8', errors='replace')
                else:
                    logs_content = logs
                
                method_used = "docker_api"
                
            except ImportError:
                error_message = "Docker Python library not available"
            except Exception as e:
                error_message = f"Docker API error: {str(e)}"
            
            # Approach 2: Try docker command with socket mount
            if not logs_content:
                try:
                    docker_socket = '/var/run/docker.sock'
                    if os.path.exists(docker_socket):
                        cmd = ['docker', '--host', 'unix:///var/run/docker.sock', 'logs', '--tail', str(lines)]
                        if follow:
                            cmd.append('--follow')
                        cmd.append(sanitized_container)
                    else:
                        cmd = ['docker', 'logs', '--tail', str(lines)]
                        if follow:
                            cmd.append('--follow')
                        cmd.append(sanitized_container)
                    
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=self.config.get('timeout', 30)
                    )
                    
                    if result.returncode == 0:
                        logs_content = result.stdout
                        method_used = "docker_command"
                    else:
                        error_message = f"Docker command failed: {result.stderr}"
                        
                except Exception as e:
                    error_message = f"Subprocess error: {str(e)}"
            
            # Approach 3: Try to read logs from common log locations
            if not logs_content:
                try:
                    import glob
                    log_paths = [
                        f'/var/log/containers/{sanitized_container}*.log',
                        f'/var/lib/docker/containers/*/{sanitized_container}*/{sanitized_container}*-json.log',
                        f'/var/log/docker/{sanitized_container}.log'
                    ]
                    
                    for pattern in log_paths:
                        log_files = glob.glob(pattern)
                        if log_files:
                            log_file = max(log_files, key=os.path.getctime)
                            with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                                all_lines = f.readlines()
                                logs_content = ''.join(all_lines[-lines:])
                            method_used = "log_file"
                            break
                            
                except Exception as e:
                    error_message = f"Log file reading error: {str(e)}"
            
            # Approach 4: Try to get logs from journalctl
            if not logs_content:
                try:
                    result = subprocess.run(
                        ['journalctl', '-u', f'docker-{sanitized_container}', '--no-pager', '-n', str(lines)],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    
                    if result.returncode == 0:
                        logs_content = result.stdout
                        method_used = "journalctl"
                    else:
                        error_message = f"Journalctl error: {result.stderr}"
                        
                except Exception as e:
                    error_message = f"Journalctl error: {str(e)}"
            
            # Return results
            if logs_content:
                self.log_access(user, sanitized_container, True, method_used)
                return {
                    'success': True,
                    'logs': logs_content,
                    'container': sanitized_container,
                    'lines_returned': len(logs_content.splitlines()),
                    'method': method_used
                }
            else:
                error_msg = f'Could not retrieve logs for container "{sanitized_container}"'
                if error_message:
                    error_msg += f'. Details: {error_message}'
                
                self.log_access(user, sanitized_container, False, method_used, error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'suggestion': 'Try checking if the container is running and accessible, or check Docker permissions.'
                }
                
        except subprocess.TimeoutExpired:
            error_msg = 'Docker logs command timed out'
            self.log_access(user, sanitized_container, False, method_used, error_msg)
            return {
                'success': False,
                'error': error_msg
            }
        except FileNotFoundError:
            error_msg = 'Docker command not found. Make sure Docker is installed and accessible.'
            self.log_access(user, sanitized_container, False, method_used, error_msg)
            return {
                'success': False,
                'error': error_msg
            }
        except Exception as e:
            error_msg = f'Unexpected error: {str(e)}'
            self.log_access(user, sanitized_container, False, method_used, error_msg)
            return {
                'success': False,
                'error': error_msg
            } 