"""
Management command to set version information.
Usage: python manage.py set_version
"""

from django.core.management.base import BaseCommand
from django.conf import settings
import os
import subprocess
import json


class Command(BaseCommand):
    help = 'Set version information from git or manual input'

    def add_arguments(self, parser):
        parser.add_argument(
            '--manual',
            action='store_true',
            help='Manually input version information',
        )
        parser.add_argument(
            '--commit-count',
            type=int,
            help='Manual commit count',
        )
        parser.add_argument(
            '--commit-hash',
            type=str,
            help='Manual commit hash',
        )
        parser.add_argument(
            '--branch',
            type=str,
            help='Manual branch name',
        )
        parser.add_argument(
            '--commit-date',
            type=str,
            help='Manual commit date (YYYY-MM-DD)',
        )
        parser.add_argument(
            '--url',
            type=str,
            help='Extract version info from GitHub/GitLab URL',
        )

    def handle(self, *args, **options):
        if options['url']:
            self.set_version_from_url(options['url'])
        elif options['manual'] or any([options['commit_count'], options['commit_hash'], options['branch'], options['commit_date']]):
            self.set_manual_version(options)
        else:
            self.set_git_version()

    def set_git_version(self):
        """Set version from git repository"""
        try:
            # Get git information
            commit_count = subprocess.check_output(['git', 'rev-list', '--count', 'HEAD'], text=True).strip()
            commit_hash = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'], text=True).strip()
            branch = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], text=True).strip()
            commit_date = subprocess.check_output(['git', 'log', '-1', '--format=%cd', '--date=short'], text=True).strip()
            
            # Set environment variables
            self.set_env_vars(commit_count, commit_hash, branch, commit_date)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Version set from git: v{commit_count}.{commit_hash} ({branch}) - {commit_date}'
                )
            )
            
        except subprocess.CalledProcessError:
            self.stdout.write(
                self.style.WARNING(
                    '⚠️  Git not available or not a git repository. Use --manual flag.'
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error getting git version: {str(e)}')
            )

    def set_manual_version(self, options):
        """Set version manually"""
        try:
            # Get values from options or prompt user
            commit_count = options['commit_count'] or input('Enter commit count: ')
            commit_hash = options['commit_hash'] or input('Enter commit hash (7 chars): ')
            branch = options['branch'] or input('Enter branch name: ')
            commit_date = options['commit_date'] or input('Enter commit date (YYYY-MM-DD): ')
            
            # Validate inputs
            if not all([commit_count, commit_hash, branch, commit_date]):
                self.stdout.write(
                    self.style.ERROR('❌ All fields are required')
                )
                return
            
            # Set environment variables
            self.set_env_vars(commit_count, commit_hash, branch, commit_date)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Version set manually: v{commit_count}.{commit_hash} ({branch}) - {commit_date}'
                )
            )
            
        except KeyboardInterrupt:
            self.stdout.write('\n❌ Operation cancelled')
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error setting manual version: {str(e)}')
            )

    def set_env_vars(self, commit_count, commit_hash, branch, commit_date):
        """Set environment variables for versioning"""
        # Create or update .env file
        env_file = '.env'
        env_content = f"""# Version Information (Auto-generated)
GIT_COMMIT_COUNT={commit_count}
GIT_COMMIT_HASH={commit_hash}
GIT_BRANCH={branch}
GIT_COMMIT_DATE={commit_date}

# Other environment variables can be added below
"""
        
        # Write to .env file
        with open(env_file, 'w') as f:
            f.write(env_content)
        
        # Also create a version.json file for easy access
        version_data = {
            'commit_count': int(commit_count),
            'commit_hash': commit_hash,
            'branch': branch,
            'commit_date': commit_date,
            'version': f'v{commit_count}.{commit_hash}',
            'full_version': f'v{commit_count}.{commit_hash} ({branch}) - {commit_date}'
        }
        
        with open('version.json', 'w') as f:
            json.dump(version_data, f, indent=2)
        
        self.stdout.write(
            self.style.SUCCESS(f'📝 Version info written to {env_file} and version.json')
        )
        
        # Show Portainer instructions
        self.stdout.write('\n🌐 For Portainer deployment, use these environment variables:')
        self.stdout.write(f'   GIT_COMMIT_COUNT={commit_count}')
        self.stdout.write(f'   GIT_COMMIT_HASH={commit_hash}')
        self.stdout.write(f'   GIT_BRANCH={branch}')
        self.stdout.write(f'   GIT_COMMIT_DATE={commit_date}')
        self.stdout.write('\n💡 Copy these values into your Portainer stack environment variables!')

    def set_version_from_url(self, url):
        """Set version from a GitHub/GitLab URL"""
        try:
            from core.url_version_extractor import URLVersionExtractor
            
            self.stdout.write(f'🌐 Extracting version info from URL: {url}')
            
            extractor = URLVersionExtractor()
            result = extractor.extract_from_url(url)
            
            if 'error' in result:
                self.stdout.write(
                    self.style.ERROR(f'❌ {result["error"]}')
                )
                if 'supported' in result:
                    self.stdout.write(
                        self.style.WARNING(f'💡 Supported providers: {", ".join(result["supported"])}')
                    )
                return
            
            # Set environment variables
            self.set_env_vars(
                result['commit_count'], 
                result['commit_hash'], 
                result['branch'], 
                result['commit_date']
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Version extracted from URL: {result["full_version"]}'
                )
            )
            
            if 'source_url' in result:
                self.stdout.write(f'🔗 Source: {result["source_url"]}')
            
            if 'commit_message' in result:
                self.stdout.write(f'📝 Commit: {result["commit_message"]}')
            
        except ImportError:
            self.stdout.write(
                self.style.ERROR('❌ URL extraction not available. Missing dependencies.')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error extracting from URL: {str(e)}')
            )
