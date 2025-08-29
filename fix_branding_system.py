#!/usr/bin/env python
"""
Fix Branding System Setup Script
This script resolves migration issues and sets up the branding system manually.
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maintenance_dashboard.settings')
django.setup()

from django.db import connection

def main():
    print("🔧 Fixing Branding System Setup...")
    
    try:
        with connection.cursor() as cursor:
            print("\n1. Creating missing branding tables...")
            
            # Create BrandingSettings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS core_brandingsettings (
                    id SERIAL PRIMARY KEY,
                    site_name VARCHAR(200) DEFAULT 'Maintenance Dashboard',
                    site_tagline VARCHAR(300),
                    window_title_prefix VARCHAR(100) DEFAULT '',
                    window_title_suffix VARCHAR(100) DEFAULT '',
                    header_brand_text VARCHAR(200) DEFAULT 'Maintenance Dashboard',
                    navigation_overview_label VARCHAR(50) DEFAULT 'Overview',
                    navigation_equipment_label VARCHAR(50) DEFAULT 'Equipment',
                    navigation_maintenance_label VARCHAR(50) DEFAULT 'Maintenance',
                    navigation_calendar_label VARCHAR(50) DEFAULT 'Calendar',
                    navigation_map_label VARCHAR(50) DEFAULT 'Map',
                    navigation_settings_label VARCHAR(50) DEFAULT 'Settings',
                    navigation_debug_label VARCHAR(50) DEFAULT 'Debug',
                    footer_copyright_text VARCHAR(200) DEFAULT '© 2025 Maintenance Dashboard. All rights reserved.',
                    footer_powered_by_text VARCHAR(100) DEFAULT 'Powered by Django',
                    primary_color VARCHAR(7) DEFAULT '#4299e1',
                    secondary_color VARCHAR(7) DEFAULT '#2d3748',
                    accent_color VARCHAR(7) DEFAULT '#3182ce',
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    logo_id INTEGER
                )
            ''')
            print("   ✅ BrandingSettings table created")
            
            # Create CSSCustomization table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS core_csscustomization (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100),
                    item_type VARCHAR(20),
                    description TEXT,
                    css_code TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    priority INTEGER DEFAULT 0,
                    "order" INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by_id INTEGER
                )
            ''')
            print("   ✅ CSSCustomization table created")
            
            print("\n2. Marking problematic migrations as applied...")
            
            # Mark all problematic migrations as applied
            problematic_migrations = [
                '0012_merge_20250829_1245',
                '0013_fix_logo_field_name',
                '0014_auto_20250829_1259',
                '0015_merge_20250829_1311'
            ]
            
            for migration in problematic_migrations:
                cursor.execute(
                    "INSERT INTO django_migrations (app, name, applied) VALUES ('core', %s, CURRENT_TIMESTAMP) ON CONFLICT DO NOTHING",
                    (migration,)
                )
                print(f"   ✅ {migration} marked as applied")
            
            print("\n3. Verifying table creation...")
            
            # Check what tables exist
            cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name LIKE 'core_%'")
            tables = [row[0] for row in cursor.fetchall()]
            
            branding_tables = ['core_brandingsettings', 'core_csscustomization', 'core_logo']
            for table in branding_tables:
                if table in tables:
                    print(f"   ✅ {table} exists")
                else:
                    print(f"   ❌ {table} missing")
            
            print("\n4. Setting up branding system...")
            
            # Import and run the setup_branding command
            from django.core.management import call_command
            call_command('setup_branding')
            print("   ✅ Branding system setup completed")
            
            print("\n🎉 Branding System Setup Complete!")
            print("\nNext steps:")
            print("1. Restart your web container in Portainer")
            print("2. Check the branding page at /branding/")
            print("3. Verify the main dashboard loads without errors")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nPlease check the error and try again.")
        return False
    
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
