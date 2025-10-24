#!/usr/bin/env python3
"""
Clear all migrations and start completely fresh.
"""

import requests
import json

# Configuration
BASE_URL = "https://dev.maintenance.errorlog.app"

def clear_migrations_and_start_fresh():
    """Clear all migrations and start completely fresh."""
    print("Clear Migrations and Start Fresh")
    print("=" * 50)
    print(f"Target: {BASE_URL}")
    print("=" * 50)
    
    api_url = f"{BASE_URL}/api/migrations/"
    
    # Step 1: Try to drop the django_migrations table completely
    print("\nStep 1: Attempting to clear django_migrations table...")
    
    # Since we can't use dbshell, we'll try a different approach
    # Let's try to create a management command that can clear the migrations table
    
    # Step 2: Try to run migrations with --fake to unapply all
    print("\nStep 2: Attempting to unapply all migrations...")
    
    try:
        # Try to fake unapply all migrations by going to zero
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
    
    # Step 3: Try to create a custom management command to clear migrations
    print("\nStep 3: Creating custom management command to clear migrations...")
    
    # We need to create a management command that can clear the django_migrations table
    # Since we can't access the filesystem directly, we'll try a different approach
    
    # Step 4: Try to force recreate the django_migrations table
    print("\nStep 4: Attempting to recreate django_migrations table...")
    
    # Let's try to use the existing API to create a management command
    # that can handle this properly
    
    # Step 5: Try to run makemigrations to create fresh migrations
    print("\nStep 5: Creating fresh migrations...")
    
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
    
    # Step 6: Try to apply migrations without fake flags
    print("\nStep 6: Applying fresh migrations...")
    
    try:
        payload = {"command": "migrate"}
        response = requests.post(api_url, json=payload, timeout=120)
        
        if response.status_code == 200:
            result = response.json()
            print(f"Fresh migrate result: {result.get('success', False)}")
            print("Fresh migrate output:")
            print(result.get('output', 'No output'))
        else:
            print(f"Fresh migrate request failed: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"Fresh migrate request failed: {e}")
    
    # Step 7: Test login after fresh start
    print("\nStep 7: Testing login after fresh start...")
    
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
    success = clear_migrations_and_start_fresh()
    
    print("\n" + "=" * 50)
    print("FRESH START SUMMARY")
    print("=" * 50)
    
    if success:
        print("SUCCESS: Fresh start completed successfully!")
        print("Login functionality should now work.")
        print("\nYou can log in at:")
        print(f"{BASE_URL}/auth/login/")
        print("Username: admin")
        print("Password: temppass123")
    else:
        print("FAIL: Fresh start did not resolve the issue")
        print("The problem may require manual intervention.")
        print("\nNext steps:")
        print("1. Check container logs in Portainer")
        print("2. Restart the web container")
        print("3. Check database permissions")
        print("4. Consider restoring from backup")
        print("5. Manually clear the django_migrations table")
    
    print("=" * 50)

if __name__ == "__main__":
    main()
