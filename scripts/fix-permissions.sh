#!/bin/bash

# Quick Permissions Fix Script
# Fixes the missing system permissions issue in Roles and Permissions

echo "🔒 Fixing Missing System Permissions..."
echo ""

# Check if we're in a Docker environment
if [ -f "docker-compose.yml" ]; then
    echo "📦 Docker environment detected"
    echo "Running permission initialization in Docker container..."
    docker-compose exec web python manage.py ensure_permissions
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "✅ Permissions fixed successfully!"
        echo ""
        echo "🎯 Next steps:"
        echo "1. Go to Settings → Roles & Permissions"
        echo "2. You should now see all system permissions"
        echo "3. Create or edit roles with appropriate permissions"
        echo ""
        echo "📋 Available permission modules:"
        echo "   - Admin (full system access)"
        echo "   - Equipment (view, create, edit, delete)"
        echo "   - Maintenance (manage activities and schedules)"
        echo "   - Users (manage user accounts)"
        echo "   - Settings (manage system configuration)"
        echo "   - Calendar (manage calendar events)"
        echo "   - Reports (view and generate reports)"
    else
        echo "❌ Error running permission fix in Docker"
        echo "Try running manually:"
        echo "   docker-compose exec web python manage.py init_rbac"
    fi
    
else
    echo "🐍 Manual Python environment detected"
    echo "Running permission initialization..."
    
    # Try different Python commands
    if command -v python3 &> /dev/null; then
        python3 manage.py ensure_permissions
    elif command -v python &> /dev/null; then
        python manage.py ensure_permissions
    else
        echo "❌ Python not found. Please run manually:"
        echo "   python manage.py ensure_permissions"
        exit 1
    fi
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "✅ Permissions fixed successfully!"
        echo ""
        echo "🎯 Access the Roles & Permissions interface:"
        echo "   http://localhost:8000/core/settings/roles-permissions/"
    else
        echo "❌ Error running permission fix"
        echo "Try the alternative command:"
        echo "   python manage.py init_rbac"
    fi
fi

echo ""
echo "🆘 If you still have issues:"
echo "   - Restart the Django server/container"
echo "   - Check the troubleshooting guide: docs/troubleshooting/bug-fixes.md"
echo "   - Log out and log back in to refresh permissions"