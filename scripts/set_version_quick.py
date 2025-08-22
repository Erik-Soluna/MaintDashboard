#!/usr/bin/env python3
"""
Quick script to set version information for Maintenance Dashboard
Usage: python scripts/set_version_quick.py <commit_count> <commit_hash> <branch> <commit_date>
Example: python scripts/set_version_quick.py 123 abc1234 main 2024-01-15
"""

import sys
import os
import json
from datetime import datetime

def set_version(commit_count, commit_hash, branch, commit_date):
    """Set version information and create necessary files"""
    
    # Create version data
    version_data = {
        'commit_count': int(commit_count),
        'commit_hash': commit_hash,
        'branch': branch,
        'commit_date': commit_date,
        'version': f'v{commit_count}.{commit_hash}',
        'full_version': f'v{commit_count}.{commit_hash} ({branch}) - {commit_date}'
    }
    
    # Update version.json
    with open('version.json', 'w') as f:
        json.dump(version_data, f, indent=2)
    
    # Update .env file
    env_content = f"""# Version Information (Auto-generated)
GIT_COMMIT_COUNT={commit_count}
GIT_COMMIT_HASH={commit_hash}
GIT_BRANCH={branch}
GIT_COMMIT_DATE={commit_date}

# Other environment variables can be added below
"""
    
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print(f"✅ Version set successfully!")
    print(f"📝 Version: {version_data['version']}")
    print(f"📝 Commit: {commit_hash}")
    print(f"📝 Branch: {branch}")
    print(f"📝 Date: {commit_date}")
    print(f"📝 Full: {version_data['full_version']}")
    print()
    print("🌐 For Portainer deployment, use these environment variables:")
    print(f"   GIT_COMMIT_COUNT={commit_count}")
    print(f"   GIT_COMMIT_HASH={commit_hash}")
    print(f"   GIT_BRANCH={branch}")
    print(f"   GIT_COMMIT_DATE={commit_date}")
    print()
    print("💡 Copy these values into your Portainer stack environment variables!")
    print("🔄 The web application will now show the updated version information.")

def main():
    if len(sys.argv) != 5:
        print("Usage: python scripts/set_version_quick.py <commit_count> <commit_hash> <branch> <commit_date>")
        print("Example: python scripts/set_version_quick.py 123 abc1234 main 2024-01-15")
        sys.exit(1)
    
    commit_count = sys.argv[1]
    commit_hash = sys.argv[2]
    branch = sys.argv[3]
    commit_date = sys.argv[4]
    
    # Validate inputs
    try:
        int(commit_count)
    except ValueError:
        print("❌ Error: commit_count must be a number")
        sys.exit(1)
    
    if len(commit_hash) != 7:
        print("❌ Error: commit_hash must be exactly 7 characters")
        sys.exit(1)
    
    try:
        datetime.strptime(commit_date, '%Y-%m-%d')
    except ValueError:
        print("❌ Error: commit_date must be in YYYY-MM-DD format")
        sys.exit(1)
    
    # Set the version
    set_version(commit_count, commit_hash, branch, commit_date)

if __name__ == "__main__":
    main()
