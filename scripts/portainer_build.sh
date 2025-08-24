#!/bin/bash

# Portainer Build Script for Maintenance Dashboard
# This script automatically captures git information and updates version files
# Run this script before deploying to Portainer for automatic version management

echo "🚀 Portainer Build Script for Maintenance Dashboard"
echo "=================================================="
echo ""

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    echo "❌ Error: Not in a git repository"
    echo "   Please run this script from the root of your MaintDashboard repository"
    exit 1
fi

# Get git information
echo "📊 Capturing git version information..."
GIT_COMMIT_COUNT=$(git rev-list --count HEAD)
GIT_COMMIT_HASH=$(git rev-parse --short HEAD)
GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
GIT_COMMIT_DATE=$(git log -1 --format=%cd --date=short)

echo "✅ Git information captured:"
echo "   Commit Count: $GIT_COMMIT_COUNT"
echo "   Commit Hash: $GIT_COMMIT_HASH"
echo "   Branch: $GIT_BRANCH"
echo "   Date: $GIT_COMMIT_DATE"
echo ""

# Automatically update version files using the unified system
echo "🔄 Updating version files automatically..."
if command -v python3 &> /dev/null; then
    python3 version.py --update
elif command -v python &> /dev/null; then
    python version.py --update
else
    echo "⚠️  Python not found, skipping automatic version file update"
fi

echo ""
echo "🔧 For Portainer deployment, set these environment variables:"
echo "=============================================================="
echo "GIT_COMMIT_COUNT=$GIT_COMMIT_COUNT"
echo "GIT_COMMIT_HASH=$GIT_COMMIT_HASH"
echo "GIT_BRANCH=$GIT_BRANCH"
echo "GIT_COMMIT_DATE=$GIT_COMMIT_DATE"
echo ""

echo "📝 Copy the above variables into your Portainer stack environment section"
echo "   Or use the 'Environment' tab when editing your stack"
echo ""

echo "🌐 After deployment, version info will be available at:"
echo "   - /core/version/ (JSON format)"
echo "   - /core/version/html/ (HTML page)"
echo "   - Settings → Version Info (navigation menu)"
echo ""

echo "🎯 Alternative: Use the build script for local Docker builds:"
echo "   ./scripts/build_with_version.sh"
echo ""

echo "✨ Happy deploying!"
echo ""
echo "💡 Pro tip: Add this script to your deployment workflow for automatic version updates!"
