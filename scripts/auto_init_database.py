#!/usr/bin/env python3
"""
Auto Database Initialization Script for Docker Environment
This script automates database initialization when it fails in Docker containers.

Features:
- Automatic database connection retries
- Database creation if missing
- Container restart automation
- Comprehensive logging and monitoring
- Error recovery mechanisms
"""

import subprocess
import sys
import time
import os
import signal
import logging
from datetime import datetime
from typing import Optional, Tuple, Dict, Any
import json

# Configuration
CONFIG = {
    'MAX_RETRIES': 30,
    'RETRY_DELAY': 5,
    'DB_READY_TIMEOUT': 300,
    'CONTAINER_RESTART_DELAY': 10,
    'LOG_LEVEL': 'INFO',
    'DOCKER_COMPOSE_FILE': 'docker-compose.yml'
}

# Container names (update these to match your setup)
CONTAINERS = {
    'db': 'maintenance_db',
    'web': 'maintenance_web',
    'redis': 'maintenance_redis'
}

# Database configuration
DB_CONFIG = {
    'name': 'maintenance_dashboard',
    'user': 'postgres',
    'password': 'postgres',
    'host': 'localhost',
    'port': 5432
}

class Color:
    """ANSI color codes for console output."""
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    PURPLE = '\033[0;35m'
    CYAN = '\033[0;36m'
    WHITE = '\033[0;37m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

