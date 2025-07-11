"""
Management command to ensure all system permissions are created and available.
This fixes the issue where permissions don't show up in the Roles and Permissions interface.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from core.rbac import initialize_default_permissions
from core.models import Permission, Role


class Command(BaseCommand):
    help = 'Ensure all system permissions are created and available'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreate all permissions',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🔒 Ensuring System Permissions...')
        )

        try:
            with transaction.atomic():
                # Initialize all default permissions
                self.stdout.write('📋 Creating/updating permissions...')
                permissions = initialize_default_permissions()
                
                self.stdout.write(
                    self.style.SUCCESS(f'   ✅ Processed {len(permissions)} permissions')
                )

                # Display summary
                self.display_summary()
                
                self.stdout.write(
                    self.style.SUCCESS('✅ Permission initialization completed successfully!')
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error during permission initialization: {str(e)}')
            )
            raise

    def display_summary(self):
        """Display a summary of permissions and roles."""
        self.stdout.write('\n📊 Permission Summary:')
        
        # Count permissions by module
        modules = Permission.objects.values_list('module', flat=True).distinct()
        for module in modules:
            count = Permission.objects.filter(module=module, is_active=True).count()
            self.stdout.write(f'   {module}: {count} permissions')

        # Count roles
        total_roles = Role.objects.filter(is_active=True).count()
        system_roles = Role.objects.filter(is_active=True, is_system_role=True).count()
        custom_roles = total_roles - system_roles

        self.stdout.write(f'\n🎭 Role Summary:')
        self.stdout.write(f'   System Roles: {system_roles}')
        self.stdout.write(f'   Custom Roles: {custom_roles}')
        self.stdout.write(f'   Total Roles: {total_roles}')

        # List all permissions for verification
        self.stdout.write(f'\n📝 All Available Permissions:')
        for module in modules:
            module_permissions = Permission.objects.filter(
                module=module, 
                is_active=True
            ).order_by('name')
            
            self.stdout.write(f'\n   📂 {module.upper()} MODULE:')
            for perm in module_permissions:
                status = "✅" if perm.is_active else "❌"
                self.stdout.write(f'      {status} {perm.codename}: {perm.name}')