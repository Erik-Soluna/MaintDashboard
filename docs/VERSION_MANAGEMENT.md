# Version Management System

The Maintenance Dashboard now includes a comprehensive version management system that allows you to easily set and update version information without manual file editing.

## Quick Start

### Option 1: Web Interface (Recommended)
1. Go to **Settings** → **Set Version** in the web application
2. **🆕 EASY WAY**: Paste a GitHub/GitLab URL to automatically extract version info!
   - Paste any GitHub or GitLab URL (commit, repository, branch)
   - Click **Extract** to automatically fill in all fields
   - Click **Quick Set Version** to immediately apply
3. **Manual Way**: Fill in the version information manually:
   - **Commit Count**: Total number of commits (e.g., 123)
   - **Commit Hash**: 7-character commit hash (e.g., abc1234)
   - **Branch**: Branch name (e.g., main, develop)
   - **Commit Date**: Date in YYYY-MM-DD format (e.g., 2024-01-15)
4. Click **Set Version**
5. The system will automatically update all version files and refresh the display

### Option 2: Command Line Scripts

#### Windows Batch File
```batch
scripts\set_version.bat 123 abc1234 main 2024-01-15
```

#### PowerShell Script
```powershell
.\scripts\set_version.ps1 123 abc1234 main 2024-01-15
```

#### Python Script
```bash
python scripts/set_version_quick.py 123 abc1234 main 2024-01-15
```

### Option 3: Django Management Command
```bash
# 🆕 From URL (GitHub/GitLab)
docker exec maintenance_web python manage.py set_version --url "https://github.com/user/repo/commit/abc123"

# Inside Docker container
docker exec maintenance_web python manage.py set_version --commit-count 123 --commit-hash abc1234 --branch main --commit-date 2024-01-15

# Manual input mode
docker exec maintenance_web python manage.py set_version --manual
```

### Option 4: API Endpoint
```bash
# 🆕 Extract from URL
curl -X POST http://localhost:4405/version/extract/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: <your-csrf-token>" \
  -d '{"url": "https://github.com/user/repo/commit/abc123", "auto_set": true}'

# Manual version setting
curl -X POST http://localhost:4405/version/set/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: <your-csrf-token>" \
  -d '{
    "commit_count": "123",
    "commit_hash": "abc1234",
    "branch": "main",
    "commit_date": "2024-01-15"
  }'
```

## What Gets Updated

When you set version information, the system automatically updates:

1. **`version.json`** - Contains all version data in JSON format
2. **`.env`** - Environment variables for Docker/Portainer deployment
3. **Web Application Display** - Version information shown in the dashboard

## Version Format

The system uses the following version format:
- **Short Version**: `v{commit_count}.{commit_hash}` (e.g., v123.abc1234)
- **Full Version**: `v{commit_count}.{commit_hash} ({branch}) - {commit_date}` (e.g., v123.abc1234 (main) - 2024-01-15)

## 🆕 URL-Based Extraction

The system now supports automatic version extraction from GitHub and GitLab URLs!

### Supported URL Types
- **GitHub commit**: `https://github.com/user/repo/commit/abc123456`
- **GitHub repository**: `https://github.com/user/repo` (gets latest commit)
- **GitHub branch**: `https://github.com/user/repo/tree/develop`
- **GitLab commit**: `https://gitlab.com/user/repo/-/commit/abc123456`
- **GitLab repository**: `https://gitlab.com/user/repo` (gets latest commit)

### How It Works
1. Paste any supported URL
2. System automatically calls GitHub/GitLab API
3. Extracts commit hash, branch, date, and estimates commit count
4. Populates all version fields automatically
5. Option to immediately set the version or review first

### Benefits
- **No manual copying** of commit hashes or dates
- **Always accurate** - pulls directly from git provider
- **Includes commit message** for reference
- **Estimates commit count** automatically
- **Links back to source** for verification

## Portainer Integration

For Portainer deployments, the system automatically generates the environment variables you need:

```env
GIT_COMMIT_COUNT=123
GIT_COMMIT_HASH=abc1234
GIT_BRANCH=main
GIT_COMMIT_DATE=2024-01-15
```

Simply copy these values into your Portainer stack environment variables.

## Celery Tasks

The system includes Celery tasks for automated version management:

- **`update_version_info`** - Automatically updates version from git (when available)
- **`set_manual_version`** - Sets version information manually via Celery

## Troubleshooting

### Version Error: "Failed to get version information"
This error typically occurs when there's a conflict with the `version` module import. The system now uses `importlib` to avoid these conflicts.

### Git Not Available in Container
If you're running in a Docker container without git access, use the manual version setting options instead of the automatic git detection.

### Permission Issues
Make sure the web application has write permissions to the project directory for creating/updating version files.

## File Locations

- **Version Form**: `/version/form/`
- **Version API**: `/version/set/`
- **Version Info**: `/version/html/`
- **Version Files**: `version.json` and `.env` in project root

## Examples

### Setting a Development Version
```bash
.\scripts\set_version.ps1 456 def5678 develop 2024-01-16
```

### Setting a Feature Branch Version
```bash
.\scripts\set_version.ps1 789 ghi9012 feature 2024-01-17
```

### Setting a Production Release
```bash
.\scripts\set_version.ps1 1000 jkl3456 main 2024-01-18
```

## Benefits

1. **No More Manual File Editing** - Set version info with a single command or web form
2. **Automatic Updates** - All version files are updated simultaneously
3. **Portainer Ready** - Environment variables are automatically generated
4. **Multiple Interfaces** - Choose from web form, command line, or API
5. **Error Prevention** - Input validation prevents invalid version data
6. **Immediate Effect** - Version changes are reflected immediately in the web application

## Support

If you encounter any issues with the version management system, check the Django logs and ensure all required files have proper permissions.
