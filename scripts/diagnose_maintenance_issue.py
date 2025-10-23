#!/usr/bin/env python3
"""
Diagnostic script to identify maintenance creation issues.
This script will check various components that could cause maintenance creation to fail.
"""

import os
import sys
import django
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maintenance_dashboard.settings')
django.setup()

from django.db import connection
from django.core.exceptions import ValidationError
from maintenance.models import MaintenanceActivity, MaintenanceActivityType
from equipment.models import Equipment
from core.models import Location, User
from maintenance.forms import MaintenanceActivityForm
from django.test import RequestFactory
import json

def check_database_connection():
    """Check if database connection is working."""
    print("🔍 Checking database connection...")
    try:
        connection.ensure_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            if result:
                print("✅ Database connection: OK")
                return True
    except Exception as e:
        print(f"❌ Database connection: FAILED - {str(e)}")
        return False

def check_equipment_data():
    """Check if there's equipment data available."""
    print("\n🔍 Checking equipment data...")
    try:
        total_equipment = Equipment.objects.count()
        active_equipment = Equipment.objects.filter(is_active=True).count()
        print(f"📊 Total equipment: {total_equipment}")
        print(f"📊 Active equipment: {active_equipment}")
        
        if active_equipment == 0:
            print("⚠️  WARNING: No active equipment found!")
            return False
        
        # Show some sample equipment
        sample_equipment = Equipment.objects.filter(is_active=True)[:3]
        print("📋 Sample equipment:")
        for eq in sample_equipment:
            print(f"   - {eq.name} (ID: {eq.id}, Location: {eq.location.name if eq.location else 'None'})")
        
        return True
    except Exception as e:
        print(f"❌ Equipment data check: FAILED - {str(e)}")
        return False

def check_activity_types():
    """Check if there are activity types available."""
    print("\n🔍 Checking activity types...")
    try:
        total_types = MaintenanceActivityType.objects.count()
        active_types = MaintenanceActivityType.objects.filter(is_active=True).count()
        print(f"📊 Total activity types: {total_types}")
        print(f"📊 Active activity types: {active_types}")
        
        if active_types == 0:
            print("⚠️  WARNING: No active activity types found!")
            return False
        
        # Show some sample activity types
        sample_types = MaintenanceActivityType.objects.filter(is_active=True)[:3]
        print("📋 Sample activity types:")
        for at in sample_types:
            print(f"   - {at.name} (ID: {at.id}, Category: {at.category.name if at.category else 'None'})")
        
        return True
    except Exception as e:
        print(f"❌ Activity types check: FAILED - {str(e)}")
        return False

def check_users():
    """Check if there are users available for assignment."""
    print("\n🔍 Checking users...")
    try:
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        print(f"📊 Total users: {total_users}")
        print(f"📊 Active users: {active_users}")
        
        if active_users == 0:
            print("⚠️  WARNING: No active users found!")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Users check: FAILED - {str(e)}")
        return False

def check_timezone_field():
    """Check if the timezone field exists in the database."""
    print("\n🔍 Checking timezone field...")
    try:
        # Try to access the timezone field
        activity = MaintenanceActivity.objects.first()
        if activity:
            timezone_value = activity.timezone
            print(f"✅ Timezone field: OK (sample value: {timezone_value})")
            return True
        else:
            print("⚠️  No maintenance activities found to test timezone field")
            return True  # Field might exist but no data
    except Exception as e:
        print(f"❌ Timezone field check: FAILED - {str(e)}")
        return False

def test_form_creation():
    """Test creating a maintenance activity form."""
    print("\n🔍 Testing form creation...")
    try:
        # Create a mock request
        factory = RequestFactory()
        request = factory.get('/')
        
        # Get sample data
        equipment = Equipment.objects.filter(is_active=True).first()
        activity_type = MaintenanceActivityType.objects.filter(is_active=True).first()
        user = User.objects.filter(is_active=True).first()
        
        if not equipment or not activity_type:
            print("❌ Cannot test form - missing required data")
            return False
        
        # Test form with minimal data
        form_data = {
            'equipment': equipment.id,
            'activity_type': activity_type.id,
            'title': 'Test Maintenance',
            'description': 'Test description',
            'status': 'scheduled',
            'priority': 'medium',
            'scheduled_start': '2025-01-15 09:00',
            'scheduled_end': '2025-01-15 17:00',
            'timezone': 'America/Chicago',
        }
        
        if user:
            form_data['assigned_to'] = user.id
        
        form = MaintenanceActivityForm(data=form_data, request=request)
        
        if form.is_valid():
            print("✅ Form validation: OK")
            return True
        else:
            print(f"❌ Form validation: FAILED")
            print(f"   Errors: {form.errors}")
            return False
            
    except Exception as e:
        print(f"❌ Form creation test: FAILED - {str(e)}")
        return False

def test_activity_creation():
    """Test actually creating a maintenance activity."""
    print("\n🔍 Testing activity creation...")
    try:
        # Get sample data
        equipment = Equipment.objects.filter(is_active=True).first()
        activity_type = MaintenanceActivityType.objects.filter(is_active=True).first()
        user = User.objects.filter(is_active=True).first()
        
        if not equipment or not activity_type:
            print("❌ Cannot test activity creation - missing required data")
            return False
        
        # Create test activity
        activity = MaintenanceActivity.objects.create(
            equipment=equipment,
            activity_type=activity_type,
            title='Diagnostic Test Activity',
            description='This is a test activity created by the diagnostic script',
            status='scheduled',
            priority='medium',
            scheduled_start='2025-01-15 09:00',
            scheduled_end='2025-01-15 17:00',
            timezone='America/Chicago',
            assigned_to=user,
            created_by=user
        )
        
        print(f"✅ Activity creation: OK (ID: {activity.id})")
        
        # Clean up - delete the test activity
        activity.delete()
        print("🧹 Test activity cleaned up")
        
        return True
        
    except Exception as e:
        print(f"❌ Activity creation test: FAILED - {str(e)}")
        return False

def main():
    """Run all diagnostic checks."""
    print("🚀 Starting Maintenance Creation Diagnostic")
    print("=" * 50)
    
    checks = [
        check_database_connection,
        check_equipment_data,
        check_activity_types,
        check_users,
        check_timezone_field,
        test_form_creation,
        test_activity_creation,
    ]
    
    results = []
    for check in checks:
        try:
            result = check()
            results.append(result)
        except Exception as e:
            print(f"❌ Check failed with exception: {str(e)}")
            results.append(False)
    
    print("\n" + "=" * 50)
    print("📊 DIAGNOSTIC SUMMARY")
    print("=" * 50)
    
    passed = sum(results)
    total = len(results)
    
    print(f"✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {total - passed}/{total}")
    
    if passed == total:
        print("🎉 All checks passed! Maintenance creation should work.")
    else:
        print("⚠️  Some checks failed. This explains why maintenance creation is not working.")
        print("\n🔧 RECOMMENDED FIXES:")
        
        if not results[0]:  # Database connection
            print("   - Fix database connection issues")
        if not results[1]:  # Equipment data
            print("   - Add equipment data or check equipment filtering")
        if not results[2]:  # Activity types
            print("   - Add maintenance activity types")
        if not results[3]:  # Users
            print("   - Ensure there are active users in the system")
        if not results[4]:  # Timezone field
            print("   - Run database migrations to add timezone field")
        if not results[5]:  # Form validation
            print("   - Check form validation logic and required fields")
        if not results[6]:  # Activity creation
            print("   - Check model constraints and database permissions")

if __name__ == "__main__":
    main()
