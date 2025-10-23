#!/usr/bin/env python
"""
Script to fix migration conflicts and set up branding system
"""
import os
import sys
import django
from django.core.management import execute_from_command_line

def main():
    print("🔧 Fixing migration conflicts...")
    
    # Set up Django environment
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maintdashboard.settings')
    django.setup()
    
    try:
        # Run migration merge
        print("📦 Running migration merge...")
        execute_from_command_line(['manage.py', 'makemigrations', '--merge'])
        print("✅ Migration merge completed")
        
        # Run migrations
        print("📦 Running migrations...")
        execute_from_command_line(['manage.py', 'migrate'])
        print("✅ Migrations completed")
        
        # Set up branding system
        print("🎨 Setting up branding system...")
        execute_from_command_line(['manage.py', 'setup_branding'])
        print("✅ Branding system setup completed")
        
        print("🎉 All migration conflicts resolved successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
