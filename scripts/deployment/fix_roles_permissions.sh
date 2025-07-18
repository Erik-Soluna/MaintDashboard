#!/bin/bash

# Fix Roles & Permissions Issues Script
# This script fixes both the System Permissions and Site Selection issues

echo "🛠️  Roles & Permissions Fix Script"
echo "=================================="

# Check if Python is available
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ Error: Python is not installed or not in PATH"
    exit 1
fi

echo "🐍 Using Python: $PYTHON_CMD"

# Check if Django is available
if ! $PYTHON_CMD -c "import django" 2>/dev/null; then
    echo "❌ Error: Django is not installed"
    echo "ℹ️  Please install dependencies first:"
    echo "   pip install -r requirements.txt"
    exit 1
fi

echo "✅ Django is available"

# Run the fix script
echo ""
echo "🔧 Running fixes..."
$PYTHON_CMD fix_permissions_and_site_selection.py

# Check if the fix script was successful
if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Fix script completed successfully!"
    echo ""
    echo "📋 Manual verification steps:"
    echo "   1. Restart your Django server if it's running"
    echo "   2. Clear your browser cache and cookies"
    echo "   3. Log in to the application again"
    echo "   4. Navigate to Settings → Roles & Permissions"
    echo "   5. Verify the System Permissions section is populated"
    echo "   6. Test the site selection dropdown in the header"
    echo ""
    echo "✅ If you see permissions listed and site selection works correctly, the issues are fixed!"
else
    echo ""
    echo "❌ Fix script failed. Please check the output above for errors."
    echo ""
    echo "🔧 Manual troubleshooting steps:"
    echo "   1. Check if the database is accessible"
    echo "   2. Ensure all Django migrations are applied:"
    echo "      python manage.py migrate"
    echo "   3. Try running the permission command manually:"
    echo "      python manage.py ensure_permissions"
    echo "   4. Check the Django logs for any errors"
    exit 1
fi