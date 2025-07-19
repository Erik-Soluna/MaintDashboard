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
        Get list of available containers by scanning log files and Docker API.
        
        Returns:
            List of container information
        """
        containers = []
        debug_info = []
        debug_info.append("=== CONTAINER DETECTION DEBUG ===")
        
        # Try to get containers from Docker API first
        try:
            from .docker_logs_service import DockerLogsService
            docker_service = DockerLogsService()
            debug_info.append("✓ DockerLogsService imported successfully")
            
            # Try to get containers using subprocess as fallback
            try:
                debug_info.append("Attempting docker ps command...")
                result = subprocess.run(
                    ['docker', 'ps', '--format', 'table {{.Names}}\t{{.ID}}\t{{.Image}}\t{{.Status}}'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                debug_info.append(f"Docker ps return code: {result.returncode}")
                debug_info.append(f"Docker ps stdout: {result.stdout[:200]}...")
                debug_info.append(f"Docker ps stderr: {result.stderr[:200]}...")
                
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')[1:]  # Skip header
                    debug_info.append(f"Found {len(lines)} container lines")
                    for i, line in enumerate(lines):
                        if line.strip():
                            parts = line.split('\t')
                            debug_info.append(f"Line {i}: {line}")
                            if len(parts) >= 4:
                                name, container_id, image, status = parts[:4]
                                container_info = {
                                    'name': name.strip(),
                                    'id': container_id.strip(),
                                    'image': image.strip(),
                                    'status': status.strip(),
                                    'log_file': None,  # Will be found by scanning
                                    'source': 'docker_cli'
                                }
                                containers.append(container_info)
                                debug_info.append(f"Added container: {container_info}")
                            else:
                                debug_info.append(f"Invalid line format: {parts}")
                else:
                    debug_info.append(f"Docker ps failed with return code {result.returncode}")
            except Exception as e:
                debug_info.append(f"Error getting containers from Docker CLI: {e}")
                self.logger.warning(f"Error getting containers from Docker CLI: {e}")
                
        except Exception as e:
            debug_info.append(f"Error importing DockerLogsService: {e}")
            self.logger.warning(f"Error getting containers from Docker API: {e}")
        
        # Scan Docker log directories for log files
        debug_info.append("\n=== LOG FILE SCANNING ===")
        for pattern in self.config.get('docker_log_paths', []):
            try:
                debug_info.append(f"Scanning pattern: {pattern}")
                log_files = glob.glob(pattern)
                debug_info.append(f"Found {len(log_files)} log files for pattern {pattern}")
                for log_file in log_files:
                    debug_info.append(f"Processing log file: {log_file}")
                    container_info = self._extract_container_info_from_log_file(log_file)
                    if container_info:
                        debug_info.append(f"Extracted container info: {container_info}")
                        # Try to match with existing containers by ID
                        container_id = container_info['id']
                        matched = False
                        for existing_container in containers:
                            if existing_container['id'].startswith(container_id) or container_id.startswith(existing_container['id']):
                                existing_container['log_file'] = log_file
                                debug_info.append(f"Matched {container_id} with existing container {existing_container['name']}")
                                matched = True
                                break
                        if not matched:
                            # Add new container if not found
                            containers.append(container_info)
                            debug_info.append(f"Added new container from log file: {container_info}")
                    else:
                        debug_info.append(f"No container info extracted from {log_file}")
            except Exception as e:
                debug_info.append(f"Error scanning log pattern {pattern}: {e}")
                self.logger.warning(f"Error scanning log pattern {pattern}: {e}")
        
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
        else:
            debug_info.append(f"Current container already exists or hostname not found")
        
        # Remove duplicates and ensure all containers have readable names
        debug_info.append(f"\n=== DEDUPLICATION ===")
        debug_info.append(f"Before deduplication: {len(containers)} containers")
        seen = set()
        unique_containers = []
        for container in containers:
            # Ensure container has a readable name
            if container['name'] in seen:
                debug_info.append(f"Skipping duplicate: {container['name']}")
                continue
                
            # If name is just an ID, try to make it more readable
            if len(container['name']) == 12 and container['name'].isalnum():
                # This looks like a short Docker ID, try to find a better name
                old_name = container['name']
                container['name'] = f"container-{container['name'][:8]}"
                debug_info.append(f"Renamed container from {old_name} to {container['name']}")
            
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
        Get system logs by reading log files directly.
        Note: journalctl is not available in Docker containers.
        
        Args:
            lines: Number of lines to read
            
        Returns:
            System log content
        """
        try:
            system_logs = []
            
            # Common system log paths in Docker containers
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
            
            # If no system logs found, try to get container logs
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
            # Check if it's a Docker JSON log
            if log_file.endswith('-json.log'):
                debug_info.append("Using Docker JSON log reader")
                result = self.read_docker_json_logs(log_file, lines)
                debug_info.append(f"JSON log result length: {len(result)}")
                debug_info.append(f"JSON log preview: {result[:100]}...")
                return result
            else:
                debug_info.append("Using regular log file reader")
                result = self.read_logs_from_file(log_file, lines)
                debug_info.append(f"Regular log result length: {len(result)}")
                debug_info.append(f"Regular log preview: {result[:100]}...")
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