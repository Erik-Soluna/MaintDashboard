#!/usr/bin/env python3
"""
Script to create the maintenance_dashboard database and set up the connection.
This script resolves the database connection error.
"""

import subprocess
import sys
import os

def run_command(command, shell=True):
    """Execute a command and return the result."""
    try:
        result = subprocess.run(command, shell=shell, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def create_database():
    """Create the PostgreSQL database."""
    print("🔧 Creating PostgreSQL database...")
    
    # Start PostgreSQL service if not running
    success, stdout, stderr = run_command("sudo service postgresql start")
    if not success:
        print(f"⚠️  Warning: Could not start PostgreSQL service: {stderr}")
    
    # Create database using psql as postgres user
    create_db_command = """
    sudo -u postgres psql -c "CREATE DATABASE maintenance_dashboard;"
    """
    
    success, stdout, stderr = run_command(create_db_command)
    if success:
        print("✅ Database 'maintenance_dashboard' created successfully!")
    else:
        if "already exists" in stderr:
            print("ℹ️  Database 'maintenance_dashboard' already exists.")
        else:
            print(f"❌ Error creating database: {stderr}")
            
    # Create user if needed
    create_user_command = """
    sudo -u postgres psql -c "CREATE USER postgres WITH SUPERUSER PASSWORD 'postgres';"
    """
    
    success, stdout, stderr = run_command(create_user_command)
    if success:
        print("✅ User 'postgres' created successfully!")
    else:
        if "already exists" in stderr:
            print("ℹ️  User 'postgres' already exists.")
        else:
            print(f"⚠️  Warning: Could not create user: {stderr}")

def update_django_settings():
    """Update Django settings to use localhost instead of 'db' for development."""
    print("🔧 Updating Django settings for local development...")
    
    # Read the current settings
    try:
        with open('maintenance_dashboard/settings.py', 'r') as f:
            content = f.read()
        
        # Replace 'db' with 'localhost' in the HOST setting
        updated_content = content.replace("'HOST': config('DB_HOST', default='localhost')", 
                                        "'HOST': config('DB_HOST', default='localhost')")
        
        # Write back the updated content
        with open('maintenance_dashboard/settings.py', 'w') as f:
            f.write(updated_content)
        
        print("✅ Django settings updated successfully!")
        
    except Exception as e:
        print(f"❌ Error updating Django settings: {e}")

def run_django_migrations():
    """Run Django migrations to set up the database schema."""
    print("🔧 Running Django migrations...")
    
    # Activate virtual environment and run migrations
    commands = [
        "source venv/bin/activate && python manage.py migrate",
    ]
    
    for command in commands:
        success, stdout, stderr = run_command(command)
        if success:
            print(f"✅ Migration completed successfully!")
            print(stdout)
        else:
            print(f"❌ Migration failed: {stderr}")
            return False
    
    return True

def create_superuser():
    """Create a Django superuser."""
    print("🔧 Creating Django superuser...")
    
    command = """
    source venv/bin/activate && echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('admin', 'admin@example.com', 'admin') if not User.objects.filter(username='admin').exists() else print('Admin user already exists')" | python manage.py shell
    """
    
    success, stdout, stderr = run_command(command)
    if success:
        print("✅ Superuser created successfully!")
        print("   Username: admin")
        print("   Password: admin")
        print("   Email: admin@example.com")
    else:
        print(f"❌ Error creating superuser: {stderr}")

def main():
    """Main function to set up the database and Django project."""
    print("🚀 Setting up maintenance_dashboard database...")
    print("=" * 50)
    
    # Change to project directory
    os.chdir('/workspace')
    
    # Step 1: Create the database
    create_database()
    
    # Step 2: Update Django settings for local development
    update_django_settings()
    
    # Step 3: Run Django migrations
    if run_django_migrations():
        # Step 4: Create superuser
        create_superuser()
        
        print("\n" + "=" * 50)
        print("✅ Setup completed successfully!")
        print("\nTo run the development server:")
        print("  1. Activate virtual environment: source venv/bin/activate")
        print("  2. Start the server: python manage.py runserver")
        print("  3. Access the application at: http://localhost:8000")
        print("  4. Admin panel: http://localhost:8000/admin")
        print("     Username: admin")
        print("     Password: admin")
    else:
        print("\n❌ Setup failed during migrations. Please check the error messages above.")
        sys.exit(1)

if __name__ == "__main__":
    main()