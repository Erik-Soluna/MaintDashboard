#!/bin/bash

# Build script with version information for Maintenance Dashboard
# This script automatically captures git information, updates version files, and builds the Docker image

set -e

echo "🚀 Build Script with Auto Version Management"
echo "==========================================="
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

# Automatically update version files
echo "🔄 Updating version files automatically..."
if command -v python3 &> /dev/null; then
    python3 version.py --update
elif command -v python &> /dev/null; then
    python version.py --update
else
    echo "⚠️  Python not found, skipping automatic version file update"
fi

echo ""
echo "🐳 Building Docker image with version v$GIT_COMMIT_COUNT.$GIT_COMMIT_HASH..."

# Build Docker image with version information
docker-compose build --build-arg GIT_COMMIT_COUNT=$GIT_COMMIT_COUNT \
                     --build-arg GIT_COMMIT_HASH=$GIT_COMMIT_HASH \
                     --build-arg GIT_BRANCH=$GIT_BRANCH \
                     --build-arg GIT_COMMIT_DATE=$GIT_COMMIT_DATE

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Build completed successfully!"
    echo "🚀 Version v$GIT_COMMIT_COUNT.$GIT_COMMIT_HASH is ready for deployment"
    echo ""
    echo "📋 For Portainer deployment, use these environment variables:"
    echo "   GIT_COMMIT_COUNT=$GIT_COMMIT_COUNT"
    echo "   GIT_COMMIT_HASH=$GIT_COMMIT_HASH"
    echo "   GIT_BRANCH=$GIT_BRANCH"
    echo "   GIT_COMMIT_DATE=$GIT_COMMIT_DATE"
    echo ""
    echo "🌐 Version info will be available at /core/version/ after deployment"
else
    echo ""
    echo "❌ Build failed!"
    exit 1
fi
