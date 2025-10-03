#!/usr/bin/env python3
"""
Force a complete database reset by unapplying all migrations and reapplying them.
"""

import requests
import json

# Configuration
BASE_URL = "https://dev.maintenance.errorlog.app"

def force_database_reset():
    """Force a complete database reset."""
    print("Force Database Reset")
    print("=" * 50)
    print(f"Target: {BASE_URL}")
    print("=" * 50)
    
    api_url = f"{BASE_URL}/api/migrations/"
    
    # Step 1: Try to unapply all migrations (migrate zero)
    print("\nStep 1: Unapplying all migrations...")
    
    try:
        payload = {"command": "migrate", "app": "zero"}
        response = requests.post(api_url, json=payload, timeout=120)
        
        if response.status_code == 200:
            result = response.json()
            print(f"Unapply result: {result.get('success', False)}")
            print("Unapply output:")
            print(result.get('output', 'No output'))
        else:
            print(f"Unapply request failed: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"Unapply request failed: {e}")
    
    # Step 2: Try to fake unapply all migrations
    print("\nStep 2: Fake unapplying all migrations...")
    
    try:
        payload = {"command": "migrate", "app": "zero", "fake": True}
        response = requests.post(api_url, json=payload, timeout=120)
        
        if response.status_code == 200:
            result = response.json()
            print(f"Fake unapply result: {result.get('success', False)}")
            print("Fake unapply output:")
            print(result.get('output', 'No output'))
        else:
            print(f"Fake unapply request failed: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"Fake unapply request failed: {e}")
    
    # Step 3: Check migration status after unapply
    print("\nStep 3: Checking migration status after unapply...")
    
    try:
        payload = {"command": "showmigrations"}
        response = requests.post(api_url, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("Migration status after unapply:")
                print(result.get('output', 'No output'))
            else:
                print(f"Migration status error: {result.get('error')}")
        else:
            print(f"Migration status request failed: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"Migration status request failed: {e}")
    
    # Step 4: Force recreate migrations
    print("\nStep 4: Forcing recreation of migrations...")
    
    try:
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
    
    # Step 5: Apply migrations with --fake-initial
    print("\nStep 5: Applying migrations with --fake-initial...")
    
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
    
    # Step 6: Apply normal migrations
    print("\nStep 6: Applying normal migrations...")
    
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
    
    # Step 7: Test login after reset
    print("\nStep 7: Testing login after database reset...")
    
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
    success = force_database_reset()
    
    print("\n" + "=" * 50)
    print("DATABASE RESET SUMMARY")
    print("=" * 50)
    
    if success:
        print("SUCCESS: Database reset completed successfully!")
        print("Login functionality should now work.")
        print("\nYou can log in at:")
        print(f"{BASE_URL}/auth/login/")
        print("Username: admin")
        print("Password: temppass123")
    else:
        print("FAIL: Database reset did not resolve the issue")
        print("The problem may be more complex than expected.")
        print("\nNext steps:")
        print("1. Check container logs in Portainer")
        print("2. Restart the web container")
        print("3. Check database permissions")
        print("4. Consider restoring from backup")
        print("5. Check if multiple database instances exist")
    
    print("=" * 50)

if __name__ == "__main__":
    main()
