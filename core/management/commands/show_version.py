from django.core.management.base import BaseCommand
from version import get_git_version


class Command(BaseCommand):
    help = 'Display current version information'

    def handle(self, *args, **options):
        try:
            version_info = get_git_version()
            
            self.stdout.write(
                self.style.SUCCESS(f"Version: {version_info['version']}")
            )
            self.stdout.write(
                self.style.SUCCESS(f"Commit: {version_info['commit_hash']}")
            )
            self.stdout.write(
                self.style.SUCCESS(f"Branch: {version_info['branch']}")
            )
            self.stdout.write(
                self.style.SUCCESS(f"Date: {version_info['commit_date']}")
            )
            self.stdout.write(
                self.style.SUCCESS(f"Full: {version_info['full_version']}")
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error getting version: {e}")
            )
