"""
Management command to clear the database.
WARNING: This is a destructive operation that will delete all data!
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.contrib.auth.models import User
from django.core.management import call_command
from django.utils import timezone
from django.db import transaction
import logging
import sys

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Clear all data from the database (DESTRUCTIVE OPERATION)'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Skip confirmation prompts (use with extreme caution)',
        )
        parser.add_argument(
            '--keep-users',
            action='store_true',
            help='Keep user accounts but clear all other data',
        )
        parser.add_argument(
            '--keep-admin',
            action='store_true',
            help='Keep admin user account even when clearing users',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        force = options['force']
        keep_users = options['keep_users']
        keep_admin = options['keep_admin']
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No data will be deleted')
            )
        
        # Show warning and get confirmation
        if not force:
            self.stdout.write(
                self.style.ERROR(
                    '\n' + '='*80 + '\n'
                    'WARNING: DESTRUCTIVE OPERATION\n'
                    'This command will delete ALL data from the database!\n'
                    '='*80 + '\n'
                )
            )
            
            if not dry_run:
                confirm = input('\nType "CLEAR DATABASE" to confirm: ')
                if confirm != 'CLEAR DATABASE':
                    self.stdout.write(
                        self.style.ERROR('Operation cancelled.')
                    )
                    return
        
        # Get database statistics before clearing
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT schemaname, relname as tablename, n_tup_ins as rows
                FROM pg_stat_user_tables
                WHERE schemaname = 'public'
                ORDER BY n_tup_ins DESC
            """)
            table_stats = cursor.fetchall()
        
        self.stdout.write('\nCurrent database statistics:')
        total_rows = 0
        for schema, table, rows in table_stats:
            if rows > 0:
                self.stdout.write(f'  {table}: {rows:,} rows')
                total_rows += rows
        
        self.stdout.write(f'\nTotal rows to be deleted: {total_rows:,}')
        
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS('\nDry run completed. No data was deleted.')
            )
            return
        
        # Proceed with clearing
        self.stdout.write('\nStarting database clear operation...')
        
        try:
            with transaction.atomic():
                # Clear all data except users if requested
                if keep_users:
                    self.stdout.write('Keeping user accounts...')
                    # Clear all data except User and UserProfile
                    models_to_clear = [
                        'equipment.Equipment',
                        'equipment.EquipmentComponent', 
                        'equipment.EquipmentDocument',
                        'maintenance.MaintenanceActivity',
                        'maintenance.MaintenanceActivityType',
                        'maintenance.MaintenanceSchedule',
                        'maintenance.MaintenanceReport',
                        'events.CalendarEvent',
                        'events.EventComment',
                        'events.EventAttachment',
                        'events.EventReminder',
                        'core.Location',
                        'core.EquipmentCategory',
                        'core.Customer',
                        'core.PlaywrightDebugLog',
                    ]
                    
                    for model in models_to_clear:
                        try:
                            # Import the model dynamically
                            app_label, model_name = model.split('.')
                            from django.apps import apps
                            Model = apps.get_model(app_label, model_name)
                            count = Model.objects.all().count()
                            Model.objects.all().delete()
                            self.stdout.write(f'  Cleared {model}: {count} records')
                        except Exception as e:
                            self.stdout.write(f'  Error clearing {model}: {e}')
                else:
                    # Clear everything including users
                    if keep_admin:
                        self.stdout.write('Preserving admin user...')
                        # Get admin user before clearing
                        admin_username = None
                        admin_email = None
                        try:
                            admin_user = User.objects.filter(is_superuser=True).first()
                            if admin_user:
                                admin_username = admin_user.username
                                admin_email = admin_user.email
                        except:
                            pass
                    
                    # Clear all data using raw SQL for better control
                    with connection.cursor() as cursor:
                        # Disable foreign key checks temporarily
                        cursor.execute("SET session_replication_role = replica;")
                        
                        # Get all tables
                        cursor.execute("""
                            SELECT tablename FROM pg_tables 
                            WHERE schemaname = 'public' 
                            AND tablename NOT LIKE 'django_%'
                            AND tablename NOT LIKE 'auth_%'
                        """)
                        tables = [row[0] for row in cursor.fetchall()]
                        
                        # Clear each table
                        for table in tables:
                            try:
                                cursor.execute(f"TRUNCATE TABLE {table} CASCADE;")
                                self.stdout.write(f'  Cleared table: {table}')
                            except Exception as e:
                                self.stdout.write(f'  Error clearing {table}: {e}')
                        
                        # Re-enable foreign key checks
                        cursor.execute("SET session_replication_role = DEFAULT;")
                    
                    # Recreate admin user if requested
                    if keep_admin and admin_username:
                        try:
                            User.objects.create_superuser(
                                username=admin_username,
                                email=admin_email or f'{admin_username}@admin.local',
                                password='admin123'
                            )
                            self.stdout.write(f'Recreated admin user: {admin_username}')
                        except Exception as e:
                            self.stdout.write(f'Error recreating admin user: {e}')
            
            # Log the operation
            logger.warning(
                f'Database cleared by user at {timezone.now()}. '
                f'Keep users: {keep_users}, Keep admin: {keep_admin}'
            )
            
            self.stdout.write(
                self.style.SUCCESS('\nDatabase cleared successfully!')
            )
            
            # Show post-clear statistics
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT schemaname, relname as tablename, n_tup_ins as rows
                    FROM pg_stat_user_tables
                    WHERE schemaname = 'public'
                    ORDER BY n_tup_ins DESC
                """)
                table_stats = cursor.fetchall()
            
            remaining_rows = sum(rows for _, _, rows in table_stats)
            self.stdout.write(f'\nRemaining rows: {remaining_rows:,}')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'\nError clearing database: {e}')
            )
            logger.error(f'Database clear operation failed: {e}')
            raise CommandError(f'Failed to clear database: {e}') 