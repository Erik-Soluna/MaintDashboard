"""
URL-based version information extractor for Maintenance Dashboard
Supports GitHub, GitLab, and other git providers
"""

import re
import requests
import json
from urllib.parse import urlparse, parse_qs
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class URLVersionExtractor:
    """Extract version information from various git provider URLs"""
    
    def __init__(self):
        self.github_api_base = "https://api.github.com"
        self.gitlab_api_base = "https://gitlab.com/api/v4"
        
    def extract_from_url(self, url):
        """
        Extract version information from a URL
        Supports:
        - GitHub commit URLs
        - GitHub repository URLs (gets latest commit)
        - GitHub branch URLs (gets latest commit from specific branch)
        - GitLab commit URLs
        - GitLab repository URLs (gets latest commit)
        """
        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.lower()
            
            if 'github.com' in domain:
                return self._extract_from_github(url, parsed_url)
            elif 'gitlab.com' in domain:
                return self._extract_from_gitlab(url, parsed_url)
            else:
                return {
                    'error': f'Unsupported git provider: {domain}',
                    'supported': ['github.com', 'gitlab.com']
                }
                
        except Exception as e:
            logger.error(f"Error extracting version from URL {url}: {str(e)}")
            return {
                'error': f'Failed to extract version from URL: {str(e)}'
            }
    
    def _extract_from_github(self, url, parsed_url):
        """Extract version information from GitHub URLs"""
        try:
            path_parts = parsed_url.path.strip('/').split('/')
            
            if len(path_parts) < 2:
                return {'error': 'Invalid GitHub URL format'}
            
            owner = path_parts[0]
            repo = path_parts[1]
            
            # Check if it's a specific commit URL
            if len(path_parts) >= 4 and path_parts[2] == 'commit':
                commit_hash = path_parts[3][:7]  # Take first 7 characters
                return self._get_github_commit_info(owner, repo, commit_hash)
            
            # Check if it's a tree/branch URL (e.g., /tree/latest, /tree/main)
            elif len(path_parts) >= 4 and path_parts[2] == 'tree':
                branch = path_parts[3]
                return self._get_github_latest_commit(owner, repo, branch)
            
            # Check if it's a branch URL (e.g., /latest, /main, /develop)
            elif len(path_parts) >= 3 and path_parts[2] not in ['commit', 'tree', 'blob', 'issues', 'pulls']:
                branch = path_parts[2]
                return self._get_github_latest_commit(owner, repo, branch)
            
            # Default to main/master branch
            else:
                return self._get_github_latest_commit(owner, repo, 'main')
                
        except Exception as e:
            logger.error(f"Error extracting from GitHub URL: {str(e)}")
            return {'error': f'GitHub extraction failed: {str(e)}'}
    
    def _get_github_commit_info(self, owner, repo, commit_hash):
        """Get specific commit information from GitHub API"""
        try:
            # Get commit details
            commit_url = f"{self.github_api_base}/repos/{owner}/{repo}/commits/{commit_hash}"
            response = requests.get(commit_url, timeout=10)
            
            if response.status_code != 200:
                return {'error': f'GitHub API error: {response.status_code}'}
            
            commit_data = response.json()
            
            # Get total commit count more accurately
            commit_count = self._get_accurate_commit_count(owner, repo)
            
            # Extract branch name (try to get from commit or use 'main')
            branch = self._get_branch_for_commit(owner, repo, commit_hash)
            
            # Parse commit date
            commit_date = datetime.fromisoformat(
                commit_data['commit']['committer']['date'].replace('Z', '+00:00')
            ).strftime('%Y-%m-%d')
            
            return {
                'commit_count': commit_count,
                'commit_hash': commit_data['sha'][:7],
                'branch': branch,
                'commit_date': commit_date,
                'version': f"v{commit_count}.{commit_data['sha'][:7]}",
                'full_version': f"v{commit_count}.{commit_data['sha'][:7]} ({branch}) - {commit_date}",
                'source_url': f"https://github.com/{owner}/{repo}/commit/{commit_data['sha']}",
                'commit_message': commit_data['commit']['message'].split('\n')[0][:100]
            }
            
        except Exception as e:
            logger.error(f"Error getting GitHub commit info: {str(e)}")
            return {'error': f'Failed to get GitHub commit info: {str(e)}'}
    
    def _get_github_latest_commit(self, owner, repo, branch='main'):
        """Get latest commit information from GitHub API"""
        try:
            # Try the specified branch first, then fallback to main/master
            branches_to_try = [branch] if branch != 'main' else ['main', 'master']
            
            for branch_name in branches_to_try:
                try:
                    commits_url = f"{self.github_api_base}/repos/{owner}/{repo}/commits"
                    response = requests.get(commits_url, params={'sha': branch_name, 'per_page': 1}, timeout=10)
                    
                    if response.status_code == 200:
                        commits_data = response.json()
                        if commits_data:
                            latest_commit = commits_data[0]
                            return self._get_github_commit_info(owner, repo, latest_commit['sha'])
                            
                except Exception:
                    continue
            
            return {'error': f'Could not find branch {branch} or main/master in repository'}
            
        except Exception as e:
            logger.error(f"Error getting GitHub latest commit: {str(e)}")
            return {'error': f'Failed to get GitHub latest commit: {str(e)}'}
    
    def _get_accurate_commit_count(self, owner, repo):
        """Get accurate commit count from GitHub API"""
        try:
            # Try to get from repository statistics first
            repo_url = f"{self.github_api_base}/repos/{owner}/{repo}"
            response = requests.get(repo_url, timeout=10)
            
            if response.status_code == 200:
                repo_data = response.json()
                # GitHub provides default_branch info
                default_branch = repo_data.get('default_branch', 'main')
                
                # Get commit count for the default branch
                commits_url = f"{self.github_api_base}/repos/{owner}/{repo}/commits"
                commits_response = requests.get(commits_url, params={'sha': default_branch, 'per_page': 1}, timeout=10)
                
                if commits_response.status_code == 200:
                    # Try to get from link header for accurate count
                    link_header = commits_response.headers.get('link', '')
                    if 'rel="last"' in link_header:
                        last_page_match = re.search(r'page=(\d+)>; rel="last"', link_header)
                        if last_page_match:
                            last_page = int(last_page_match.group(1))
                            # Get the last page to see how many commits are on it
                            last_page_response = requests.get(commits_url, params={'sha': default_branch, 'page': last_page, 'per_page': 100}, timeout=10)
                            if last_page_response.status_code == 200:
                                last_page_commits = last_page_response.json()
                                total_commits = (last_page - 1) * 100 + len(last_page_commits)
                                return max(1, total_commits)
                    
                    # Fallback: estimate from repository age
                    created_at = datetime.fromisoformat(repo_data['created_at'].replace('Z', '+00:00'))
                    days_old = (datetime.now().replace(tzinfo=created_at.tzinfo) - created_at).days
                    return max(1, days_old // 3)  # Rough estimate: 1 commit per 3 days
            
            return 1  # Fallback
            
        except Exception:
            return 1  # Default fallback
    
    def _get_branch_for_commit(self, owner, repo, commit_hash):
        """Try to determine which branch a commit belongs to"""
        try:
            # Get branches containing this commit
            branches_url = f"{self.github_api_base}/repos/{owner}/{repo}/commits/{commit_hash}/branches-where-head"
            response = requests.get(branches_url, timeout=10)
            
            if response.status_code == 200:
                branches = response.json()
                if branches:
                    # Prefer main/master, otherwise take the first one
                    for branch in branches:
                        if branch['name'] in ['main', 'master']:
                            return branch['name']
                    return branches[0]['name']
            
            return 'main'  # Default fallback
            
        except Exception:
            return 'main'  # Default fallback
    
    def _extract_from_gitlab(self, url, parsed_url):
        """Extract version information from GitLab URLs"""
        try:
            path_parts = parsed_url.path.strip('/').split('/')
            
            if len(path_parts) < 2:
                return {'error': 'Invalid GitLab URL format'}
            
            # GitLab URLs can have groups, so we need to be more flexible
            project_path = '/'.join(path_parts[:2])  # Simplified for now
            
            # Check if it's a specific commit URL
            if 'commit' in path_parts:
                commit_index = path_parts.index('commit')
                if commit_index + 1 < len(path_parts):
                    commit_hash = path_parts[commit_index + 1][:7]
                    return self._get_gitlab_commit_info(project_path, commit_hash)
            
            # Default to main branch
            return self._get_gitlab_latest_commit(project_path, 'main')
            
        except Exception as e:
            logger.error(f"Error extracting from GitLab URL: {str(e)}")
            return {'error': f'GitLab extraction failed: {str(e)}'}
    
    def _get_gitlab_commit_info(self, project_path, commit_hash):
        """Get specific commit information from GitLab API"""
        try:
            # Encode project path for URL
            encoded_project = requests.utils.quote(project_path, safe='')
            commit_url = f"{self.gitlab_api_base}/projects/{encoded_project}/repository/commits/{commit_hash}"
            
            response = requests.get(commit_url, timeout=10)
            
            if response.status_code != 200:
                return {'error': f'GitLab API error: {response.status_code}'}
            
            commit_data = response.json()
            
            # Estimate commit count (GitLab doesn't provide this easily)
            commit_count = self._estimate_gitlab_commit_count(encoded_project)
            
            # Parse commit date
            commit_date = datetime.fromisoformat(
                commit_data['committed_date'].replace('Z', '+00:00')
            ).strftime('%Y-%m-%d')
            
            return {
                'commit_count': commit_count,
                'commit_hash': commit_data['id'][:7],
                'branch': 'main',  # Simplified
                'commit_date': commit_date,
                'version': f"v{commit_count}.{commit_data['id'][:7]}",
                'full_version': f"v{commit_count}.{commit_data['id'][:7]} (main) - {commit_date}",
                'source_url': commit_data['web_url'],
                'commit_message': commit_data['message'].split('\n')[0][:100]
            }
            
        except Exception as e:
            logger.error(f"Error getting GitLab commit info: {str(e)}")
            return {'error': f'Failed to get GitLab commit info: {str(e)}'}
    
    def _get_gitlab_latest_commit(self, project_path, branch='main'):
        """Get latest commit information from GitLab API"""
        try:
            encoded_project = requests.utils.quote(project_path, safe='')
            commits_url = f"{self.gitlab_api_base}/projects/{encoded_project}/repository/commits"
            
            response = requests.get(commits_url, params={'ref_name': branch, 'per_page': 1}, timeout=10)
            
            if response.status_code == 200:
                commits_data = response.json()
                if commits_data:
                    latest_commit = commits_data[0]
                    return self._get_gitlab_commit_info(project_path, latest_commit['id'])
            
            return {'error': f'Could not find branch {branch} in repository'}
            
        except Exception as e:
            logger.error(f"Error getting GitLab latest commit: {str(e)}")
            return {'error': f'Failed to get GitLab latest commit: {str(e)}'}
    
    def _estimate_gitlab_commit_count(self, encoded_project):
        """Estimate commit count for GitLab (simplified)"""
        try:
            # Get project info for creation date
            project_url = f"{self.gitlab_api_base}/projects/{encoded_project}"
            response = requests.get(project_url, timeout=10)
            
            if response.status_code == 200:
                project_data = response.json()
                created_at = datetime.fromisoformat(project_data['created_at'].replace('Z', '+00:00'))
                days_old = (datetime.now().replace(tzinfo=created_at.tzinfo) - created_at).days
                return max(1, days_old // 7)  # Rough estimate
            
            return 1
            
        except Exception:
            return 1

# Example usage and URL patterns
def get_example_urls():
    """Return example URLs that can be used for testing"""
    return {
        'github_commit': 'https://github.com/user/repo/commit/abc1234567890',
        'github_repo': 'https://github.com/user/repo',
        'github_branch': 'https://github.com/user/repo/tree/develop',
        'github_branch_simple': 'https://github.com/user/repo/latest',
        'gitlab_commit': 'https://gitlab.com/user/repo/-/commit/abc1234567890',
        'gitlab_repo': 'https://gitlab.com/user/repo'
    }
