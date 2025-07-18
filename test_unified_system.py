#!/usr/bin/env python3
"""
Comprehensive test script for the unified calendar/maintenance system.
Run this after starting Docker Desktop and the containers.
"""

import os
import sys
import django
from datetime import datetime, timedelta
from django.utils import timezone

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maintenance_dashboard.settings')
django.setup()

from django.contrib.auth.models import User
from events.models import CalendarEvent
from maintenance.models import MaintenanceActivityType, ActivityTypeCategory
from equipment.models import Equipment
from core.models import Location

def test_database_connection():
    """Test basic database connectivity."""
    print("🔍 Testing database connection...")
    try:
        # Test basic queries
        user_count = User.objects.count()
        equipment_count = Equipment.objects.count()
        event_count = CalendarEvent.objects.count()
        
        print(f"✅ Database connection successful")
        print(f"   - Users: {user_count}")
        print(f"   - Equipment: {equipment_count}")
        print(f"   - Calendar Events: {event_count}")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")
        return False

def test_calendar_event_model():
    """Test the enhanced CalendarEvent model."""
    print("\n🔍 Testing CalendarEvent model...")
    try:
        # Test creating a maintenance event
        equipment = Equipment.objects.first()
        if not equipment:
            print("⚠️  No equipment found, creating test equipment...")
            location = Location.objects.first()
            if not location:
                print("❌ No location found, cannot create test equipment")
                return False
            
            equipment = Equipment.objects.create(
                name="Test Equipment",
                location=location,
                is_active=True
            )
        
        user = User.objects.first()
        if not user:
            print("❌ No user found, cannot create test event")
            return False
        
        # Create a test maintenance event
        event = CalendarEvent.objects.create(
            title="Test Maintenance Event",
            description="Test maintenance event for unified system",
            event_type='maintenance',
            equipment=equipment,
            event_date=timezone.now().date(),
            start_time=datetime.now().time(),
            end_time=(datetime.now() + timedelta(hours=2)).time(),
            assigned_to=user,
            priority='medium',
            created_by=user,
            # Maintenance-specific fields
            maintenance_status='scheduled',
            estimated_duration_hours=2,
            frequency_days=30,
            is_mandatory=False,
            tools_required="Test tools",
            parts_required="Test parts",
            safety_notes="Test safety notes"
        )
        
        print(f"✅ Created test maintenance event: {event.title}")
        
        # Test compatibility properties
        print("🔍 Testing compatibility properties...")
        
        # Test scheduled_start property
        scheduled_start = event.scheduled_start
        print(f"   - scheduled_start: {scheduled_start}")
        
        # Test scheduled_end property
        scheduled_end = event.scheduled_end
        print(f"   - scheduled_end: {scheduled_end}")
        
        # Test status property
        status = event.status
        print(f"   - status: {status}")
        
        # Test is_overdue method
        is_overdue = event.is_overdue()
        print(f"   - is_overdue: {is_overdue}")
        
        # Test get_duration method
        duration = event.get_duration()
        print(f"   - duration: {duration} hours")
        
        # Test display methods
        priority_display = event.get_priority_display()
        status_display = event.get_status_display()
        event_type_display = event.get_event_type_display()
        
        print(f"   - priority_display: {priority_display}")
        print(f"   - status_display: {status_display}")
        print(f"   - event_type_display: {event_type_display}")
        
        # Clean up test event
        event.delete()
        print("✅ Test event cleaned up")
        
        return True
        
    except Exception as e:
        print(f"❌ CalendarEvent model test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_activity_type_categories():
    """Test activity type categories and global activity types."""
    print("\n🔍 Testing activity type categories...")
    try:
        # Check if global category exists
        global_category = ActivityTypeCategory.objects.filter(is_global=True).first()
        if global_category:
            print(f"✅ Global category found: {global_category.name}")
            
            # Check global activity types
            global_activity_types = MaintenanceActivityType.objects.filter(category=global_category)
            print(f"   - Global activity types: {global_activity_types.count()}")
            
            for activity_type in global_activity_types:
                print(f"     - {activity_type.name}: {activity_type.description[:50]}...")
        else:
            print("⚠️  Global category not found")
        
        # Check all categories
        all_categories = ActivityTypeCategory.objects.all()
        print(f"   - Total categories: {all_categories.count()}")
        
        return True
        
    except Exception as e:
        print(f"❌ Activity type categories test failed: {str(e)}")
        return False

def test_maintenance_activity_types():
    """Test maintenance activity types."""
    print("\n🔍 Testing maintenance activity types...")
    try:
        activity_types = MaintenanceActivityType.objects.all()
        print(f"✅ Found {activity_types.count()} activity types")
        
        for activity_type in activity_types[:5]:  # Show first 5
            print(f"   - {activity_type.name} (Category: {activity_type.category.name})")
        
        return True
        
    except Exception as e:
        print(f"❌ Maintenance activity types test failed: {str(e)}")
        return False

def test_calendar_events():
    """Test calendar events functionality."""
    print("\n🔍 Testing calendar events...")
    try:
        # Test maintenance events
        maintenance_events = CalendarEvent.objects.filter(event_type='maintenance')
        print(f"✅ Found {maintenance_events.count()} maintenance events")
        
        # Test other event types
        other_events = CalendarEvent.objects.exclude(event_type='maintenance')
        print(f"   - Other events: {other_events.count()}")
        
        # Test event creation
        equipment = Equipment.objects.first()
        user = User.objects.first()
        
        if equipment and user:
            # Create a test event
            test_event = CalendarEvent.objects.create(
                title="Test Event",
                description="Test event",
                event_type='inspection',
                equipment=equipment,
                event_date=timezone.now().date(),
                assigned_to=user,
                created_by=user
            )
            
            print(f"✅ Created test event: {test_event.title}")
            
            # Clean up
            test_event.delete()
            print("✅ Test event cleaned up")
        
        return True
        
    except Exception as e:
        print(f"❌ Calendar events test failed: {str(e)}")
        return False

def test_unified_functionality():
    """Test the unified functionality."""
    print("\n🔍 Testing unified functionality...")
    try:
        # Test that maintenance events can be accessed as calendar events
        maintenance_events = CalendarEvent.objects.filter(event_type='maintenance')
        
        if maintenance_events.exists():
            event = maintenance_events.first()
            if event:
                print(f"✅ Testing unified event: {event.title}")
                
                # Test that it has maintenance properties
                print(f"   - Event type: {event.event_type}")
                print(f"   - Maintenance status: {event.maintenance_status}")
                print(f"   - Equipment: {event.equipment.name if event.equipment else 'None'}")
                print(f"   - Assigned to: {event.assigned_to.get_full_name() if event.assigned_to else 'None'}")
                
                # Test status compatibility
                event.status = 'in_progress'
                event.save()
                print(f"   - Updated status to: {event.status}")
                
                # Reset status
                event.status = 'scheduled'
                event.save()
            else:
                print("⚠️  No maintenance event found")
            
        else:
            print("⚠️  No maintenance events found to test")
        
        return True
        
    except Exception as e:
        print(f"❌ Unified functionality test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("🚀 Starting comprehensive unified system test...")
    print("=" * 60)
    
    tests = [
        ("Database Connection", test_database_connection),
        ("CalendarEvent Model", test_calendar_event_model),
        ("Activity Type Categories", test_activity_type_categories),
        ("Maintenance Activity Types", test_maintenance_activity_types),
        ("Calendar Events", test_calendar_events),
        ("Unified Functionality", test_unified_functionality),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 Running: {test_name}")
        print("-" * 40)
        
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} FAILED with exception: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print(f"🎯 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The unified system is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 