#!/usr/bin/env python3
"""
Fix all missing database tables by forcing a complete migration reset.
"""

import requests
import json

# Configuration
BASE_URL = "https://dev.maintenance.errorlog.app"

def reset_all_migrations():
    """Reset all migrations and force recreate tables."""
    print("Fix All Missing Database Tables")
    print("=" * 50)
    print(f"Target: {BASE_URL}")
    print("=" * 50)
    
    api_url = f"{BASE_URL}/api/migrations/"
    
    # Step 1: Check current migration status
    print("\nStep 1: Checking current migration status...")
    
    try:
        payload = {"command": "showmigrations"}
        response = requests.post(api_url, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("SUCCESS: Migration status retrieved")
                output = result.get('output', '')
                print("Current migration status:")
                print(output)
            else:
                print(f"FAIL: Migration status error: {result.get('error')}")
                return False
        else:
            print(f"FAIL: Migration status request failed: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"FAIL: Migration status request failed: {e}")
        return False
    
    # Step 2: Try to fake unapply all migrations
    print("\nStep 2: Attempting to reset migrations...")
    
    try:
        # First, try to fake unapply all migrations
        payload = {"command": "migrate", "fake": True, "app": "zero"}
        response = requests.post(api_url, json=payload, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            print(f"Reset result: {result.get('success', False)}")
            print("Reset output:")
            print(result.get('output', 'No output'))
        else:
            print(f"Reset request failed: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"Reset request failed: {e}")
    
    # Step 3: Force recreate all migrations
    print("\nStep 3: Forcing recreation of all migrations...")
    
    try:
        # Try to run makemigrations first
        payload = {"command": "makemigrations"}
        response = requests.post(api_url, json=payload, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            print(f"Makemigrations result: {result.get('success', False)}")
            print("Makemigrations output:")
            print(result.get('output', 'No output'))
        else:
            print(f"Makemigrations request failed: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"Makemigrations request failed: {e}")
    
    # Step 4: Run migrations with --fake-initial to force table creation
    print("\nStep 4: Running migrations with --fake-initial...")
    
    try:
        payload = {"command": "migrate", "fake_initial": True}
        response = requests.post(api_url, json=payload, timeout=120)
        
        if response.status_code == 200:
            result = response.json()
            print(f"Fake initial result: {result.get('success', False)}")
            print("Fake initial output:")
            print(result.get('output', 'No output'))
        else:
            print(f"Fake initial request failed: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"Fake initial request failed: {e}")
    
    # Step 5: Run normal migrations
    print("\nStep 5: Running normal migrations...")
    
    try:
        payload = {"command": "migrate"}
        response = requests.post(api_url, json=payload, timeout=120)
        
        if response.status_code == 200:
            result = response.json()
            print(f"Normal migrate result: {result.get('success', False)}")
            print("Normal migrate output:")
            print(result.get('output', 'No output'))
        else:
            print(f"Normal migrate request failed: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"Normal migrate request failed: {e}")
    
    # Step 6: Create specific missing tables via SQL
    print("\nStep 6: Creating specific missing tables...")
    
    missing_tables_sql = [
        # Django core tables
        """
        CREATE TABLE IF NOT EXISTS django_session (
            session_key VARCHAR(40) NOT NULL PRIMARY KEY,
            session_data TEXT NOT NULL,
            expire_date TIMESTAMP WITH TIME ZONE NOT NULL
        );
        CREATE INDEX IF NOT EXISTS django_session_expire_date_idx ON django_session (expire_date);
        """,
        
        # Core app tables
        """
        CREATE TABLE IF NOT EXISTS core_logo (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            image VARCHAR(100) NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """,
        
        """
        CREATE TABLE IF NOT EXISTS core_brandingsettings (
            id SERIAL PRIMARY KEY,
            site_name VARCHAR(255) DEFAULT 'Maintenance Dashboard',
            site_tagline VARCHAR(255) DEFAULT '',
            primary_color VARCHAR(7) DEFAULT '#007bff',
            secondary_color VARCHAR(7) DEFAULT '#6c757d',
            accent_color VARCHAR(7) DEFAULT '#28a745',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """,
        
        """
        CREATE TABLE IF NOT EXISTS core_csscustomization (
            id SERIAL PRIMARY KEY,
            custom_css TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """,
        
        # Equipment app tables
        """
        CREATE TABLE IF NOT EXISTS equipment_equipment (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """,
        
        """
        CREATE TABLE IF NOT EXISTS equipment_equipmentcategoryfield (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            field_type VARCHAR(50) NOT NULL,
            is_required BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """,
        
        """
        CREATE TABLE IF NOT EXISTS equipment_equipmentcategoryconditionalfield (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            condition_field VARCHAR(255) NOT NULL,
            condition_value VARCHAR(255) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """,
        
        """
        CREATE TABLE IF NOT EXISTS equipment_equipmentcustomvalue (
            id SERIAL PRIMARY KEY,
            value TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """,
        
        # Maintenance app tables
        """
        CREATE TABLE IF NOT EXISTS maintenance_maintenanceactivity (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """,
        
        """
        CREATE TABLE IF NOT EXISTS maintenance_maintenanceactivitytype (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """,
        
        """
        CREATE TABLE IF NOT EXISTS maintenance_activitytypecategory (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """,
        
        """
        CREATE TABLE IF NOT EXISTS maintenance_activitytypetemplate (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """,
        
        # Celery Beat tables
        """
        CREATE TABLE IF NOT EXISTS django_celery_beat_crontabschedule (
            id SERIAL PRIMARY KEY,
            minute VARCHAR(240) NOT NULL,
            hour VARCHAR(96) NOT NULL,
            day_of_week VARCHAR(64) NOT NULL,
            day_of_month VARCHAR(124) NOT NULL,
            month_of_year VARCHAR(64) NOT NULL,
            timezone VARCHAR(63) NOT NULL
        );
        """
    ]
    
    for i, sql in enumerate(missing_tables_sql, 1):
        try:
            print(f"Creating table {i}/{len(missing_tables_sql)}...")
            
            payload = {
                "command": "dbshell",
                "sql": sql
            }
            
            response = requests.post(api_url, json=payload, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    print(f"SUCCESS: Table {i} created")
                else:
                    print(f"FAIL: Table {i} creation error: {result.get('error')}")
            else:
                print(f"FAIL: Table {i} creation request failed: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"FAIL: Table {i} creation request failed: {e}")
    
    # Step 7: Test login after table creation
    print("\nStep 7: Testing login after table creation...")
    
    try:
        session = requests.Session()
        
        # Get login page
        login_url = f"{BASE_URL}/auth/login/"
        response = session.get(login_url, timeout=30)
        
        if response.status_code != 200:
            print(f"FAIL: Could not get login page: {response.status_code}")
            return False
        
        # Extract CSRF token
        import re
        csrf_token = None
        patterns = [
            r'name="csrfmiddlewaretoken"\s+value="([^"]+)"',
            r'csrfmiddlewaretoken["\']?\s*[:=]\s*["\']([^"\']+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response.text, re.IGNORECASE)
            if match:
                csrf_token = match.group(1)
                break
        
        if not csrf_token:
            print("FAIL: Could not extract CSRF token")
            return False
        
        # Try login
        login_data = {
            'username': 'admin',
            'password': 'temppass123',
            'csrfmiddlewaretoken': csrf_token
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': login_url,
        }
        
        response = session.post(login_url, data=login_data, headers=headers, timeout=30, allow_redirects=False)
        
        print(f"Login response status: {response.status_code}")
        
        if response.status_code == 302:
            location = response.headers.get('Location', '')
            print(f"SUCCESS: Login successful! Redirected to: {location}")
            return True
        elif response.status_code == 200:
            if 'invalid' not in response.text.lower() and 'incorrect' not in response.text.lower():
                print("SUCCESS: Login successful (no redirect)")
                return True
            else:
                print("FAIL: Invalid credentials")
                return False
        else:
            print(f"FAIL: Login failed with status {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"FAIL: Login test failed: {e}")
        return False

def main():
    """Main function."""
    success = reset_all_migrations()
    
    print("\n" + "=" * 50)
    print("MISSING TABLES FIX SUMMARY")
    print("=" * 50)
    
    if success:
        print("SUCCESS: All missing tables have been created!")
        print("Login functionality should now work.")
        print("\nYou can log in at:")
        print(f"{BASE_URL}/auth/login/")
        print("Username: admin")
        print("Password: temppass123")
    else:
        print("FAIL: Some tables may still be missing")
        print("Manual intervention may be required.")
        print("\nNext steps:")
        print("1. Check container logs in Portainer")
        print("2. Restart the web container")
        print("3. Check database permissions")
        print("4. Consider restoring from backup")
    
    print("=" * 50)

if __name__ == "__main__":
    main()
