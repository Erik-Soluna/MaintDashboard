"""
Django management command to initialize RBAC system.
Sets up default roles and permissions.
"""

from django.core.management.base import BaseCommand
from core.rbac import initialize_default_permissions, assign_default_roles


class Command(BaseCommand):
    help = 'Initialize RBAC system with default roles and permissions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force initialization even if roles already exist'
        )

    def handle(self, *args, **options):
        """Initialize RBAC system."""
        self.stdout.write(
            self.style.SUCCESS('🚀 Initializing RBAC system...\n')
        )

        try:
            # Initialize permissions and roles
            self.stdout.write('📋 Creating default permissions and roles...')
            permissions = initialize_default_permissions()
            self.stdout.write(
                self.style.SUCCESS(f'   ✅ Created {len(permissions)} permissions')
            )

            # Assign default roles to users
            self.stdout.write('👥 Assigning default roles to users...')
            assign_default_roles()
            self.stdout.write(
                self.style.SUCCESS('   ✅ Default roles assigned')
            )

            self.stdout.write(
                self.style.SUCCESS('\n🎉 RBAC system initialized successfully!')
            )
            
            # Show summary
            from core.models import Role, Permission, UserProfile
            from django.contrib.auth.models import User
            
            total_roles = Role.objects.count()
            total_permissions = Permission.objects.count()
            users_with_roles = UserProfile.objects.exclude(role=None).count()
            total_users = User.objects.count()
            
            self.stdout.write('\n📊 Summary:')
            self.stdout.write(f'   Roles: {total_roles}')
            self.stdout.write(f'   Permissions: {total_permissions}')
            self.stdout.write(f'   Users with roles: {users_with_roles}/{total_users}')

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'\n❌ RBAC initialization failed: {str(e)}')
            )
            raise