"""
Log Streaming Service
Provides real-time log streaming from multiple sources without Docker commands.
"""

import os
import json
import glob
import time
import threading
import asyncio
import subprocess
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from django.conf import settings
from django.core.cache import cache
from django.contrib.auth.models import User
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class LogStreamingService:
    """
    Service for streaming logs from multiple sources in real-time.
    """
    
    def __init__(self):
        """Initialize the log streaming service."""
        self.config = getattr(settings, 'LOG_STREAMING_CONFIG', {
            'enabled': True,
            'max_lines': 1000,
            'stream_timeout': 300,  # 5 minutes
            'log_sources': ['docker', 'system', 'application'],
            'docker_log_paths': [
                '/var/lib/docker/containers/*/*-json.log',
                '/var/log/containers/*.log',
                '/var/log/docker/*.log'
            ],
            'system_log_paths': [
                '/var/log/syslog',
                '/var/log/messages',
                '/var/log/system.log'
            ]
        })
        self.active_streams = {}
        self.logger = logging.getLogger(__name__)
    
    def get_available_containers(self) -> List[Dict[str, Any]]:
        """
        Get list of available containers from collected log files.
        
        Returns:
            List of container information
        """
        containers = []
        debug_info = []
        debug_info.append("=== CONTAINER DETECTION DEBUG ===")
        
        # First, try to read from collected log files
        logs_dir = '/app/logs'
        debug_info.append(f"Scanning collected logs directory: {logs_dir}")
        
        if os.path.exists(logs_dir):
            try:
                # Read collection summary if available
                summary_file = os.path.join(logs_dir, 'collection_summary.json')
                if os.path.exists(summary_file):
                    with open(summary_file, 'r', encoding='utf-8') as f:
                        summary = json.load(f)
                    
                    debug_info.append(f"Found collection summary: {summary['containers_successful']} successful containers")
                    
                    # Add containers from successful log collections
                    for container_name, result in summary.get('results', {}).items():
                        if result.get('status') == 'success':
                            log_file = result.get('file')
                            if log_file and os.path.exists(log_file):
                                containers.append({
                                    'name': container_name,
                                    'id': container_name,  # Use name as ID for simplicity
                                    'image': 'Unknown',
                                    'status': 'Running',
                                    'log_file': log_file,
                                    'source': 'collected_logs'
                                })
                                debug_info.append(f"Added container from collected logs: {container_name}")
                
                # Also scan for individual log files
                for filename in os.listdir(logs_dir):
                    if filename.endswith('.log') and not filename.startswith('system_'):
                        container_name = filename.replace('.log', '')
                        log_file = os.path.join(logs_dir, filename)
                        
                        # Check if we already have this container
                        if not any(c['name'] == container_name for c in containers):
                            containers.append({
                                'name': container_name,
                                'id': container_name,
                                'image': 'Unknown',
                                'status': 'Running',
                                'log_file': log_file,
                                'source': 'log_file'
                            })
                            debug_info.append(f"Added container from log file: {container_name}")
                
            except Exception as e:
                debug_info.append(f"Error reading collected logs: {e}")
                self.logger.warning(f"Error reading collected logs: {e}")
        else:
            debug_info.append("Collected logs directory does not exist")
        
        # Since Docker CLI is not accessible, use alternative sources
        debug_info.append("Docker CLI not accessible, using alternative log sources...")
        
        # Add current container with accessible log sources
        hostname = os.environ.get('HOSTNAME', '')
        if hostname:
            # Add current container with accessible log files
            current_container = {
                'name': hostname,
                'id': hostname,
                'image': 'Current Container',
                'status': 'Running',
                'log_file': '/proc/1/fd/1',  # Container stdout
                'source': 'current'
            }
            containers.append(current_container)
            debug_info.append(f"Added current container with stdout: {hostname}")
            
            # Also add stderr
            stderr_container = {
                'name': f"{hostname}_stderr",
                'id': hostname,
                'image': 'Current Container (stderr)',
                'status': 'Running',
                'log_file': '/proc/1/fd/2',  # Container stderr
                'source': 'current_stderr'
            }
            containers.append(stderr_container)
            debug_info.append(f"Added current container stderr: {hostname}_stderr")
        
        # Add system log sources
        system_logs = [
            ('/var/log/syslog', 'system_syslog'),
            ('/var/log/messages', 'system_messages'),
            ('/var/log/dmesg', 'system_dmesg'),
            ('/proc/loadavg', 'system_loadavg'),
            ('/proc/meminfo', 'system_meminfo'),
            ('/proc/cpuinfo', 'system_cpuinfo'),
        ]
        
        for log_path, name in system_logs:
            if os.path.exists(log_path):
                containers.append({
                    'name': name,
                    'id': name,
                    'image': 'System Log',
                    'status': 'Available',
                    'log_file': log_path,
                    'source': 'system'
                })
                debug_info.append(f"Added system log: {name} -> {log_path}")
        
        # Add application logs if available
        app_logs = [
            ('/app/debug.log', 'app_debug'),
            ('/app/logs/app.log', 'app_logs'),
            ('/var/log/nginx/access.log', 'nginx_access'),
            ('/var/log/nginx/error.log', 'nginx_error'),
        ]
        
        for log_path, name in app_logs:
            if os.path.exists(log_path):
                containers.append({
                    'name': name,
                    'id': name,
                    'image': 'Application Log',
                    'status': 'Available',
                    'log_file': log_path,
                    'source': 'application'
                })
                debug_info.append(f"Added application log: {name} -> {log_path}")
        
        # Add current container info if not already present
        hostname = os.environ.get('HOSTNAME', '')
        debug_info.append(f"\n=== HOSTNAME INFO ===")
        debug_info.append(f"Hostname: {hostname}")
        if hostname and not any(c['name'] == hostname for c in containers):
            current_container = {
                'name': hostname,
                'id': hostname,
                'image': 'Current Container',
                'status': 'Running',
                'log_file': None,
                'source': 'current'
            }
            containers.insert(0, current_container)
            debug_info.append(f"Added current container: {current_container}")
        
        # Remove duplicates
        debug_info.append(f"\n=== DEDUPLICATION ===")
        debug_info.append(f"Before deduplication: {len(containers)} containers")
        seen = set()
        unique_containers = []
        for container in containers:
            if container['name'] in seen:
                debug_info.append(f"Skipping duplicate: {container['name']}")
                continue
            
            seen.add(container['name'])
            unique_containers.append(container)
            debug_info.append(f"Added unique container: {container}")
        
        debug_info.append(f"After deduplication: {len(unique_containers)} containers")
        debug_info.append("=== END CONTAINER DETECTION DEBUG ===\n")
        
        # Log debug info
        self.logger.info("\n".join(debug_info))
        
        return unique_containers
    
    def _extract_container_info_from_log_file(self, log_file: str) -> Optional[Dict[str, Any]]:
        """
        Extract container information from a log file path.
        
        Args:
            log_file: Path to the log file
            
        Returns:
            Container information or None
        """
        try:
            # Extract container ID from path
            # Example: /var/lib/docker/containers/abc123/abc123-json.log
            path_parts = log_file.split('/')
            
            if 'containers' in path_parts:
                container_idx = path_parts.index('containers')
                if container_idx + 1 < len(path_parts):
                    container_id = path_parts[container_idx + 1]
                    return {
                        'name': container_id[:12],  # Short ID
                        'id': container_id,
                        'image': 'Unknown',
                        'status': 'Running',
                        'log_file': log_file,
                        'source': 'docker'
                    }
            
            # Extract from filename
            filename = os.path.basename(log_file)
            if filename.endswith('.log'):
                container_name = filename.replace('.log', '')
                return {
                    'name': container_name,
                    'id': container_name,
                    'image': 'Unknown',
                    'status': 'Running',
                    'log_file': log_file,
                    'source': 'file'
                }
                
        except Exception as e:
            self.logger.warning(f"Error extracting container info from {log_file}: {e}")
        
        return None
    
    def read_logs_from_file(self, log_file: str, lines: int = 100, follow: bool = False) -> str:
        """
        Read logs from a file with optional following.
        
        Args:
            log_file: Path to the log file
            lines: Number of lines to read
            follow: Whether to follow the file
            
        Returns:
            Log content as string
        """
        try:
            if not os.path.exists(log_file):
                return f"Log file not found: {log_file}"
            
            # Read the file
            with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                if follow:
                    # For following, read all lines and return
                    all_lines = f.readlines()
                    return ''.join(all_lines[-lines:]) if lines > 0 else ''.join(all_lines)
                else:
                    # For non-following, read last N lines
                    all_lines = f.readlines()
                    return ''.join(all_lines[-lines:]) if lines > 0 else ''.join(all_lines)
                    
        except Exception as e:
            return f"Error reading log file {log_file}: {str(e)}"
    
    def read_docker_json_logs(self, log_file: str, lines: int = 100) -> str:
        """
        Read and parse Docker JSON log format.
        
        Args:
            log_file: Path to Docker JSON log file
            lines: Number of lines to read
            
        Returns:
            Formatted log content
        """
        try:
            if not os.path.exists(log_file):
                return f"Log file not found: {log_file}"
            
            logs = []
            with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                file_lines = f.readlines()
                
                # Parse JSON logs (Docker format: {"log":"message","stream":"stdout","time":"timestamp"})
                for line in file_lines[-lines:] if lines > 0 else file_lines:
                    try:
                        log_entry = json.loads(line.strip())
                        timestamp = log_entry.get('time', '')
                        stream = log_entry.get('stream', 'stdout')
                        message = log_entry.get('log', '')
                        
                        # Format timestamp
                        if timestamp:
                            try:
                                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                                formatted_time = dt.strftime('%Y-%m-%d %H:%M:%S')
                            except (ValueError, TypeError):
                                formatted_time = timestamp
                        else:
                            formatted_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        
                        logs.append(f"[{formatted_time}] [{stream.upper()}] {message}")
                    except json.JSONDecodeError:
                        # Fallback to raw line if not JSON
                        logs.append(line.strip())
            
            return '\n'.join(logs)
            
        except Exception as e:
            return f"Error reading Docker JSON logs from {log_file}: {str(e)}"
    
    def get_system_logs(self, lines: int = 100) -> str:
        """
        Get system logs from collected log files.
        
        Args:
            lines: Number of lines to read
            
        Returns:
            System log content
        """
        try:
            system_logs = []
            logs_dir = '/app/logs'
            
            # First, try to read from collected system logs
            if os.path.exists(logs_dir):
                system_log_files = []
                
                # Look for system log files
                for filename in os.listdir(logs_dir):
                    if filename.startswith('system_') and filename.endswith('.log'):
                        system_log_files.append(os.path.join(logs_dir, filename))
                
                # Also check for system logs summary
                summary_file = os.path.join(logs_dir, 'system_logs_summary.json')
                if os.path.exists(summary_file):
                    try:
                        with open(summary_file, 'r', encoding='utf-8') as f:
                            summary = json.load(f)
                        
                        # Add successful system logs
                        for log_path, result in summary.get('results', {}).items():
                            if result.get('status') == 'success':
                                log_file = result.get('file')
                                if log_file and os.path.exists(log_file):
                                    system_log_files.append(log_file)
                    except Exception as e:
                        self.logger.warning(f"Error reading system logs summary: {e}")
                
                # Read from collected system log files
                for log_file in system_log_files:
                    try:
                        with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                            all_lines = f.readlines()
                        
                        # Skip header lines (lines starting with #)
                        content_lines = [line for line in all_lines if not line.startswith('#')]
                        
                        # Take last lines from this file
                        lines_per_file = max(1, lines // len(system_log_files)) if system_log_files else lines
                        system_logs.extend(content_lines[-lines_per_file:])
                        
                    except Exception as e:
                        self.logger.warning(f"Error reading system log file {log_file}: {e}")
            
            # Fallback: Try original system log paths
            if not system_logs:
                log_paths = [
                    '/var/log/syslog',
                    '/var/log/messages',
                    '/var/log/dmesg',
                    '/proc/1/fd/1',  # Docker container stdout
                    '/proc/1/fd/2',  # Docker container stderr
                ]
                
                # Add any custom paths from config
                log_paths.extend(self.config.get('system_log_paths', []))
                
                for log_path in log_paths:
                    try:
                        if os.path.exists(log_path):
                            with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                                file_lines = f.readlines()
                                # Take last lines from this file
                                lines_per_file = max(1, lines // len(log_paths))
                                system_logs.extend(file_lines[-lines_per_file:])
                    except Exception as e:
                        self.logger.warning(f"Error reading system log {log_path}: {e}")
            
            # If still no system logs found, try to get container logs
            if not system_logs:
                containers = self.get_available_containers()
                for container in containers[:3]:  # Limit to first 3 containers
                    if container.get('log_file') and os.path.exists(container['log_file']):
                        try:
                            with open(container['log_file'], 'r', encoding='utf-8', errors='replace') as f:
                                file_lines = f.readlines()
                                lines_per_container = max(1, lines // 3)
                                system_logs.extend([f"[{container['name']}] {line}" for line in file_lines[-lines_per_container:]])
                        except Exception as e:
                            self.logger.warning(f"Error reading container log {container['name']}: {e}")
            
            if system_logs:
                return ''.join(system_logs[-lines:])
            else:
                return "No system logs available. This is normal in Docker containers.\n\nAvailable log sources:\n" + \
                       "\n".join([f"- {c['name']}: {c.get('log_file', 'No log file')}" 
                                 for c in self.get_available_containers()[:5]])
            
        except Exception as e:
            return f"Error getting system logs: {str(e)}"
    
    def get_aggregated_logs(self, containers: List[str] = None, lines: int = 100) -> str:
        """
        Get aggregated logs from multiple containers.
        
        Args:
            containers: List of container names to include
            lines: Number of lines per container
            
        Returns:
            Aggregated log content
        """
        debug_info = []
        debug_info.append("=== AGGREGATED LOGS DEBUG ===")
        debug_info.append(f"Input containers: {containers}")
        debug_info.append(f"Lines requested: {lines}")
        
        if not containers:
            available_containers = self.get_available_containers()
            containers = [c['name'] for c in available_containers]
            debug_info.append(f"No containers specified, using all available: {containers}")
        else:
            debug_info.append(f"Using specified containers: {containers}")
        
        aggregated_logs = []
        containers_processed = 0
        containers_with_logs = 0
        
        for container_name in containers:
            debug_info.append(f"\nProcessing container: {container_name}")
            containers_processed += 1
            
            try:
                container_logs = self.get_container_logs(container_name, lines)
                debug_info.append(f"Logs for {container_name}: {len(container_logs)} characters")
                debug_info.append(f"Logs preview: {container_logs[:100]}...")
                
                if container_logs and container_logs.strip():
                    aggregated_logs.append(f"\n=== {container_name} ===\n{container_logs}")
                    containers_with_logs += 1
                    debug_info.append(f"✓ Added logs for {container_name}")
                else:
                    debug_info.append(f"✗ No logs for {container_name}")
            except Exception as e:
                debug_info.append(f"✗ Error getting logs for {container_name}: {e}")
        
        debug_info.append(f"\n=== SUMMARY ===")
        debug_info.append(f"Containers processed: {containers_processed}")
        debug_info.append(f"Containers with logs: {containers_with_logs}")
        total_content = '\n'.join(aggregated_logs)
        debug_info.append(f"Total log content length: {len(total_content)}")
        debug_info.append("=== END AGGREGATED LOGS DEBUG ===\n")
        
        # Log debug info
        self.logger.info("\n".join(debug_info))
        
        result = '\n'.join(aggregated_logs) if aggregated_logs else "No logs available"
        return result
    
    def get_container_logs(self, container_name: str, lines: int = 100) -> str:
        """
        Get logs for a specific container.
        
        Args:
            container_name: Name of the container
            lines: Number of lines to read
            
        Returns:
            Log content for the container
        """
        debug_info = []
        debug_info.append(f"=== CONTAINER LOGS DEBUG for {container_name} ===")
        debug_info.append(f"Lines requested: {lines}")
        
        containers = self.get_available_containers()
        debug_info.append(f"Available containers: {[c['name'] for c in containers]}")
        
        container = next((c for c in containers if c['name'] == container_name), None)
        
        if not container:
            debug_info.append(f"✗ Container '{container_name}' not found in available containers")
            self.logger.warning(f"Container '{container_name}' not found")
            return f"Container '{container_name}' not found"
        
        debug_info.append(f"✓ Found container: {container}")
        
        log_file = container.get('log_file')
        debug_info.append(f"Log file: {log_file}")
        
        if log_file and os.path.exists(log_file):
            debug_info.append(f"✓ Log file exists: {log_file}")
            
            # Read from collected log file
            try:
                with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                    all_lines = f.readlines()
                
                # Skip header lines (lines starting with #)
                content_lines = [line for line in all_lines if not line.startswith('#')]
                
                # Take the last N lines
                if lines > 0:
                    content_lines = content_lines[-lines:]
                
                result = ''.join(content_lines)
                debug_info.append(f"Collected log result length: {len(result)}")
                debug_info.append(f"Collected log preview: {result[:100]}...")
                return result
            except Exception as e:
                debug_info.append(f"Error reading collected log file: {e}")
                # Fall back to original methods
                if log_file.endswith('-json.log'):
                    debug_info.append("Falling back to Docker JSON log reader")
                    result = self.read_docker_json_logs(log_file, lines)
                    debug_info.append(f"JSON log result length: {len(result)}")
                    return result
                else:
                    debug_info.append("Falling back to regular log file reader")
                    result = self.read_logs_from_file(log_file, lines)
                    debug_info.append(f"Regular log result length: {len(result)}")
                    return result
        else:
            debug_info.append(f"✗ Log file not accessible: {log_file}")
            debug_info.append("Attempting Docker CLI fallback...")
            
            # Try to get logs directly from Docker CLI as fallback
            try:
                debug_info.append(f"Running: docker logs --tail {lines} {container_name}")
                result = subprocess.run(
                    ['docker', 'logs', '--tail', str(lines), container_name],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                debug_info.append(f"Docker logs return code: {result.returncode}")
                debug_info.append(f"Docker logs stdout length: {len(result.stdout)}")
                debug_info.append(f"Docker logs stderr: {result.stderr}")
                
                if result.returncode == 0:
                    debug_info.append(f"✓ Docker CLI logs successful: {len(result.stdout)} characters")
                    debug_info.append(f"Logs preview: {result.stdout[:100]}...")
                    return result.stdout
                else:
                    error_msg = f"Error getting logs for {container_name}: {result.stderr}"
                    debug_info.append(f"✗ Docker CLI failed: {error_msg}")
                    return error_msg
                    
            except subprocess.TimeoutExpired:
                error_msg = f"Timeout getting logs for {container_name}"
                debug_info.append(f"✗ Docker CLI timeout: {error_msg}")
                return error_msg
            except FileNotFoundError:
                error_msg = f"Docker CLI not available for {container_name}"
                debug_info.append(f"✗ Docker CLI not found: {error_msg}")
                return error_msg
            except Exception as e:
                error_msg = f"Error getting logs for {container_name}: {str(e)}"
                debug_info.append(f"✗ Docker CLI exception: {error_msg}")
                return error_msg
        
        debug_info.append("=== END CONTAINER LOGS DEBUG ===\n")
        self.logger.info("\n".join(debug_info))
    
    def start_log_stream(self, user: User, containers: List[str] = None, 
                        callback: Callable = None) -> str:
        """
        Start a real-time log stream.
        
        Args:
            user: Django user
            containers: List of containers to stream
            callback: Callback function for log updates
            
        Returns:
            Stream ID
        """
        import uuid
        stream_id = str(uuid.uuid4())
        
        # Store stream info
        self.active_streams[stream_id] = {
            'user_id': user.id,
            'containers': containers or [],
            'started_at': timezone.now(),
            'callback': callback,
            'active': True
        }
        
        # Start streaming in background thread
        thread = threading.Thread(
            target=self._stream_logs,
            args=(stream_id, containers or []),
            daemon=True
        )
        thread.start()
        
        return stream_id
    
    def _stream_logs(self, stream_id: str, containers: List[str]):
        """
        Background thread for streaming logs.
        
        Args:
            stream_id: Unique stream identifier
            containers: List of containers to monitor
        """
        try:
            stream_info = self.active_streams.get(stream_id)
            if not stream_info:
                return
            
            # Track file positions
            file_positions = {}
            
            while stream_info.get('active', False):
                for container_name in containers:
                    container = next(
                        (c for c in self.get_available_containers() if c['name'] == container_name), 
                        None
                    )
                    
                    if container and container.get('log_file'):
                        log_file = container['log_file']
                        current_pos = file_positions.get(log_file, 0)
                        
                        try:
                            with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                                f.seek(current_pos)
                                new_lines = f.readlines()
                                if new_lines:
                                    file_positions[log_file] = f.tell()
                                    
                                    # Process new lines
                                    for line in new_lines:
                                        if stream_info.get('callback'):
                                            stream_info['callback'](container_name, line.strip())
                        except Exception as e:
                            self.logger.warning(f"Error streaming logs for {container_name}: {e}")
                
                time.sleep(1)  # Check every second
                
        except Exception as e:
            self.logger.error(f"Error in log stream {stream_id}: {e}")
        finally:
            # Clean up
            if stream_id in self.active_streams:
                del self.active_streams[stream_id]
    
    def stop_log_stream(self, stream_id: str):
        """
        Stop a log stream.
        
        Args:
            stream_id: Stream ID to stop
        """
        if stream_id in self.active_streams:
            self.active_streams[stream_id]['active'] = False
    
    def get_stream_status(self, stream_id: str) -> Dict[str, Any]:
        """
        Get status of a log stream.
        
        Args:
            stream_id: Stream ID
            
        Returns:
            Stream status information
        """
        stream_info = self.active_streams.get(stream_id)
        if not stream_info:
            return {'active': False, 'error': 'Stream not found'}
        
        return {
            'active': stream_info.get('active', False),
            'user_id': stream_info.get('user_id'),
            'containers': stream_info.get('containers', []),
            'started_at': stream_info.get('started_at').isoformat() if stream_info.get('started_at') else None,
            'duration': (timezone.now() - stream_info['started_at']).total_seconds() if stream_info.get('started_at') else 0
        } 