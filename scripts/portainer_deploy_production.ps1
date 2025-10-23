# Production Portainer Deployment Script for Maintenance Dashboard (PowerShell)
# This script automates the complete production deployment process
# Run this script to prepare and deploy to Portainer production environment

param(
    [switch]$SkipVersionUpdate,
    [switch]$SkipValidation,
    [switch]$Help
)

# Function to print colored output
function Write-Header {
    param([string]$Message)
    Write-Host "================================================" -ForegroundColor Magenta
    Write-Host $Message -ForegroundColor Magenta
    Write-Host "================================================" -ForegroundColor Magenta
}

function Write-Status {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

# Function to check prerequisites
function Test-Prerequisites {
    Write-Header "🔍 Checking Prerequisites"
    
    # Check if we're in a git repository
    if (-not (Test-Path ".git")) {
        Write-Error "Not in a git repository"
        Write-Error "Please run this script from the root of your MaintDashboard repository"
        exit 1
    }
    
    # Check if required files exist
    $requiredFiles = @(
        "portainer-stack.yml",
        "portainer.env.template",
        "Dockerfile",
        "scripts/deployment/docker-entrypoint.sh"
    )
    
    foreach ($file in $requiredFiles) {
        if (-not (Test-Path $file)) {
            Write-Error "Required file missing: $file"
            exit 1
        }
    }
    
    # Check if Python is available
    if (-not (Get-Command python -ErrorAction SilentlyContinue) -and -not (Get-Command python3 -ErrorAction SilentlyContinue)) {
        Write-Warning "Python not found - version information may not be updated"
    }
    
    Write-Success "All prerequisites met"
}

# Function to update version information
function Update-VersionInfo {
    if ($SkipVersionUpdate) {
        Write-Warning "Skipping version update as requested"
        return
    }
    
    Write-Header "📊 Updating Version Information"
    
    # Get git information
    Write-Status "Capturing git version information..."
    try {
        $GIT_COMMIT_COUNT = git rev-list --count HEAD
        $GIT_COMMIT_HASH = git rev-parse --short HEAD
        $GIT_BRANCH = git rev-parse --abbrev-ref HEAD
        $GIT_COMMIT_DATE = git log -1 --format=%cd --date=short
        
        Write-Success "Git information captured:"
        Write-Host "   Commit Count: $GIT_COMMIT_COUNT" -ForegroundColor White
        Write-Host "   Commit Hash: $GIT_COMMIT_HASH" -ForegroundColor White
        Write-Host "   Branch: $GIT_BRANCH" -ForegroundColor White
        Write-Host "   Date: $GIT_COMMIT_DATE" -ForegroundColor White
        
        # Update version files using the unified system
        Write-Status "Updating version files automatically..."
        try {
            python version.py --update
            Write-Success "Version files updated successfully"
        } catch {
            Write-Warning "Python not found or error updating version files: $_"
        }
        
        # Update portainer.env.template with current version
        Write-Status "Updating portainer.env.template with current version..."
        $templateContent = Get-Content "portainer.env.template" -Raw
        $templateContent = $templateContent -replace "GIT_COMMIT_COUNT=.*", "GIT_COMMIT_COUNT=$GIT_COMMIT_COUNT"
        $templateContent = $templateContent -replace "GIT_COMMIT_HASH=.*", "GIT_COMMIT_HASH=$GIT_COMMIT_HASH"
        $templateContent = $templateContent -replace "GIT_BRANCH=.*", "GIT_BRANCH=$GIT_BRANCH"
        $templateContent = $templateContent -replace "GIT_COMMIT_DATE=.*", "GIT_COMMIT_DATE=$GIT_COMMIT_DATE"
        $templateContent = $templateContent -replace "Current Version: .*", "Current Version: v$GIT_COMMIT_COUNT.$GIT_COMMIT_HASH"
        $templateContent = $templateContent -replace "Generated on .*", "Generated on $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
        Set-Content "portainer.env.template" -Value $templateContent
        
        Write-Success "Version information updated successfully"
        
        # Set global variables for later use
        $script:GIT_COMMIT_COUNT = $GIT_COMMIT_COUNT
        $script:GIT_COMMIT_HASH = $GIT_COMMIT_HASH
        $script:GIT_BRANCH = $GIT_BRANCH
        $script:GIT_COMMIT_DATE = $GIT_COMMIT_DATE
        
    } catch {
        Write-Error "Error capturing git information: $_"
        exit 1
    }
}

# Function to validate production configuration
function Test-ProductionConfig {
    if ($SkipValidation) {
        Write-Warning "Skipping validation as requested"
        return
    }
    
    Write-Header "🔧 Validating Production Configuration"
    
    # Check if production stack file exists and is valid
    if (-not (Test-Path "portainer-stack.yml")) {
        Write-Error "Production stack file not found: portainer-stack.yml"
        exit 1
    }
    
    # Basic validation of stack file
    $stackContent = Get-Content "portainer-stack.yml" -Raw
    if (-not ($stackContent -match "services:")) {
        Write-Error "Invalid portainer-stack.yml - missing services section"
        exit 1
    }
    
    # Check for required services
    $requiredServices = @("db", "redis", "web", "celery", "celery-beat")
    foreach ($service in $requiredServices) {
        if (-not ($stackContent -match "  $service`:")) {
            Write-Error "Required service missing from stack: $service"
            exit 1
        }
    }
    
    # Check for security settings
    if (-not ($stackContent -match "SECURE_SSL_REDIRECT=True")) {
        Write-Warning "SSL redirect not enabled in production stack"
    }
    
    if (-not ($stackContent -match "DEBUG=False")) {
        Write-Warning "Debug mode not disabled in production stack"
    }
    
    Write-Success "Production configuration validation completed"
}

# Function to generate deployment summary
function Show-DeploymentSummary {
    Write-Header "📋 Deployment Summary"
    
    Write-Host "🚀 Production Deployment Ready!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📊 Version Information:" -ForegroundColor Cyan
    Write-Host "   Version: v$script:GIT_COMMIT_COUNT.$script:GIT_COMMIT_HASH" -ForegroundColor White
    Write-Host "   Commit: $script:GIT_COMMIT_HASH" -ForegroundColor White
    Write-Host "   Branch: $script:GIT_BRANCH" -ForegroundColor White
    Write-Host "   Date: $script:GIT_COMMIT_DATE" -ForegroundColor White
    Write-Host ""
    Write-Host "🔧 Required Environment Variables for Portainer:" -ForegroundColor Cyan
    Write-Host "   GIT_COMMIT_COUNT=$script:GIT_COMMIT_COUNT" -ForegroundColor White
    Write-Host "   GIT_COMMIT_HASH=$script:GIT_COMMIT_HASH" -ForegroundColor White
    Write-Host "   GIT_BRANCH=$script:GIT_BRANCH" -ForegroundColor White
    Write-Host "   GIT_COMMIT_DATE=$script:GIT_COMMIT_DATE" -ForegroundColor White
    Write-Host ""
    Write-Host "📁 Files Ready for Deployment:" -ForegroundColor Cyan
    Write-Host "   ✅ portainer-stack.yml (Production stack configuration)" -ForegroundColor Green
    Write-Host "   ✅ portainer.env.template (Environment variables template)" -ForegroundColor Green
    Write-Host "   ✅ Dockerfile (Container build configuration)" -ForegroundColor Green
    Write-Host "   ✅ scripts/deployment/docker-entrypoint.sh (Container entrypoint)" -ForegroundColor Green
    Write-Host ""
    Write-Host "🌐 Post-Deployment Verification:" -ForegroundColor Cyan
    Write-Host "   • Health Check: https://your-domain/health/simple/" -ForegroundColor White
    Write-Host "   • Version Info: https://your-domain/version/" -ForegroundColor White
    Write-Host "   • Admin Panel: https://your-domain/admin/" -ForegroundColor White
    Write-Host ""
    Write-Host "📝 Next Steps:" -ForegroundColor Cyan
    Write-Host "   1. Copy the environment variables above into your Portainer stack" -ForegroundColor White
    Write-Host "   2. Upload portainer-stack.yml to Portainer" -ForegroundColor White
    Write-Host "   3. Deploy the stack" -ForegroundColor White
    Write-Host "   4. Monitor container health and logs" -ForegroundColor White
    Write-Host "   5. Verify application accessibility" -ForegroundColor White
    Write-Host ""
    Write-Host "💡 Pro Tips:" -ForegroundColor Cyan
    Write-Host "   • Use the 'latest' branch for development deployments" -ForegroundColor White
    Write-Host "   • Use the 'main' branch for production deployments" -ForegroundColor White
    Write-Host "   • Monitor the application logs for any issues" -ForegroundColor White
    Write-Host "   • Test the health endpoints after deployment" -ForegroundColor White
    Write-Host ""
    Write-Success "Deployment preparation completed successfully!"
}

# Function to create deployment checklist
function New-DeploymentChecklist {
    Write-Header "✅ Creating Deployment Checklist"
    
    $checklistContent = @"
# Production Deployment Checklist

## Pre-Deployment
- [ ] Version information updated (v$script:GIT_COMMIT_COUNT.$script:GIT_COMMIT_HASH)
- [ ] All tests passing
- [ ] Database migrations reviewed
- [ ] Security settings verified
- [ ] Environment variables configured

## Portainer Configuration
- [ ] Stack file uploaded (portainer-stack.yml)
- [ ] Environment variables set:
  - [ ] GIT_COMMIT_COUNT=$script:GIT_COMMIT_COUNT
  - [ ] GIT_COMMIT_HASH=$script:GIT_COMMIT_HASH
  - [ ] GIT_BRANCH=$script:GIT_BRANCH
  - [ ] GIT_COMMIT_DATE=$script:GIT_COMMIT_DATE
  - [ ] Database credentials configured
  - [ ] Admin credentials configured
  - [ ] Domain settings configured

## Deployment
- [ ] Stack deployed successfully
- [ ] All containers showing as healthy
- [ ] No error messages in logs

## Post-Deployment Verification
- [ ] Health endpoint responding: /health/simple/
- [ ] Version endpoint working: /version/
- [ ] Admin panel accessible: /admin/
- [ ] Application fully functional
- [ ] SSL certificate working (if applicable)
- [ ] Database connectivity verified
- [ ] Redis connectivity verified
- [ ] Celery workers running
- [ ] Celery beat scheduler running

## Monitoring
- [ ] Container resource usage normal
- [ ] Application logs clean
- [ ] Error rates within acceptable limits
- [ ] Performance metrics satisfactory

---
**Deployment Date**: $(Get-Date)
**Version**: v$script:GIT_COMMIT_COUNT.$script:GIT_COMMIT_HASH
**Branch**: $script:GIT_BRANCH
"@

    Set-Content "DEPLOYMENT_CHECKLIST.md" -Value $checklistContent
    Write-Success "Deployment checklist created: DEPLOYMENT_CHECKLIST.md"
}

# Function to show help
function Show-Help {
    Write-Host "Production Portainer Deployment Script for Maintenance Dashboard" -ForegroundColor Green
    Write-Host ""
    Write-Host "Usage: .\scripts\portainer_deploy_production.ps1 [OPTIONS]" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Options:" -ForegroundColor Cyan
    Write-Host "  -SkipVersionUpdate    Skip updating version information" -ForegroundColor White
    Write-Host "  -SkipValidation       Skip production configuration validation" -ForegroundColor White
    Write-Host "  -Help                 Show this help message" -ForegroundColor White
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Cyan
    Write-Host "  .\scripts\portainer_deploy_production.ps1" -ForegroundColor White
    Write-Host "  .\scripts\portainer_deploy_production.ps1 -SkipVersionUpdate" -ForegroundColor White
    Write-Host "  .\scripts\portainer_deploy_production.ps1 -SkipValidation" -ForegroundColor White
    Write-Host ""
    Write-Host "This script will prepare your application for production deployment to Portainer." -ForegroundColor Yellow
}

# Main execution
function Main {
    if ($Help) {
        Show-Help
        return
    }
    
    Write-Header "🚀 Maintenance Dashboard - Production Portainer Deployment"
    Write-Host "This script will prepare your application for production deployment to Portainer"
    Write-Host ""
    
    # Check prerequisites
    Test-Prerequisites
    
    # Update version information
    Update-VersionInfo
    
    # Validate production configuration
    Test-ProductionConfig
    
    # Generate deployment summary
    Show-DeploymentSummary
    
    # Create deployment checklist
    New-DeploymentChecklist
    
    Write-Header "🎉 Deployment Preparation Complete!"
    Write-Host "Your application is ready for production deployment to Portainer."
    Write-Host "Follow the checklist in DEPLOYMENT_CHECKLIST.md for the deployment process."
    Write-Host ""
    Write-Host "Happy deploying! 🚀" -ForegroundColor Green
}

# Run main function
Main
