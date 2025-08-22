from django.core.management.base import BaseCommand
import importlib.util
import os
from django.conf import settings


class Command(BaseCommand):
    help = 'Display current version information'

    def handle(self, *args, **options):
        try:
            spec = importlib.util.spec_from_file_location("version_module", settings.BASE_DIR / "version.py")
            version_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(version_module)
            
            version_info = version_module.get_git_version()
            
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
