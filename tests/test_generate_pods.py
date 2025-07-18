#!/usr/bin/env python3
"""
Test script to verify the generate_pods management command works.
"""

import os
import sys
import django

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maintenance_dashboard.settings')
django.setup()

from django.core.management import call_command
from core.models import Location

def test_generate_pods():
    """Test the generate_pods management command."""
    print("Testing generate_pods management command...")
    
    # Check if we have any sites
    sites = Location.objects.filter(is_site=True)
    print(f"Found {sites.count()} sites:")
    for site in sites:
        print(f"  - {site.name} (ID: {site.id})")
    
    if not sites.exists():
        print("No sites found. Creating a test site...")
        from django.contrib.auth.models import User
        
        # Get or create system user
        system_user, created = User.objects.get_or_create(
            username='system',
            defaults={
                'email': 'system@example.com',
                'first_name': 'System',
                'last_name': 'User',
                'is_active': False
            }
        )
        
        # Create a test site
        test_site = Location.objects.create(
            name='Test Site',
            is_site=True,
            created_by=system_user,
            updated_by=system_user
        )
        print(f"Created test site: {test_site.name}")
    
    # Test the generate_pods command
    print("\nRunning generate_pods command...")
    try:
        call_command('generate_pods', '--pod-count', '3', '--mdcs-per-pod', '2')
        print("✅ generate_pods command executed successfully!")
        
        # Check results
        total_pods = Location.objects.filter(is_site=False, parent_location__is_site=True).count()
        total_mdcs = Location.objects.filter(is_site=False, parent_location__is_site=False).count()
        
        print(f"Results:")
        print(f"  - Total PODs created: {total_pods}")
        print(f"  - Total MDCs created: {total_mdcs}")
        
        # Show the hierarchy
        print("\nLocation hierarchy:")
        for site in Location.objects.filter(is_site=True):
            print(f"  {site.name}")
            for pod in site.child_locations.all():
                print(f"    └── {pod.name}")
                for mdc in pod.child_locations.all():
                    print(f"        └── {mdc.name}")
        
    except Exception as e:
        print(f"❌ Error running generate_pods command: {e}")
        return False
    
    return True

if __name__ == '__main__':
    success = test_generate_pods()
    sys.exit(0 if success else 1) 