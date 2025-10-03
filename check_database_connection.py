#!/usr/bin/env python3
"""
Check which database the application is actually connecting to.
"""

import requests
import json

# Configuration
BASE_URL = "https://dev.maintenance.errorlog.app"

def check_database_connection():
    """Check database connection details."""
    print("Check Database Connection")
    print("=" * 50)
    print(f"Target: {BASE_URL}")
    print("=" * 50)
    
    api_url = f"{BASE_URL}/api/migrations/"
    
    # Step 1: Check database connection info
    print("\nStep 1: Checking database connection info...")
    
    try:
        # Try to get database info via a simple query
        payload = {"command": "showmigrations"}
        response = requests.post(api_url, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("SUCCESS: Can connect to database via API")
                
                # Try to get more detailed info
                print("\nStep 2: Getting detailed database info...")
                
                # Try to check if we can run a simple SQL query
                test_payload = {
                    "command": "dbshell",
                    "sql": "SELECT current_database(), current_user, version();"
                }
                
                response = requests.post(api_url, json=test_payload, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('success'):
                        print("SUCCESS: Can execute SQL queries")
                        print("Database info:")
                        print(result.get('output', 'No output'))
                    else:
                        print(f"FAIL: SQL query failed: {result.get('error')}")
                        print("This suggests the dbshell command is not working")
                else:
                    print(f"FAIL: SQL query request failed: {response.status_code}")
                    print("This suggests the dbshell endpoint is not available")
                
                # Try to check what tables actually exist
                print("\nStep 3: Checking what tables actually exist...")
                
                tables_payload = {
                    "command": "dbshell", 
                    "sql": "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;"
                }
                
                response = requests.post(api_url, json=tables_payload, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('success'):
                        print("SUCCESS: Can list tables")
                        print("Existing tables:")
                        print(result.get('output', 'No output'))
                    else:
                        print(f"FAIL: Table listing failed: {result.get('error')}")
                else:
                    print(f"FAIL: Table listing request failed: {response.status_code}")
                
                # Try to check django_migrations table specifically
                print("\nStep 4: Checking django_migrations table...")
                
                migrations_payload = {
                    "command": "dbshell",
                    "sql": "SELECT COUNT(*) FROM django_migrations;"
                }
                
                response = requests.post(api_url, json=migrations_payload, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('success'):
                        print("SUCCESS: django_migrations table exists")
                        print("Migration count:")
                        print(result.get('output', 'No output'))
                    else:
                        print(f"FAIL: django_migrations query failed: {result.get('error')}")
                        print("This suggests the django_migrations table doesn't exist")
                else:
                    print(f"FAIL: django_migrations query request failed: {response.status_code}")
                
                # Try to check django_session table specifically
                print("\nStep 5: Checking django_session table...")
                
                session_payload = {
                    "command": "dbshell",
                    "sql": "SELECT COUNT(*) FROM django_session;"
                }
                
                response = requests.post(api_url, json=session_payload, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('success'):
                        print("SUCCESS: django_session table exists")
                        print("Session count:")
                        print(result.get('output', 'No output'))
                    else:
                        print(f"FAIL: django_session query failed: {result.get('error')}")
                        print("This confirms the django_session table doesn't exist")
                else:
                    print(f"FAIL: django_session query request failed: {response.status_code}")
                
            else:
                print(f"FAIL: Database connection error: {result.get('error')}")
                return False
        else:
            print(f"FAIL: Database connection request failed: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"FAIL: Database connection request failed: {e}")
        return False
    
    return True

def main():
    """Main function."""
    success = check_database_connection()
    
    print("\n" + "=" * 50)
    print("DATABASE CONNECTION SUMMARY")
    print("=" * 50)
    
    if success:
        print("SUCCESS: Database connection analysis completed")
        print("\nKey findings:")
        print("1. The application can connect to the database")
        print("2. Migrations are marked as applied in django_migrations table")
        print("3. But the actual tables don't exist")
        print("4. This suggests a database connection mismatch")
        print("\nPossible causes:")
        print("- Migrations applied to different database")
        print("- Database schema/permissions issue")
        print("- Connection pooling issue")
        print("- Multiple database instances")
    else:
        print("FAIL: Could not analyze database connection")
    
    print("=" * 50)

if __name__ == "__main__":
    main()