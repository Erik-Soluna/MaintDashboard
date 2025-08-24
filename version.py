#!/usr/bin/env python3
"""
Unified Version Management for Maintenance Dashboard
Automatically generates version information from git and manages version files
"""

import os
import subprocess
import re
import json
import sys
from datetime import datetime

def get_git_version():
    """Get version information from git repository"""
    try:
        # Get the current working directory
        repo_path = os.path.dirname(os.path.abspath(__file__))
        
        # Change to the repository directory
        os.chdir(repo_path)
        
        # Get commit count (total number of commits)
        commit_count = subprocess.check_output(
            ['git', 'rev-list', '--count', 'HEAD'], 
            stderr=subprocess.STDOUT,
            universal_newlines=True
        ).strip()
        
        # Get short commit hash
        commit_hash = subprocess.check_output(
            ['git', 'rev-parse', '--short', 'HEAD'],
            stderr=subprocess.STDOUT,
            universal_newlines=True
        ).strip()
        
        # Get current branch
        branch = subprocess.check_output(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            stderr=subprocess.STDOUT,
            universal_newlines=True
        ).strip()
        
        # Get last commit date
        commit_date = subprocess.check_output(
            ['git', 'log', '-1', '--format=%cd', '--date=short'],
            stderr=subprocess.STDOUT,
            universal_newlines=True
        ).strip()
        
        # Get tag if available
        try:
            tag = subprocess.check_output(
                ['git', 'describe', '--tags', '--abbrev=0'],
                stderr=subprocess.STDOUT,
                universal_newlines=True
            ).strip()
        except subprocess.CalledProcessError:
            tag = None
        
        return {
            'version': f"v{commit_count}.{commit_hash}",
            'commit_count': int(commit_count),
            'commit_hash': commit_hash,
            'branch': branch,
            'commit_date': commit_date,
            'tag': tag,
            'full_version': f"v{commit_count}.{commit_hash} ({branch}) - {commit_date}"
        }
        
    except (subprocess.CalledProcessError, FileNotFoundError, OSError) as e:
        # Check for environment variables (useful for Docker builds)
        commit_count = os.environ.get('GIT_COMMIT_COUNT', '0')
        commit_hash = os.environ.get('GIT_COMMIT_HASH', 'unknown')
        branch = os.environ.get('GIT_BRANCH', 'unknown')
        commit_date = os.environ.get('GIT_COMMIT_DATE', datetime.now().strftime('%Y-%m-%d'))
        
        if commit_hash != 'unknown':
            # We have some git info from environment
            return {
                'version': f"v{commit_count}.{commit_hash}",
                'commit_count': int(commit_count),
                'commit_hash': commit_hash,
                'branch': branch,
                'commit_date': commit_date,
                'tag': None,
                'full_version': f"v{commit_count}.{commit_hash} ({branch}) - {commit_date}"
            }
        else:
            # Fallback if no git info available
            return {
                'version': 'v0.0.0',
                'commit_count': 0,
                'commit_hash': 'unknown',
                'branch': 'unknown',
                'commit_date': datetime.now().strftime('%Y-%m-%d'),
                'tag': None,
                'full_version': 'v0.0.0 (unknown) - Development'
            }

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
    
    # Update .env file in root directory
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
    
    return version_data

def get_version_string():
    """Get a simple version string for display"""
    version_info = get_git_version()
    return version_info['version']

def get_full_version_info():
    """Get full version information"""
    return get_git_version()

def update_version_files():
    """Update version.json and .env files with current git information"""
    version_info = get_git_version()
    return set_version(
        version_info['commit_count'],
        version_info['commit_hash'],
        version_info['branch'],
        version_info['commit_date']
    )

# For direct execution
if __name__ == "__main__":
    if len(sys.argv) == 5:
        # Command line usage: python version.py <commit_count> <commit_hash> <branch> <commit_date>
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
        
    elif len(sys.argv) == 1:
        # No arguments - just display current version info
        version_info = get_git_version()
        print(f"Version: {version_info['version']}")
        print(f"Commit: {version_info['commit_hash']}")
        print(f"Branch: {version_info['branch']}")
        print(f"Date: {version_info['commit_date']}")
        print(f"Full: {version_info['full_version']}")
        
    elif len(sys.argv) == 2 and sys.argv[1] == '--update':
        # Update version files with current git info
        update_version_files()
        
    else:
        print("Usage:")
        print("  python version.py                                    # Display current version")
        print("  python version.py --update                          # Update version files from git")
        print("  python version.py <count> <hash> <branch> <date>    # Set specific version")
        print("Example: python version.py 123 abc1234 main 2024-01-15")
