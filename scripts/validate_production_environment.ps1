# Production Environment Validation Script for Maintenance Dashboard (PowerShell)
# This script validates that the production environment is properly configured
# Run this script to verify your production setup before deployment

param(
    [switch]$SkipSecurityCheck,
    [switch]$SkipVersionCheck,
    [switch]$Help
)

# Validation results
$script:ValidationPassed = $true
$script:IssuesFound = 0

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
    $script:IssuesFound++
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
    $script:ValidationPassed = $false
    $script:IssuesFound++
}

# Function to validate file exists and is readable
function Test-File {
    param(
        [string]$FilePath,
        [string]$Description
    )
    
    if (Test-Path $FilePath) {
        if ((Get-Item $FilePath).Attributes -notmatch "ReadOnly") {
            Write-Success "$Description`: $FilePath"
            return $true
        } else {
            Write-Error "$Description`: $FilePath (not readable)"
            return $false
        }
    } else {
        Write-Error "$Description`: $FilePath (not found)"
        return $false
    }
}

# Function to validate environment variables in file
function Test-EnvironmentVariables {
    param(
        [string]$FilePath,
        [string]$Description
    )
    
    if (-not (Test-Path $FilePath)) {
        Write-Error "$Description`: File not found"
        return $false
    }
    
    Write-Status "Validating environment variables in $FilePath"
    
    # Required environment variables
    $requiredVars = @(
        "GIT_COMMIT_COUNT",
        "GIT_COMMIT_HASH",
        "GIT_BRANCH",
        "GIT_COMMIT_DATE",
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD",
        "POSTGRES_PASSWORD",
        "SECRET_KEY",
        "ADMIN_USERNAME",
        "ADMIN_EMAIL",
        "ADMIN_PASSWORD"
    )
    
    $fileContent = Get-Content $FilePath -Raw
    $missingVars = @()
    
    foreach ($var in $requiredVars) {
        if (-not ($fileContent -match "$var=")) {
            $missingVars += $var
        }
    }
    
    if ($missingVars.Count -eq 0) {
        Write-Success "All required environment variables present"
    } else {
        Write-Error "Missing required environment variables: $($missingVars -join ', ')"
        return $false
    }
    
    # Validate specific values
    if ($fileContent -match "DEBUG=True") {
        Write-Warning "Debug mode is enabled in production environment"
    }
    
    if ($fileContent -match "SECURE_SSL_REDIRECT=False") {
        Write-Warning "SSL redirect is disabled in production environment"
    }
    
    # Check for default passwords
    if ($fileContent -match "temppass123|password123|admin123") {
        Write-Error "Default/weak passwords detected in environment file"
    }
    
    return $true
}

# Function to validate Docker Compose file
function Test-DockerCompose {
    param(
        [string]$FilePath,
        [string]$Description
    )
    
    if (-not (Test-Path $FilePath)) {
        Write-Error "$Description`: File not found"
        return $false
    }
    
    Write-Status "Validating Docker Compose file: $FilePath"
    
    # Check for required services
    $requiredServices = @("db", "redis", "web", "celery", "celery-beat")
    $fileContent = Get-Content $FilePath -Raw
    $missingServices = @()
    
    foreach ($service in $requiredServices) {
        if (-not ($fileContent -match "  $service`:")) {
            $missingServices += $service
        }
    }
    
    if ($missingServices.Count -eq 0) {
        Write-Success "All required services present"
    } else {
        Write-Error "Missing required services: $($missingServices -join ', ')"
        return $false
    }
    
    # Check for security settings
    if (-not ($fileContent -match "SECURE_SSL_REDIRECT=True")) {
        Write-Warning "SSL redirect not enabled"
    }
    
    # Check for debug mode (should be controlled by environment variable)
    if (-not ($fileContent -match "DEBUG=\$\{DEBUG:-False\}")) {
        Write-Warning "Debug mode not properly configured with environment variable"
    }
    
    # Check for health checks
    if (-not ($fileContent -match "healthcheck:")) {
        Write-Warning "Health checks not configured"
    }
    
    # Check for resource limits
    if (-not ($fileContent -match "deploy:")) {
        Write-Warning "Resource limits not configured"
    }
    
    return $true
}

