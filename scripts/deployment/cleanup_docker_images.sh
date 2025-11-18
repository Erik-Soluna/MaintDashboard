#!/bin/bash

# Docker Image Cleanup Script for Maintenance Dashboard
# This script removes unused Docker images to prevent accumulation
# Run this script periodically or before/after deployments

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Configuration
DRY_RUN="${DRY_RUN:-false}"
KEEP_LAST_N="${KEEP_LAST_N:-3}"  # Keep last N images
FORCE="${FORCE:-false}"

print_status "🧹 Docker Image Cleanup Script"
print_status "This will remove unused/dangling images for Maintenance Dashboard"

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ] && ! command -v sudo &> /dev/null; then
    print_warning "⚠️  Not running as root. Some cleanup operations may require elevated privileges."
fi

# Function to get image size
get_image_size() {
    docker images --format "{{.Size}}" "$1" 2>/dev/null | head -1
}

# Function to count images
count_images() {
    docker images --filter "reference=maint-dashboard*" --format "{{.ID}}" | wc -l
}

# Show current image count
CURRENT_COUNT=$(count_images)
print_status "📊 Current Maintenance Dashboard images: $CURRENT_COUNT"

if [ "$CURRENT_COUNT" -eq 0 ]; then
    print_warning "⚠️  No Maintenance Dashboard images found. Nothing to clean."
    exit 0
fi

# List current images
print_status "📋 Current images:"
docker images --filter "reference=maint-dashboard*" --format "table {{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.Size}}\t{{.CreatedAt}}"

if [ "$DRY_RUN" = "true" ]; then
    print_warning "🔍 DRY RUN MODE - No images will be deleted"
    print_status "Would remove images older than the last $KEEP_LAST_N"
    exit 0
fi

# Confirm before proceeding
if [ "$FORCE" != "true" ]; then
    echo ""
    read -p "Do you want to proceed with cleanup? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_warning "⚠️  Cleanup cancelled by user"
        exit 0
    fi
fi

print_status "🗑️  Starting cleanup..."

# 1. Remove dangling images (untagged)
print_status "1️⃣  Removing dangling images..."
DANGLING_COUNT=$(docker images -f "dangling=true" -q | wc -l)
if [ "$DANGLING_COUNT" -gt 0 ]; then
    docker image prune -f
    print_success "✅ Removed dangling images"
else
    print_status "ℹ️  No dangling images found"
fi

# 2. Remove unused images (not used by any container)
print_status "2️⃣  Removing unused images..."
UNUSED_COUNT=$(docker images --filter "reference=maint-dashboard*" --format "{{.ID}}" | wc -l)
if [ "$UNUSED_COUNT" -gt "$KEEP_LAST_N" ]; then
    # Get all images sorted by creation date (newest first)
    IMAGE_IDS=$(docker images --filter "reference=maint-dashboard*" --format "{{.ID}}" --no-trunc | head -n -$KEEP_LAST_N)
    
    if [ -n "$IMAGE_IDS" ]; then
        for IMAGE_ID in $IMAGE_IDS; do
            IMAGE_INFO=$(docker images --format "{{.Repository}}:{{.Tag}}" "$IMAGE_ID")
            print_status "   Removing: $IMAGE_INFO"
            docker rmi "$IMAGE_ID" 2>/dev/null || print_warning "   ⚠️  Could not remove $IMAGE_INFO (may be in use)"
        done
        print_success "✅ Removed old unused images (kept last $KEEP_LAST_N)"
    fi
else
    print_status "ℹ️  Only $UNUSED_COUNT images found, keeping all (threshold: $KEEP_LAST_N)"
fi

# 3. System-wide cleanup (optional - more aggressive)
if [ "$FORCE" = "true" ]; then
    print_status "3️⃣  Performing system-wide cleanup..."
    docker system prune -af --volumes 2>/dev/null || print_warning "⚠️  System prune failed (may require root)"
    print_success "✅ System cleanup completed"
fi

# Show final count
FINAL_COUNT=$(count_images)
print_success "✅ Cleanup complete!"
print_status "📊 Remaining Maintenance Dashboard images: $FINAL_COUNT"
print_status "💾 Freed space: $((CURRENT_COUNT - FINAL_COUNT)) images removed"

# Show remaining images
if [ "$FINAL_COUNT" -gt 0 ]; then
    print_status "📋 Remaining images:"
    docker images --filter "reference=maint-dashboard*" --format "table {{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.Size}}\t{{.CreatedAt}}"
fi

