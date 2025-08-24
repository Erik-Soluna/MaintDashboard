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

Write-Host "Setting version information using unified version.py..." -ForegroundColor Green
Write-Host "Commit Count: $commit_count"
Write-Host "Commit Hash: $commit_hash"
Write-Host "Branch: $branch"
Write-Host "Commit Date: $commit_date"
Write-Host ""

# Use the unified version.py script
try {
    python version.py $commit_count $commit_hash $branch $commit_date
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Version set successfully using unified system!" -ForegroundColor Green
    } else {
        Write-Error "❌ Failed to set version using unified system"
        exit 1
    }
} catch {
    Write-Error "❌ Error running unified version.py: $_"
    exit 1
}
