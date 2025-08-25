# Portainer Build Script for Maintenance Dashboard (PowerShell)
# This script automatically captures git information and updates version files
# Run this script before deploying to Portainer for automatic version management

Write-Host "🚀 Portainer Build Script for Maintenance Dashboard" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green
Write-Host ""

# Check if we're in a git repository
if (-not (Test-Path ".git")) {
    Write-Host "❌ Error: Not in a git repository" -ForegroundColor Red
    Write-Host "   Please run this script from the root of your MaintDashboard repository" -ForegroundColor Red
    exit 1
}

# Get git information
Write-Host "📊 Capturing git version information..." -ForegroundColor Yellow
try {
    $GIT_COMMIT_COUNT = git rev-list --count HEAD
    $GIT_COMMIT_HASH = git rev-parse --short HEAD
    $GIT_BRANCH = git rev-parse --abbrev-ref HEAD
    $GIT_COMMIT_DATE = git log -1 --format=%cd --date=short
    
    Write-Host "✅ Git information captured:" -ForegroundColor Green
    Write-Host "   Commit Count: $GIT_COMMIT_COUNT" -ForegroundColor White
    Write-Host "   Commit Hash: $GIT_COMMIT_HASH" -ForegroundColor White
    Write-Host "   Branch: $GIT_BRANCH" -ForegroundColor White
    Write-Host "   Date: $GIT_COMMIT_DATE" -ForegroundColor White
    Write-Host ""
} catch {
    Write-Host "❌ Error capturing git information: $_" -ForegroundColor Red
    exit 1
}

# Automatically update version files using the unified system
Write-Host "🔄 Updating version files automatically..." -ForegroundColor Yellow
try {
    python version.py --update
    Write-Host "✅ Version files updated successfully" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Python not found or error updating version files: $_" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "🔧 For Portainer deployment, set these environment variables:" -ForegroundColor Cyan
Write-Host "==============================================================" -ForegroundColor Cyan
Write-Host "GIT_COMMIT_COUNT=$GIT_COMMIT_COUNT" -ForegroundColor White
Write-Host "GIT_COMMIT_HASH=$GIT_COMMIT_HASH" -ForegroundColor White
Write-Host "GIT_BRANCH=$GIT_BRANCH" -ForegroundColor White
Write-Host "GIT_COMMIT_DATE=$GIT_COMMIT_DATE" -ForegroundColor White
Write-Host ""

Write-Host "📝 Copy the above variables into your Portainer stack environment section" -ForegroundColor Yellow
Write-Host "   Or use the 'Environment' tab when editing your stack" -ForegroundColor Yellow
Write-Host ""

Write-Host "🌐 After deployment, version info will be available at:" -ForegroundColor Cyan
Write-Host "   - /version/ (JSON format)" -ForegroundColor White
Write-Host "   - /version/html/ (HTML page)" -ForegroundColor White
Write-Host "   - Settings → Version Info (navigation menu)" -ForegroundColor White
Write-Host ""

Write-Host "🎯 Alternative: Use the build script for local Docker builds:" -ForegroundColor Yellow
Write-Host "   .\scripts\build_with_version.ps1" -ForegroundColor White
Write-Host ""

Write-Host "✨ Happy deploying!" -ForegroundColor Green
Write-Host ""
Write-Host "💡 Pro tip: Add this script to your deployment workflow for automatic version updates!" -ForegroundColor Cyan

