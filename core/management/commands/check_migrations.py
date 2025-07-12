"""
Django management command to check migration status across all apps.
This command will verify that all migrations have been applied correctly
and flag any issues that need attention.
"""

import os
import sys
from collections import defaultdict
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.apps import apps
from django.core.management import call_command
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.recorder import MigrationRecorder
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Check migration status across all apps and flag any issues'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix-conflicts',
            action='store_true',
            help='Attempt to fix migration conflicts automatically'
        )
        parser.add_argument(
            '--apply-missing',
            action='store_true',
            help='Apply missing migrations automatically'
        )
        parser.add_argument(
            '--verbose',
            '-v',
            action='store_true',
            help='Show detailed output'
        )
        parser.add_argument(
            '--app',
            type=str,
            help='Check migrations for specific app only'
        )

    def handle(self, *args, **options):
        self.verbosity = options.get('verbosity', 1)
        self.verbose = options.get('verbose', False)
        self.fix_conflicts = options.get('fix_conflicts', False)
        self.apply_missing = options.get('apply_missing', False)
        self.target_app = options.get('app')
        
        self.style = self.style
        self.issues_found = []
        self.success_count = 0
        self.warning_count = 0
        self.error_count = 0
        
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('Migration Status Check'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        
        try:
            # Check database connection
            self.check_database_connection()
            
            # Get migration status
            migration_status = self.get_migration_status()
            
            # Check for issues
            self.check_migration_issues(migration_status)
            
            # Display results
            self.display_results(migration_status)
            
            # Apply fixes if requested
            if self.fix_conflicts or self.apply_missing:
                self.apply_fixes()
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error during migration check: {str(e)}'))
            if self.verbose:
                import traceback
                self.stdout.write(self.style.ERROR(traceback.format_exc()))
            sys.exit(1)

    def check_database_connection(self):
        """Check if database connection is working."""
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                if result and result[0] == 1:
                    self.stdout.write(self.style.SUCCESS('✓ Database connection: OK'))
                else:
                    raise Exception("Database connection test failed")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Database connection: FAILED - {str(e)}'))
            raise

    def get_migration_status(self):
        """Get detailed migration status for all apps."""
        loader = MigrationLoader(connection)
        executor = MigrationExecutor(connection)
        recorder = MigrationRecorder(connection)
        
        # Get all migration files
        migration_files = {}
        for app_name in apps.get_app_configs():
            if self.target_app and app_name.name != self.target_app:
                continue
                
            app_path = app_name.path
            migrations_path = os.path.join(app_path, 'migrations')
            
            if os.path.exists(migrations_path):
                migration_files[app_name.name] = []
                for file in os.listdir(migrations_path):
                    if file.endswith('.py') and file != '__init__.py':
                        migration_files[app_name.name].append(file[:-3])  # Remove .py extension

        # Get applied migrations from database
        applied_migrations = set()
        try:
            for migration in recorder.applied_migrations():
                applied_migrations.add(migration)
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Could not read applied migrations: {str(e)}'))

        # Get pending migrations
        pending_migrations = executor.migration_plan(executor.loader.graph.leaf_nodes())
        
        # Check for conflicts
        conflicts = []
        try:
            conflicts = loader.detect_conflicts()
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Could not detect conflicts: {str(e)}'))

        return {
            'migration_files': migration_files,
            'applied_migrations': applied_migrations,
            'pending_migrations': pending_migrations,
            'conflicts': conflicts,
            'loader': loader,
            'executor': executor
        }

    def check_migration_issues(self, migration_status):
        """Check for various migration issues."""
        
        # Check for migration conflicts
        if migration_status['conflicts']:
            for conflict in migration_status['conflicts']:
                issue = {
                    'type': 'CONFLICT',
                    'app': conflict.app_label if hasattr(conflict, 'app_label') else 'Unknown',
                    'description': f'Migration conflict detected: {conflict}',
                    'severity': 'HIGH'
                }
                self.issues_found.append(issue)
                self.error_count += 1

        # Check for duplicate migration numbers
        for app_name, migrations in migration_status['migration_files'].items():
            migration_numbers = defaultdict(list)
            for migration in migrations:
                if migration.startswith('0'):
                    try:
                        number = migration.split('_')[0]
                        migration_numbers[number].append(migration)
                    except:
                        continue
            
            for number, migration_list in migration_numbers.items():
                if len(migration_list) > 1:
                    issue = {
                        'type': 'DUPLICATE_NUMBER',
                        'app': app_name,
                        'description': f'Duplicate migration number {number}: {migration_list}',
                        'severity': 'HIGH'
                    }
                    self.issues_found.append(issue)
                    self.error_count += 1

        # Check for missing migrations
        if migration_status['pending_migrations']:
            for app_label, migration_name in migration_status['pending_migrations']:
                issue = {
                    'type': 'PENDING',
                    'app': app_label,
                    'description': f'Pending migration: {migration_name}',
                    'severity': 'MEDIUM'
                }
                self.issues_found.append(issue)
                self.warning_count += 1

        # Check for orphaned migrations (applied but file doesn't exist)
        for app_label, migration_name in migration_status['applied_migrations']:
            if app_label in migration_status['migration_files']:
                if migration_name not in migration_status['migration_files'][app_label]:
                    issue = {
                        'type': 'ORPHANED',
                        'app': app_label,
                        'description': f'Applied migration file not found: {migration_name}',
                        'severity': 'LOW'
                    }
                    self.issues_found.append(issue)
                    self.warning_count += 1

    def display_results(self, migration_status):
        """Display detailed migration status results."""
        
        self.stdout.write('\n' + self.style.SUCCESS('Migration Status by App:'))
        self.stdout.write('-' * 40)
        
        for app_name, migrations in migration_status['migration_files'].items():
            self.stdout.write(f'\n{self.style.HTTP_INFO(app_name.upper())}:')
            
            if not migrations:
                self.stdout.write('  No migrations found')
                continue
                
            for migration in sorted(migrations):
                status = 'APPLIED' if (app_name, migration) in migration_status['applied_migrations'] else 'PENDING'
                status_color = self.style.SUCCESS if status == 'APPLIED' else self.style.WARNING
                self.stdout.write(f'  {migration}: {status_color(status)}')
        
        # Display issues
        if self.issues_found:
            self.stdout.write('\n' + self.style.ERROR('Issues Found:'))
            self.stdout.write('-' * 40)
            
            for issue in self.issues_found:
                severity_color = {
                    'HIGH': self.style.ERROR,
                    'MEDIUM': self.style.WARNING,
                    'LOW': self.style.NOTICE
                }.get(issue['severity'], self.style.NOTICE)
                
                self.stdout.write(f'{severity_color(issue["severity"])}: {issue["app"]} - {issue["description"]}')
        
        # Display summary
        self.stdout.write('\n' + self.style.SUCCESS('Summary:'))
        self.stdout.write('-' * 40)
        
        total_apps = len(migration_status['migration_files'])
        total_migrations = sum(len(migrations) for migrations in migration_status['migration_files'].values())
        applied_count = len(migration_status['applied_migrations'])
        pending_count = len(migration_status['pending_migrations'])
        
        self.stdout.write(f'Total apps: {total_apps}')
        self.stdout.write(f'Total migrations: {total_migrations}')
        self.stdout.write(f'Applied migrations: {applied_count}')
        self.stdout.write(f'Pending migrations: {pending_count}')
        self.stdout.write(f'Issues found: {len(self.issues_found)}')
        
        if self.error_count > 0:
            self.stdout.write(self.style.ERROR(f'Errors: {self.error_count}'))
        if self.warning_count > 0:
            self.stdout.write(self.style.WARNING(f'Warnings: {self.warning_count}'))
        
        if not self.issues_found:
            self.stdout.write(self.style.SUCCESS('✓ All migrations are in good state!'))
        else:
            self.stdout.write(self.style.WARNING('⚠ Issues found that may need attention.'))

    def apply_fixes(self):
        """Apply automatic fixes for migration issues."""
        
        if not self.issues_found:
            self.stdout.write(self.style.SUCCESS('No issues to fix.'))
            return
        
        self.stdout.write('\n' + self.style.WARNING('Applying fixes...'))
        
        # Apply missing migrations
        if self.apply_missing:
            pending_issues = [issue for issue in self.issues_found if issue['type'] == 'PENDING']
            if pending_issues:
                self.stdout.write('Applying pending migrations...')
                try:
                    call_command('migrate', verbosity=1)
                    self.stdout.write(self.style.SUCCESS('✓ Pending migrations applied'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'✗ Failed to apply migrations: {str(e)}'))
        
        # Fix conflicts (this is more complex and depends on the specific conflict)
        if self.fix_conflicts:
            conflict_issues = [issue for issue in self.issues_found if issue['type'] == 'CONFLICT']
            if conflict_issues:
                self.stdout.write('Attempting to fix migration conflicts...')
                # This would need specific logic based on the type of conflict
                self.stdout.write(self.style.WARNING('Manual intervention may be required for migration conflicts.'))
                self.stdout.write('Consider using: python manage.py migrate --fake-initial')
        
        # Report on duplicate migration numbers
        duplicate_issues = [issue for issue in self.issues_found if issue['type'] == 'DUPLICATE_NUMBER']
        if duplicate_issues:
            self.stdout.write('\n' + self.style.ERROR('Duplicate migration numbers found:'))
            for issue in duplicate_issues:
                self.stdout.write(f'  {issue["app"]}: {issue["description"]}')
            self.stdout.write('Manual intervention required to resolve duplicate migration numbers.')

    def get_recommendations(self):
        """Get recommendations based on found issues."""
        recommendations = []
        
        if any(issue['type'] == 'CONFLICT' for issue in self.issues_found):
            recommendations.append('Run: python manage.py migrate --fake-initial')
        
        if any(issue['type'] == 'PENDING' for issue in self.issues_found):
            recommendations.append('Run: python manage.py migrate')
        
        if any(issue['type'] == 'DUPLICATE_NUMBER' for issue in self.issues_found):
            recommendations.append('Manually rename migration files to resolve numbering conflicts')
        
        return recommendations