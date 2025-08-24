#!/bin/bash

# Docker Build Hook Script for Maintenance Dashboard
# This script automatically handles version information during Docker builds
# Use this with: docker build --build-arg GIT_COMMIT_COUNT=$(git rev-list --count HEAD) ...

set -e

echo "🐳 Docker Build Hook for Maintenance Dashboard"
echo "=============================================="
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

# Update version files automatically
echo "🔄 Updating version files..."
if command -v python3 &> /dev/null; then
    python3 version.py --update
elif command -v python &> /dev/null; then
    python version.py --update
else
    echo "⚠️  Python not found, skipping automatic version file update"
fi

echo ""
echo "🔧 Docker build command with version arguments:"
echo "================================================"
echo "docker build \\"
echo "  --build-arg GIT_COMMIT_COUNT=$GIT_COMMIT_COUNT \\"
echo "  --build-arg GIT_COMMIT_HASH=$GIT_COMMIT_HASH \\"
echo "  --build-arg GIT_BRANCH=$GIT_BRANCH \\"
echo "  --build-arg GIT_COMMIT_DATE=$GIT_COMMIT_DATE \\"
echo "  -t maint-dashboard:v$GIT_COMMIT_COUNT.$GIT_COMMIT_HASH \\"
echo "  ."
echo ""

echo "🚀 Or use the simplified build script:"
echo "   ./scripts/build_with_version.sh"
echo ""

echo "📋 Version information will be embedded in the Docker image:"
echo "   - Environment variables set at build time"
echo "   - Available at runtime via os.environ"
echo "   - Automatic fallback if git info unavailable"
echo ""

echo "✨ Ready for Docker build!"
echo ""
echo "💡 Pro tip: This script can be integrated into your CI/CD pipeline!"
