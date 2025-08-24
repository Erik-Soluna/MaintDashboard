# Build script with version information for Maintenance Dashboard
# This script automatically captures git information, updates version files, and builds the Docker image

param(
    [switch]$SkipVersionUpdate,
    [switch]$Help
)

if ($Help) {
    Write-Host "Usage: .\build_with_version.ps1 [-SkipVersionUpdate] [-Help]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -SkipVersionUpdate    Skip automatic version file updates"
    Write-Host "  -Help                 Show this help message"
    exit 0
}

Write-Host "🚀 Build Script with Auto Version Management" -ForegroundColor Green
Write-Host "===========================================" -ForegroundColor Green
Write-Host ""

# Check if we're in a git repository
if (-not (Test-Path ".git")) {
    Write-Error "❌ Error: Not in a git repository"
    Write-Host "   Please run this script from the root of your MaintDashboard repository" -ForegroundColor Red
    exit 1
}

# Get git information
Write-Host "📊 Capturing git version information..." -ForegroundColor Cyan
try {
    $GIT_COMMIT_COUNT = git rev-list --count HEAD
    $GIT_COMMIT_HASH = git rev-parse --short HEAD
    $GIT_BRANCH = git rev-parse --abbrev-ref HEAD
    $GIT_COMMIT_DATE = git log -1 --format=%cd --date=short
} catch {
    Write-Error "❌ Failed to get git information: $_"
    exit 1
}

Write-Host "✅ Git information captured:" -ForegroundColor Green
Write-Host "   Commit Count: $GIT_COMMIT_COUNT"
Write-Host "   Commit Hash: $GIT_COMMIT_HASH"
Write-Host "   Branch: $GIT_BRANCH"
Write-Host "   Date: $GIT_COMMIT_DATE"
Write-Host ""

# Automatically update version files unless skipped
if (-not $SkipVersionUpdate) {
    Write-Host "🔄 Updating version files automatically..." -ForegroundColor Cyan
    try {
        if (Get-Command python -ErrorAction SilentlyContinue) {
            python version.py --update
        } elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
            python3 version.py --update
        } else {
            Write-Warning "⚠️  Python not found, skipping automatic version file update"
        }
    } catch {
        Write-Warning "⚠️  Failed to update version files: $_"
    }
} else {
    Write-Host "⏭️  Skipping version file update (requested)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "🐳 Building Docker image with version v$GIT_COMMIT_COUNT.$GIT_COMMIT_HASH..." -ForegroundColor Cyan

# Build Docker image with version information
try {
    docker-compose build --build-arg GIT_COMMIT_COUNT=$GIT_COMMIT_COUNT `
                         --build-arg GIT_COMMIT_HASH=$GIT_COMMIT_HASH `
                         --build-arg GIT_BRANCH=$GIT_BRANCH `
                         --build-arg GIT_COMMIT_DATE=$GIT_COMMIT_DATE
    
    Write-Host ""
    Write-Host "✅ Build completed successfully!" -ForegroundColor Green
    Write-Host "🚀 Version v$GIT_COMMIT_COUNT.$GIT_COMMIT_HASH is ready for deployment" -ForegroundColor Green
    Write-Host ""
    Write-Host "📋 For Portainer deployment, use these environment variables:" -ForegroundColor Cyan
    Write-Host "   GIT_COMMIT_COUNT=$GIT_COMMIT_COUNT"
    Write-Host "   GIT_COMMIT_HASH=$GIT_COMMIT_HASH"
    Write-Host "   GIT_BRANCH=$GIT_BRANCH"
    Write-Host "   GIT_COMMIT_DATE=$GIT_COMMIT_DATE"
    Write-Host ""
    Write-Host "🌐 Version info will be available at /core/version/ after deployment" -ForegroundColor Cyan
    
} catch {
    Write-Host ""
    Write-Error "❌ Build failed!"
    exit 1
}
