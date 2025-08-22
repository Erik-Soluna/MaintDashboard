# Quick script to set version information for Maintenance Dashboard
# Usage: .\set_version.ps1 <commit_count> <commit_hash> <branch> <commit_date>
# Example: .\set_version.ps1 123 abc1234 main 2024-01-15

param(
    [Parameter(Mandatory=$true)]
    [string]$commit_count,
    
    [Parameter(Mandatory=$true)]
    [string]$commit_hash,
    
    [Parameter(Mandatory=$true)]
    [string]$branch,
    
    [Parameter(Mandatory=$true)]
    [string]$commit_date
)

# Validate inputs
if ($commit_count -notmatch '^\d+$') {
    Write-Error "❌ Error: commit_count must be a number"
    exit 1
}

if ($commit_hash.Length -ne 7) {
    Write-Error "❌ Error: commit_hash must be exactly 7 characters"
    exit 1
}

try {
    [DateTime]::ParseExact($commit_date, 'yyyy-MM-dd', $null)
} catch {
    Write-Error "❌ Error: commit_date must be in YYYY-MM-DD format"
    exit 1
}

Write-Host "Setting version information..." -ForegroundColor Green
Write-Host "Commit Count: $commit_count"
Write-Host "Commit Hash: $commit_hash"
Write-Host "Branch: $branch"
Write-Host "Commit Date: $commit_date"
Write-Host ""

# Create version data
$version_data = @{
    commit_count = [int]$commit_count
    commit_hash = $commit_hash
    branch = $branch
    commit_date = $commit_date
    version = "v$commit_count.$commit_hash"
    full_version = "v$commit_count.$commit_hash ($branch) - $commit_date"
}

# Update version.json
$version_data | ConvertTo-Json -Depth 10 | Set-Content "version.json"

# Update .env file
$env_content = @"
# Version Information (Auto-generated)
GIT_COMMIT_COUNT=$commit_count
GIT_COMMIT_HASH=$commit_hash
GIT_BRANCH=$branch
GIT_COMMIT_DATE=$commit_date

# Other environment variables can be added below
"@

$env_content | Set-Content ".env"

Write-Host "✅ Version set successfully!" -ForegroundColor Green
Write-Host "📝 Version: $($version_data.version)"
Write-Host "📝 Commit: $commit_hash"
Write-Host "📝 Branch: $branch"
Write-Host "📝 Date: $commit_date"
Write-Host "📝 Full: $($version_data.full_version)"
Write-Host ""
Write-Host "🌐 For Portainer deployment, use these environment variables:" -ForegroundColor Cyan
Write-Host "   GIT_COMMIT_COUNT=$commit_count"
Write-Host "   GIT_COMMIT_HASH=$commit_hash"
Write-Host "   GIT_BRANCH=$branch"
Write-Host "   GIT_COMMIT_DATE=$commit_date"
Write-Host ""
Write-Host "💡 Copy these values into your Portainer stack environment variables!" -ForegroundColor Yellow
Write-Host "🔄 The web application will now show the updated version information." -ForegroundColor Green
