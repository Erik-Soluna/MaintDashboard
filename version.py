#!/usr/bin/env python3
"""
Version management for Maintenance Dashboard
Automatically generates version information from git
"""

import os
import subprocess
import re
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

def get_version_string():
    """Get a simple version string for display"""
    version_info = get_git_version()
    return version_info['version']

def get_full_version_info():
    """Get full version information"""
    return get_git_version()

# For direct execution
if __name__ == "__main__":
    version_info = get_git_version()
    print(f"Version: {version_info['version']}")
    print(f"Commit: {version_info['commit_hash']}")
    print(f"Branch: {version_info['branch']}")
    print(f"Date: {version_info['commit_date']}")
    print(f"Full: {version_info['full_version']}")