class AutoInitDB:
    """Automated database initialization manager."""
    
    def __init__(self, config_override: Optional[Dict[str, Any]] = None):
        """Initialize the auto database initialization manager."""
        self.config = CONFIG.copy()
        if config_override:
            self.config.update(config_override)
        
        self.setup_logging()
        self.start_time = datetime.now()
        self.logger.info(f"🚀 AutoInitDB started at {self.start_time}")
        
        # Handle interruption gracefully
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def setup_logging(self):
        """Setup logging configuration."""
        log_format = '%(asctime)s - %(levelname)s - %(message)s'
        logging.basicConfig(
            level=getattr(logging, self.config['LOG_LEVEL']),
            format=log_format,
            handlers=[
                logging.FileHandler('auto_init_db.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def _signal_handler(self, signum, frame):
        """Handle interruption signals."""
        self.logger.info("🛑 Received interruption signal, shutting down gracefully...")
        sys.exit(0)
    
    def run_command(self, command: str, capture_output: bool = True, timeout: int = 30) -> Tuple[bool, str, str]:
        """Execute a command and return the result."""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=capture_output,
                text=True,
                timeout=timeout
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", f"Command timed out after {timeout} seconds"
        except Exception as e:
            return False, "", str(e)
    
    def print_status(self, message: str, color: str = Color.BLUE):
        """Print colored status message."""
        print(f"{color}[INFO]{Color.RESET} {message}")
        self.logger.info(message)
    
    def print_success(self, message: str):
        """Print success message."""
        print(f"{Color.GREEN}[SUCCESS]{Color.RESET} {message}")
        self.logger.info(message)
    
    def print_warning(self, message: str):
        """Print warning message."""
        print(f"{Color.YELLOW}[WARNING]{Color.RESET} {message}")
        self.logger.warning(message)
    
    def print_error(self, message: str):
        """Print error message."""
        print(f"{Color.RED}[ERROR]{Color.RESET} {message}")
        self.logger.error(message)
    
    def check_docker_environment(self) -> bool:
        """Check if Docker environment is available."""
        self.print_status("Checking Docker environment...")
        
        success, stdout, stderr = self.run_command("docker --version")
        if not success:
            self.print_error("Docker is not installed or not accessible")
            return False
        
        success, stdout, stderr = self.run_command("docker-compose --version")
        if not success:
            self.print_error("Docker Compose is not installed or not accessible")
            return False
        
        self.print_success("Docker environment is available")
        return True
    
    def get_container_name(self, service: str) -> Optional[str]:
        """Get the actual container name for a service."""
        # Try to get container name from docker-compose
        cmd = f"docker-compose -f {self.config['DOCKER_COMPOSE_FILE']} ps -q {service}"
        success, stdout, stderr = self.run_command(cmd)
        
        if success and stdout.strip():
            container_id = stdout.strip()
            # Get container name from ID
            cmd = f"docker inspect --format='{{{{.Name}}}}' {container_id}"
            success, stdout, stderr = self.run_command(cmd)
            if success:
                return stdout.strip().lstrip('/')
        
        # Fallback to predefined names
        return CONTAINERS.get(service)
    
    def check_container_status(self, service: str) -> Dict[str, Any]:
        """Check the status of a Docker container."""
        container_name = self.get_container_name(service)
        if not container_name:
            return {'exists': False, 'running': False, 'healthy': False}
        
        # Check if container exists
        cmd = f"docker ps -a --filter name={container_name} --format '{{{{.Status}}}}'"
        success, stdout, stderr = self.run_command(cmd)
        
        if not success or not stdout.strip():
            return {'exists': False, 'running': False, 'healthy': False}
        
        status = stdout.strip()
        running = 'Up' in status
        healthy = 'healthy' in status or 'starting' in status
        
        return {
            'exists': True,
            'running': running,
            'healthy': healthy,
            'status': status,
            'name': container_name
        }
    
    def wait_for_container_health(self, service: str, timeout: int = 300) -> bool:
        """Wait for a container to become healthy."""
        self.print_status(f"Waiting for {service} container to be healthy...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            status = self.check_container_status(service)
            
            if status['exists'] and status['running'] and status['healthy']:
                self.print_success(f"{service} container is healthy")
                return True
            
            if not status['exists']:
                self.print_error(f"{service} container does not exist")
                return False
            
            if not status['running']:
                self.print_warning(f"{service} container is not running")
                time.sleep(5)
                continue
            
            self.print_status(f"Waiting for {service} container... ({status.get('status', 'unknown')})")
            time.sleep(5)
        
        self.print_error(f"Timeout waiting for {service} container to be healthy")
        return False
    
    def check_database_connection(self) -> bool:
        """Check if database connection is available."""
        container_name = self.get_container_name('db')
        if not container_name:
            return False
        
        cmd = f"docker exec {container_name} pg_isready -U {DB_CONFIG['user']} -d {DB_CONFIG['name']}"
        success, stdout, stderr = self.run_command(cmd)
        
        return success
    
    def create_database_if_missing(self) -> bool:
        """Create database if it doesn't exist."""
        container_name = self.get_container_name('db')
        if not container_name:
            self.print_error("Database container not found")
            return False
        
        # Check if database exists
        cmd = f"docker exec {container_name} psql -U {DB_CONFIG['user']} -t -c \"SELECT 1 FROM pg_database WHERE datname='{DB_CONFIG['name']}'\""
        success, stdout, stderr = self.run_command(cmd)
        
        if success and stdout.strip():
            self.print_success(f"Database '{DB_CONFIG['name']}' already exists")
            return True
        
        # Create database
        self.print_status(f"Creating database '{DB_CONFIG['name']}'...")
        cmd = f"docker exec {container_name} psql -U {DB_CONFIG['user']} -c \"CREATE DATABASE {DB_CONFIG['name']}\""
        success, stdout, stderr = self.run_command(cmd)
        
        if success:
            self.print_success(f"Database '{DB_CONFIG['name']}' created successfully")
            return True
        else:
            self.print_error(f"Failed to create database: {stderr}")
            return False
    
    def restart_container(self, service: str) -> bool:
        """Restart a Docker container."""
        self.print_status(f"Restarting {service} container...")
        
        cmd = f"docker-compose -f {self.config['DOCKER_COMPOSE_FILE']} restart {service}"
        success, stdout, stderr = self.run_command(cmd, timeout=60)
        
        if success:
            self.print_success(f"{service} container restarted successfully")
            time.sleep(self.config['CONTAINER_RESTART_DELAY'])
            return True
        else:
            self.print_error(f"Failed to restart {service} container: {stderr}")
            return False
    
    def run_database_initialization(self) -> bool:
        """Run the database initialization command."""
        container_name = self.get_container_name('web')
        if not container_name:
            self.print_error("Web container not found")
            return False
        
        self.print_status("Running database initialization...")
        
        # Use environment variables from the container
        cmd = f"docker exec {container_name} python manage.py init_database"
        success, stdout, stderr = self.run_command(cmd, timeout=120)
        
        if success:
            self.print_success("Database initialization completed successfully")
            print(stdout)
            return True
        else:
            self.print_error(f"Database initialization failed: {stderr}")
            return False
    
    def monitor_and_recover(self) -> bool:
        """Monitor containers and recover from failures."""
        self.print_status("Starting monitoring and recovery process...")
        
        retry_count = 0
        max_retries = self.config['MAX_RETRIES']
        
        while retry_count < max_retries:
            self.print_status(f"Attempt {retry_count + 1}/{max_retries}")
            
            # Check all containers
            db_status = self.check_container_status('db')
            web_status = self.check_container_status('web')
            redis_status = self.check_container_status('redis')
            
            # Print status
            self.print_status(f"Database: {db_status.get('status', 'unknown')}")
            self.print_status(f"Web: {web_status.get('status', 'unknown')}")
            self.print_status(f"Redis: {redis_status.get('status', 'unknown')}")
            
            # Wait for database to be healthy
            if not self.wait_for_container_health('db', timeout=60):
                self.print_warning("Database container is not healthy, restarting...")
                self.restart_container('db')
                retry_count += 1
                continue
            
            # Create database if missing
            if not self.create_database_if_missing():
                self.print_warning("Database creation failed, retrying...")
                retry_count += 1
                time.sleep(self.config['RETRY_DELAY'])
                continue
            
            # Wait for web container to be healthy
            if not self.wait_for_container_health('web', timeout=60):
                self.print_warning("Web container is not healthy, restarting...")
                self.restart_container('web')
                retry_count += 1
                continue
            
            # Try to run database initialization
            if self.run_database_initialization():
                self.print_success("🎉 Database initialization successful!")
                return True
            else:
                self.print_warning("Database initialization failed, retrying...")
                
                # Try restarting web container
                if retry_count < max_retries - 1:
                    self.restart_container('web')
                
                retry_count += 1
                time.sleep(self.config['RETRY_DELAY'])
        
        self.print_error("Maximum retry attempts reached, initialization failed")
        return False
    
    def create_monitoring_script(self):
        """Create a monitoring script for continuous operation."""
        script_content = """#!/bin/bash
# Continuous monitoring script for database initialization
# This script monitors the containers and automatically fixes issues

while true; do
    echo "🔍 Checking container health..."
    
    # Check if web container is running
    if ! docker ps --filter name=maintenance_web --format "table {{.Names}}" | grep -q maintenance_web; then
        echo "⚠️  Web container not running, starting auto-recovery..."
        python3 auto_init_database.py
    fi
    
    # Check database connection
    if ! docker exec maintenance_db pg_isready -U postgres -d maintenance_dashboard > /dev/null 2>&1; then
        echo "⚠️  Database connection failed, starting auto-recovery..."
        python3 auto_init_database.py
    fi
    
    # Wait before next check
    sleep 30
done
"""
        
        with open('monitor_database.sh', 'w') as f:
            f.write(script_content)
        
        # Make it executable
        os.chmod('monitor_database.sh', 0o755)
        self.print_success("Monitoring script created: monitor_database.sh")
    
    def generate_status_report(self):
        """Generate a comprehensive status report."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'runtime': str(datetime.now() - self.start_time),
            'containers': {},
            'database': {},
            'configuration': self.config
        }
        
        # Check container statuses
        for service in ['db', 'web', 'redis']:
            report['containers'][service] = self.check_container_status(service)
        
        # Check database
        report['database']['connection'] = self.check_database_connection()
        
        # Save report
        with open('auto_init_status.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        self.print_success("Status report generated: auto_init_status.json")
        return report
    
    def run(self):
        """Main execution method."""
        try:
            self.print_status("🚀 Starting automated database initialization...")
            
            # Check Docker environment
            if not self.check_docker_environment():
                return False
            
            # Run monitoring and recovery
            success = self.monitor_and_recover()
            
            # Generate status report
            self.generate_status_report()
            
            # Create monitoring script
            self.create_monitoring_script()
            
            if success:
                self.print_success("✅ Automated database initialization completed successfully!")
                elapsed = datetime.now() - self.start_time
                self.print_status(f"Total runtime: {elapsed}")
                return True
            else:
                self.print_error("❌ Automated database initialization failed!")
                return False
                
        except Exception as e:
            self.print_error(f"Unexpected error: {str(e)}")
            return False

def main():
    """Main function."""
    print(f"{Color.CYAN}{Color.BOLD}")
    print("=" * 70)
    print("  AUTO DATABASE INITIALIZATION FOR DOCKER")
    print("  Automated recovery and monitoring system")
    print("=" * 70)
    print(f"{Color.RESET}")
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Automated database initialization for Docker')
    parser.add_argument('--max-retries', type=int, default=30, help='Maximum retry attempts')
    parser.add_argument('--retry-delay', type=int, default=5, help='Delay between retries (seconds)')
    parser.add_argument('--compose-file', default='docker-compose.yml', help='Docker Compose file')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
    
    args = parser.parse_args()
    
    # Override configuration
    config_override = {
        'MAX_RETRIES': args.max_retries,
        'RETRY_DELAY': args.retry_delay,
        'DOCKER_COMPOSE_FILE': args.compose_file,
        'LOG_LEVEL': args.log_level
    }
    
    # Create and run the auto-init manager
    auto_init = AutoInitDB(config_override)
    success = auto_init.run()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()