#!/usr/bin/env python
"""
Manual fix script for Roles & Permissions issues.
Run this script to fix both the System Permissions and Site Selection issues.
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maintenance_dashboard.settings')
django.setup()

from django.db import transaction
from core.rbac import initialize_default_permissions
from core.models import Permission, Role
from django.contrib.sessions.models import Session


def fix_system_permissions():
    """Fix the System Permissions issue by ensuring all permissions are created."""
    print("🔒 Fixing System Permissions...")
    
    try:
        with transaction.atomic():
            # Initialize all default permissions
            permissions = initialize_default_permissions()
            
            # Count permissions by module
            total_permissions = Permission.objects.filter(is_active=True).count()
            print(f"   ✅ Total permissions in database: {total_permissions}")
            
            # Display permissions by module
            modules = Permission.objects.values_list('module', flat=True).distinct()
            for module in modules:
                count = Permission.objects.filter(module=module, is_active=True).count()
                print(f"   📂 {module}: {count} permissions")
            
            # Count roles
            total_roles = Role.objects.filter(is_active=True).count()
            system_roles = Role.objects.filter(is_active=True, is_system_role=True).count()
            custom_roles = total_roles - system_roles
            
            print(f"   🎭 System Roles: {system_roles}")
            print(f"   🎭 Custom Roles: {custom_roles}")
            print(f"   🎭 Total Roles: {total_roles}")
            
            if total_permissions > 0:
                print("   ✅ System Permissions successfully populated!")
                return True
            else:
                print("   ❌ No permissions found after initialization")
                return False
                
    except Exception as e:
        print(f"   ❌ Error during permission initialization: {str(e)}")
        return False


def fix_site_selection():
    """Fix the Site Selection issue by clearing all user sessions."""
    print("\n🌐 Fixing Site Selection...")
    
    try:
        # Clear all sessions to reset site selection state
        session_count = Session.objects.count()
        Session.objects.all().delete()
        
        print(f"   ✅ Cleared {session_count} user sessions")
        print("   ✅ Site selection state has been reset")
        print("   ℹ️  Users will need to log in again")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error clearing sessions: {str(e)}")
        return False


def verify_fixes():
    """Verify that the fixes are working correctly."""
    print("\n🔍 Verifying Fixes...")
    
    # Check permissions
    permission_count = Permission.objects.filter(is_active=True).count()
    role_count = Role.objects.filter(is_active=True).count()
    
    print(f"   📋 Active Permissions: {permission_count}")
    print(f"   🎭 Active Roles: {role_count}")
    
    if permission_count > 0 and role_count > 0:
        print("   ✅ Permission system is working correctly")
        permission_success = True
    else:
        print("   ❌ Permission system still has issues")
        permission_success = False
    
    # For site selection, we can only verify that sessions were cleared
    session_count = Session.objects.count()
    print(f"   🔄 Current Sessions: {session_count}")
    
    return permission_success


def main():
    """Main function to run all fixes."""
    print("🛠️  Starting Roles & Permissions Fix Script...")
    print("=" * 50)
    
    # Fix system permissions
    permissions_fixed = fix_system_permissions()
    
    # Fix site selection
    site_selection_fixed = fix_site_selection()
    
    # Verify fixes
    verification_success = verify_fixes()
    
    print("\n" + "=" * 50)
    print("📊 Fix Summary:")
    print(f"   System Permissions: {'✅ FIXED' if permissions_fixed else '❌ FAILED'}")
    print(f"   Site Selection: {'✅ FIXED' if site_selection_fixed else '❌ FAILED'}")
    print(f"   Verification: {'✅ PASSED' if verification_success else '❌ FAILED'}")
    
    if permissions_fixed and site_selection_fixed:
        print("\n🎉 All fixes completed successfully!")
        print("\n📋 Next Steps:")
        print("   1. Restart your Django server")
        print("   2. Clear your browser cache")
        print("   3. Log in again and test:")
        print("      - Go to Settings → Roles & Permissions")
        print("      - Test site selection dropdown")
        print("      - Verify permissions are visible")
        
        return True
    else:
        print("\n❌ Some fixes failed. Please check the errors above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)