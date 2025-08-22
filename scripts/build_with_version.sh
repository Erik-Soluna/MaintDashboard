#!/bin/bash

# Build script with version information for Maintenance Dashboard
# This script captures git information and builds the Docker image with version data

echo "🔍 Capturing git version information..."

# Get git information
GIT_COMMIT_COUNT=$(git rev-list --count HEAD)
GIT_COMMIT_HASH=$(git rev-parse --short HEAD)
GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
GIT_COMMIT_DATE=$(git log -1 --format=%cd --date=short)

echo "📊 Version Info:"
echo "  Commit Count: $GIT_COMMIT_COUNT"
echo "  Commit Hash: $GIT_COMMIT_HASH"
echo "  Branch: $GIT_BRANCH"
echo "  Date: $GIT_COMMIT_DATE"

# Build Docker image with version information
echo "🐳 Building Docker image with version $GIT_COMMIT_COUNT.$GIT_COMMIT_HASH..."

docker-compose build --build-arg GIT_COMMIT_COUNT=$GIT_COMMIT_COUNT \
                     --build-arg GIT_COMMIT_HASH=$GIT_COMMIT_HASH \
                     --build-arg GIT_BRANCH=$GIT_BRANCH \
                     --build-arg GIT_COMMIT_DATE=$GIT_COMMIT_DATE

if [ $? -eq 0 ]; then
    echo "✅ Build completed successfully!"
    echo "🚀 Version $GIT_COMMIT_COUNT.$GIT_COMMIT_HASH is ready for deployment"
else
    echo "❌ Build failed!"
    exit 1
fi