# Function to validate Dockerfile
function Test-Dockerfile {
    param([string]$FilePath)
    
    if (-not (Test-Path $FilePath)) {
        Write-Error "Dockerfile not found"
        return $false
    }
    
    Write-Status "Validating Dockerfile: $FilePath"
    
    $fileContent = Get-Content $FilePath -Raw
    
    # Check for required build args
    if (-not ($fileContent -match "ARG GIT_COMMIT_COUNT")) {
        Write-Warning "GIT_COMMIT_COUNT build arg not found"
    }
    
    if (-not ($fileContent -match "ARG GIT_COMMIT_HASH")) {
        Write-Warning "GIT_COMMIT_HASH build arg not found"
    }
    
    # Check for security best practices
    if (-not ($fileContent -match "USER appuser")) {
        Write-Warning "Non-root user not configured (security best practice)"
    }
    
    # Check for health check
    if (-not ($fileContent -match "HEALTHCHECK")) {
        Write-Warning "Health check not configured in Dockerfile"
    }
    
    return $true
}

# Function to validate entrypoint script
function Test-EntrypointScript {
    param([string]$FilePath)
    
    if (-not (Test-Path $FilePath)) {
        Write-Error "Entrypoint script not found: $FilePath"
        return $false
    }
    
    Write-Status "Validating entrypoint script: $FilePath"
    
    $fileContent = Get-Content $FilePath -Raw
    
    # Check for required functions
    $requiredFunctions = @("check_database_ready", "ensure_database_exists", "run_database_initialization")
    $missingFunctions = @()
    
    foreach ($func in $requiredFunctions) {
        if (-not ($fileContent -match "$func\(\)")) {
            $missingFunctions += $func
        }
    }
    
    if ($missingFunctions.Count -eq 0) {
        Write-Success "All required functions present in entrypoint script"
    } else {
        Write-Error "Missing required functions: $($missingFunctions -join ', ')"
        return $false
    }
    
    return $true
}

# Function to validate version information
function Test-VersionInfo {
    if ($SkipVersionCheck) {
        Write-Warning "Skipping version check as requested"
        return $true
    }
    
    Write-Status "Validating version information"
    
    # Check version.json
    if (Test-Path "version.json") {
        try {
            $versionData = Get-Content "version.json" | ConvertFrom-Json
            Write-Success "version.json is valid JSON"
        } catch {
            Write-Error "version.json contains invalid JSON"
            return $false
        }
    } else {
        Write-Warning "version.json not found"
    }
    
    # Check if version information is up to date
    if ((Test-Path "version.json") -and (Get-Command git -ErrorAction SilentlyContinue)) {
        try {
            $currentCommit = git rev-parse --short HEAD
            $versionData = Get-Content "version.json" | ConvertFrom-Json
            $fileCommit = $versionData.commit_hash
            
            if ($currentCommit -eq $fileCommit) {
                Write-Success "Version information is up to date"
            } else {
                Write-Warning "Version information may be outdated (current: $currentCommit, file: $fileCommit)"
            }
        } catch {
            Write-Warning "Could not compare version information"
        }
    }
    
    return $true
}

# Function to validate security settings
function Test-Security {
    if ($SkipSecurityCheck) {
        Write-Warning "Skipping security check as requested"
        return $true
    }
    
    Write-Status "Validating security settings"
    
    $securityIssues = 0
    
    # Check for default secrets (exclude development files)
    $configFiles = Get-ChildItem -Path . -Include "*.yml", "*.yaml", "*.env", "*.template" -Recurse -ErrorAction SilentlyContinue
    foreach ($file in $configFiles) {
        # Skip development files
        if ($file.Name -match "docker-compose\.yml$" -and $file.Directory.Name -eq ".") {
            continue
        }
        
        $content = Get-Content $file.FullName -Raw -ErrorAction SilentlyContinue
        if ($content -match "django-insecure|temppass123|password123|admin123") {
            Write-Error "Default/weak secrets detected in configuration files: $($file.Name)"
            $securityIssues++
        }
    }
    
    # Check for exposed sensitive information
    foreach ($file in $configFiles) {
        $content = Get-Content $file.FullName -Raw -ErrorAction SilentlyContinue
        if ($content -match "password.*=" -and $content -notmatch "POSTGRES_PASSWORD|DB_PASSWORD|ADMIN_PASSWORD" -and $content -notmatch "SecureProdPassword|DevPassword") {
            Write-Warning "Potential password exposure in configuration files: $($file.Name)"
            $securityIssues++
        }
    }
    
    if ($securityIssues -eq 0) {
        Write-Success "No obvious security issues detected"
    }
    
    return $true
}

