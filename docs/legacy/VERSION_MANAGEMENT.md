# Version Management for Maintenance Dashboard

This document explains how to use the unified version management system for the Maintenance Dashboard project.

## Overview

The version management system has been unified into a single `version.py` file that handles:
- Reading version information from git
- Setting specific version information
- Updating version files automatically
- Managing environment variables for Docker deployments

## Usage

### Display Current Version
```bash
python version.py
```
This shows the current version information from git or environment variables.

### Update Version Files from Git
```bash
python version.py --update
```
This automatically updates `version.json` and `.env` files with current git information.

### Set Specific Version
```bash
python version.py <commit_count> <commit_hash> <branch> <commit_date>
```
Example:
```bash
python version.py 289 65462d3 latest 2025-08-23
```

## Files Generated

### version.json
Contains version information in JSON format:
```json
{
  "commit_count": 289,
  "commit_hash": "65462d3",
  "branch": "latest",
  "commit_date": "2025-08-23",
  "version": "v289.65462d3",
  "full_version": "v289.65462d3 (latest) - 2025-08-23"
}
```

### .env
Contains environment variables for Docker deployments:
```bash
# Version Information (Auto-generated)
GIT_COMMIT_COUNT=289
GIT_COMMIT_HASH=65462d3
GIT_BRANCH=latest
GIT_COMMIT_DATE=2025-08-23
```

## Docker Deployment

For Portainer deployments, copy the environment variables from the `.env` file into your stack configuration. The web application will automatically display the correct version information.

## Fallback Behavior

If git information is not available (e.g., in Docker containers), the system will:
1. Check for environment variables
2. Fall back to default values if none are found

## Integration

The version information is automatically available in Django views through the `version.py` module:
```python
from version import get_version_string, get_full_version_info

version = get_version_string()
full_info = get_full_version_info()
```

## Migration from Old System

The old `set_version_quick.py` script has been removed. All functionality is now available in the unified `version.py` file.
