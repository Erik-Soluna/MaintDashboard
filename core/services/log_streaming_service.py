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
        Get list of available containers by scanning log files.
        
        Returns:
            List of container information
        """
        containers = []
        
        # Scan Docker log directories
        for pattern in self.config.get('docker_log_paths', []):
            try:
                log_files = glob.glob(pattern)
                for log_file in log_files:
                    container_info = self._extract_container_info_from_log_file(log_file)
                    if container_info:
                        containers.append(container_info)
            except Exception as e:
                self.logger.warning(f"Error scanning log pattern {pattern}: {e}")
        
        # Add current container info
        hostname = os.environ.get('HOSTNAME', '')
        if hostname:
            containers.insert(0, {
                'name': hostname,
                'id': hostname,
                'image': 'Current Container',
                'status': 'Running',
                'log_file': None,
                'source': 'current'
            })
        
        # Remove duplicates
        seen = set()
        unique_containers = []
        for container in containers:
            if container['name'] not in seen:
                seen.add(container['name'])
                unique_containers.append(container)
        
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
                            except:
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
        Get system logs using journalctl or reading log files.
        
        Args:
            lines: Number of lines to read
            
        Returns:
            System log content
        """
        try:
            # Try journalctl first
            import subprocess
            result = subprocess.run(
                ['journalctl', '--no-pager', '-n', str(lines), '--output=short'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return result.stdout
            
            # Fallback to reading log files
            system_logs = []
            for pattern in self.config.get('system_log_paths', []):
                try:
                    log_files = glob.glob(pattern)
                    for log_file in log_files:
                        if os.path.exists(log_file):
                            with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                                file_lines = f.readlines()
                                system_logs.extend(file_lines[-lines//len(log_files):])
                except Exception as e:
                    self.logger.warning(f"Error reading system log {pattern}: {e}")
            
            return ''.join(system_logs[-lines:]) if system_logs else "No system logs available"
            
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
        if not containers:
            containers = [c['name'] for c in self.get_available_containers()]
        
        aggregated_logs = []
        
        for container_name in containers:
            container_logs = self.get_container_logs(container_name, lines)
            if container_logs:
                aggregated_logs.append(f"\n=== {container_name} ===\n{container_logs}")
        
        return '\n'.join(aggregated_logs) if aggregated_logs else "No logs available"
    
    def get_container_logs(self, container_name: str, lines: int = 100) -> str:
        """
        Get logs for a specific container.
        
        Args:
            container_name: Name of the container
            lines: Number of lines to read
            
        Returns:
            Log content for the container
        """
        containers = self.get_available_containers()
        container = next((c for c in containers if c['name'] == container_name), None)
        
        if not container:
            return f"Container '{container_name}' not found"
        
        log_file = container.get('log_file')
        if log_file:
            # Check if it's a Docker JSON log
            if log_file.endswith('-json.log'):
                return self.read_docker_json_logs(log_file, lines)
            else:
                return self.read_logs_from_file(log_file, lines)
        else:
            # For current container or containers without log files
            return f"Logs for {container_name} are not directly accessible"
    
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