# Function to generate validation report
function Show-ValidationReport {
    Write-Header "📊 Validation Report"
    
    if ($script:ValidationPassed) {
        Write-Success "✅ Production environment validation PASSED"
        Write-Host ""
        Write-Host "Your production environment is properly configured and ready for deployment." -ForegroundColor Green
        Write-Host ""
        Write-Host "Next steps:" -ForegroundColor Cyan
        Write-Host "1. Run the deployment script: .\scripts\portainer_deploy_production.ps1" -ForegroundColor White
        Write-Host "2. Follow the deployment checklist" -ForegroundColor White
        Write-Host "3. Monitor the deployment process" -ForegroundColor White
    } else {
        Write-Error "❌ Production environment validation FAILED"
        Write-Host ""
        Write-Host "Found $script:IssuesFound issue(s) that need to be addressed before deployment." -ForegroundColor Red
        Write-Host ""
        Write-Host "Please fix the issues above and run this validation script again." -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Common fixes:" -ForegroundColor Cyan
        Write-Host "- Update environment variables with proper values" -ForegroundColor White
        Write-Host "- Enable security settings (SSL, debug mode off)" -ForegroundColor White
        Write-Host "- Replace default passwords with secure ones" -ForegroundColor White
        Write-Host "- Ensure all required files are present" -ForegroundColor White
    }
    
    Write-Host ""
    Write-Host "Validation completed at: $(Get-Date)" -ForegroundColor Gray
}

# Function to show help
function Show-Help {
    Write-Host "Production Environment Validation Script for Maintenance Dashboard" -ForegroundColor Green
    Write-Host ""
    Write-Host "Usage: .\scripts\validate_production_environment.ps1 [OPTIONS]" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Options:" -ForegroundColor Cyan
    Write-Host "  -SkipSecurityCheck    Skip security validation checks" -ForegroundColor White
    Write-Host "  -SkipVersionCheck     Skip version information validation" -ForegroundColor White
    Write-Host "  -Help                 Show this help message" -ForegroundColor White
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Cyan
    Write-Host "  .\scripts\validate_production_environment.ps1" -ForegroundColor White
    Write-Host "  .\scripts\validate_production_environment.ps1 -SkipSecurityCheck" -ForegroundColor White
    Write-Host "  .\scripts\validate_production_environment.ps1 -SkipVersionCheck" -ForegroundColor White
    Write-Host ""
    Write-Host "This script will validate your production environment configuration." -ForegroundColor Yellow
}

# Main execution
function Main {
    if ($Help) {
        Show-Help
        return
    }
    
    Write-Header "🔍 Production Environment Validation"
    Write-Host "This script will validate your production environment configuration"
    Write-Host ""
    
    # Validate required files
    Write-Header "📁 File Validation"
    Test-File "portainer-stack.yml" "Production stack file"
    Test-File "portainer.env.template" "Environment template file"
    Test-File "Dockerfile" "Docker build file"
    Test-File "scripts/deployment/docker-entrypoint.sh" "Container entrypoint script"
    
    # Validate environment configuration
    Write-Header "🔧 Environment Configuration"
    Test-EnvironmentVariables "portainer.env.template" "Environment template"
    
    # Validate Docker configuration
    Write-Header "🐳 Docker Configuration"
    Test-DockerCompose "portainer-stack.yml" "Production stack"
    Test-Dockerfile "Dockerfile"
    Test-EntrypointScript "scripts/deployment/docker-entrypoint.sh"
    
    # Validate version information
    Write-Header "📊 Version Information"
    Test-VersionInfo
    
    # Validate security settings
    Write-Header "🔒 Security Validation"
    Test-Security
    
    # Generate final report
    Show-ValidationReport
    
    # Exit with appropriate code
    if ($script:ValidationPassed) {
        exit 0
    } else {
        exit 1
    }
}

# Run main function
Main
