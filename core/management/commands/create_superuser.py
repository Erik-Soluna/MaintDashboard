"""
Django command to create a superuser if one doesn't exist.
"""
import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    """Django command to create superuser."""

    help = 'Create a superuser if one does not exist'

    def handle(self, *args, **options):
        """Handle the command."""
        username = os.environ.get('ADMIN_USERNAME', 'admin')
        email = os.environ.get('ADMIN_EMAIL', 'admin@maintenance.local')
        password = os.environ.get('ADMIN_PASSWORD', 'admin123')

        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write(
                self.style.WARNING('Superuser already exists, skipping creation.')
            )
            return

        try:
            user = User.objects.create_superuser(
                username=username,
                email=email,
                password=password
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f'Superuser "{username}" created successfully!'
                )
            )
            self.stdout.write(
                self.style.WARNING(
                    f'Please change the default password for security!'
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating superuser: {e}')
            )