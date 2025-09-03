#!/usr/bin/env python3
"""
Configuration Manager for Maintenance Dashboard
This script helps manage environment configurations and settings.
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional
import argparse


class ConfigManager:
    """Manages configuration for the Maintenance Dashboard application."""
    
    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or Path(__file__).parent.parent
        self.env_file = self.base_dir / '.env'
        self.env_example = self.base_dir / 'env.example'
        
    def validate_config(self) -> Dict[str, Any]:
        """Validate current configuration and return issues."""
        issues = {
            'critical': [],
            'warning': [],
            'info': []
        }
        
        # Check for required files
        if not self.env_file.exists():
            issues['critical'].append("No .env file found. Copy env.example to .env and configure it.")
        
        # Check for critical environment variables
        critical_vars = [
            'SECRET_KEY',
            'DB_NAME',
            'DB_USER', 
            'DB_PASSWORD',
            'DEBUG'
        ]
        
        for var in critical_vars:
            if not os.getenv(var):
                issues['critical'].append(f"Missing critical environment variable: {var}")
        
        # Check for security issues
        if os.getenv('SECRET_KEY') == 'django-insecure-change-me-in-production':
            issues['critical'].append("SECRET_KEY is using default value. Change it immediately!")
        
        if os.getenv('DEBUG') == 'True' and os.getenv('SECURE_SSL_REDIRECT') == 'True':
            issues['warning'].append("DEBUG=True with SECURE_SSL_REDIRECT=True may cause issues")
        
        # Check database configuration
        if os.getenv('USE_SQLITE') == 'False':
            if not all(os.getenv(var) for var in ['DB_HOST', 'DB_PORT']):
                issues['warning'].append("PostgreSQL selected but DB_HOST or DB_PORT not set")
        
        # Check Redis configuration
        if os.getenv('USE_REDIS') == 'True':
            if not os.getenv('REDIS_URL') and not os.getenv('REDIS_HOST'):
                issues['warning'].append("Redis enabled but REDIS_URL or REDIS_HOST not set")
        
        return issues
    
    def generate_env_file(self, force: bool = False) -> bool:
        """Generate .env file from template."""
        if self.env_file.exists() and not force:
            print("❌ .env file already exists. Use --force to overwrite.")
            return False
        
        if not self.env_example.exists():
            print("❌ env.example file not found.")
            return False
        
        try:
            with open(self.env_example, 'r') as f:
                content = f.read()
            
            with open(self.env_file, 'w') as f:
                f.write(content)
            
            print("✅ .env file generated successfully!")
            print("📝 Please edit .env file with your actual values.")
            return True
        except Exception as e:
            print(f"❌ Failed to generate .env file: {e}")
            return False
    
    def show_current_config(self, show_secrets: bool = False) -> None:
        """Display current configuration."""
        print("🔧 Current Configuration:")
        print("=" * 50)
        
        # Core settings
        print("\n📋 Core Settings:")
        print(f"  DEBUG: {os.getenv('DEBUG', 'Not set')}")
        print(f"  SECRET_KEY: {'***' if not show_secrets else os.getenv('SECRET_KEY', 'Not set')}")
        print(f"  ALLOWED_HOSTS: {os.getenv('ALLOWED_HOSTS', 'Not set')}")
        
        # Database
        print("\n🗄️ Database:")
        print(f"  USE_SQLITE: {os.getenv('USE_SQLITE', 'Not set')}")
        print(f"  DB_NAME: {os.getenv('DB_NAME', 'Not set')}")
        print(f"  DB_HOST: {os.getenv('DB_HOST', 'Not set')}")
        print(f"  DB_PORT: {os.getenv('DB_PORT', 'Not set')}")
        print(f"  DB_USER: {os.getenv('DB_USER', 'Not set')}")
        print(f"  DB_PASSWORD: {'***' if not show_secrets else os.getenv('DB_PASSWORD', 'Not set')}")
        
        # Redis
        print("\n🔴 Redis:")
        print(f"  USE_REDIS: {os.getenv('USE_REDIS', 'Not set')}")
        print(f"  REDIS_URL: {os.getenv('REDIS_URL', 'Not set')}")
        print(f"  REDIS_HOST: {os.getenv('REDIS_HOST', 'Not set')}")
        print(f"  REDIS_PORT: {os.getenv('REDIS_PORT', 'Not set')}")
        
        # Celery
        print("\n🐌 Celery:")
        print(f"  CELERY_BROKER_URL: {os.getenv('CELERY_BROKER_URL', 'Not set')}")
        print(f"  CELERY_RESULT_BACKEND: {os.getenv('CELERY_RESULT_BACKEND', 'Not set')}")
        
        # Email
        print("\n📧 Email:")
        print(f"  EMAIL_BACKEND: {os.getenv('EMAIL_BACKEND', 'Not set')}")
        print(f"  EMAIL_HOST: {os.getenv('EMAIL_HOST', 'Not set')}")
        print(f"  EMAIL_PORT: {os.getenv('EMAIL_PORT', 'Not set')}")
        print(f"  EMAIL_HOST_USER: {os.getenv('EMAIL_HOST_USER', 'Not set')}")
        print(f"  EMAIL_HOST_PASSWORD: {'***' if not show_secrets else os.getenv('EMAIL_HOST_PASSWORD', 'Not set')}")
        
        # Security
        print("\n🔒 Security:")
        print(f"  SECURE_SSL_REDIRECT: {os.getenv('SECURE_SSL_REDIRECT', 'Not set')}")
        print(f"  SECURE_HSTS_SECONDS: {os.getenv('SECURE_HSTS_SECONDS', 'Not set')}")
        print(f"  CSRF_TRUSTED_ORIGINS: {os.getenv('CSRF_TRUSTED_ORIGINS', 'Not set')}")
    
    def export_docker_env(self, output_file: str = 'docker.env') -> bool:
        """Export current environment variables to Docker format."""
        try:
            with open(output_file, 'w') as f:
                for key, value in os.environ.items():
                    if value:  # Only export non-empty values
                        f.write(f"{key}={value}\n")
            
            print(f"✅ Docker environment exported to {output_file}")
            return True
        except Exception as e:
            print(f"❌ Failed to export Docker environment: {e}")
            return False
    
    def check_docker_compatibility(self) -> Dict[str, Any]:
        """Check if current config is compatible with Docker deployment."""
        issues = {
            'critical': [],
            'warning': [],
            'info': []
        }
        
        # Check for Docker-specific requirements
        if os.getenv('DB_HOST') not in ['db', 'localhost', '127.0.0.1']:
            issues['warning'].append("DB_HOST should be 'db' for Docker deployment")
        
        if os.getenv('REDIS_HOST') not in ['redis', 'localhost', '127.0.0.1']:
            issues['warning'].append("REDIS_HOST should be 'redis' for Docker deployment")
        
        # Check for required Docker environment variables
        docker_required = [
            'SECRET_KEY',
            'DB_NAME',
            'DB_USER',
            'DB_PASSWORD',
            'POSTGRES_PASSWORD'
        ]
        
        for var in docker_required:
            if not os.getenv(var):
                issues['critical'].append(f"Missing Docker required variable: {var}")
        
        return issues


def main():
    parser = argparse.ArgumentParser(description='Maintenance Dashboard Configuration Manager')
    parser.add_argument('action', choices=['validate', 'generate', 'show', 'export', 'check-docker'],
                       help='Action to perform')
    parser.add_argument('--force', action='store_true', help='Force overwrite existing files')
    parser.add_argument('--show-secrets', action='store_true', help='Show secret values in output')
    parser.add_argument('--output', help='Output file for export action')
    
    args = parser.parse_args()
    
    config_manager = ConfigManager()
    
    if args.action == 'validate':
        issues = config_manager.validate_config()
        
        if issues['critical']:
            print("❌ Critical Issues:")
            for issue in issues['critical']:
                print(f"  - {issue}")
        
        if issues['warning']:
            print("⚠️ Warnings:")
            for issue in issues['warning']:
                print(f"  - {issue}")
        
        if issues['info']:
            print("ℹ️ Info:")
            for issue in issues['info']:
                print(f"  - {issue}")
        
        if not any(issues.values()):
            print("✅ Configuration is valid!")
        
        sys.exit(1 if issues['critical'] else 0)
    
    elif args.action == 'generate':
        success = config_manager.generate_env_file(force=args.force)
        sys.exit(0 if success else 1)
    
    elif args.action == 'show':
        config_manager.show_current_config(show_secrets=args.show_secrets)
    
    elif args.action == 'export':
        output_file = args.output or 'docker.env'
        success = config_manager.export_docker_env(output_file)
        sys.exit(0 if success else 1)
    
    elif args.action == 'check-docker':
        issues = config_manager.check_docker_compatibility()
        
        if issues['critical']:
            print("❌ Docker Compatibility Issues:")
            for issue in issues['critical']:
                print(f"  - {issue}")
        
        if issues['warning']:
            print("⚠️ Docker Warnings:")
            for issue in issues['warning']:
                print(f"  - {issue}")
        
        if issues['info']:
            print("ℹ️ Docker Info:")
            for issue in issues['info']:
                print(f"  - {issue}")
        
        if not any(issues.values()):
            print("✅ Configuration is Docker compatible!")
        
        sys.exit(1 if issues['critical'] else 0)


if __name__ == '__main__':
    main()
