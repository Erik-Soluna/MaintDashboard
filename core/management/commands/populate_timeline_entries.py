"""
Management command to populate timeline entries for maintenance activities.
"""

from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from maintenance.models import MaintenanceActivity, MaintenanceTimelineEntry


class Command(BaseCommand):
    help = 'Populate database with timeline entries for maintenance activities'

    def handle(self, *args, **options):
        self.stdout.write('Starting to populate timeline entries...')
        
        # Get admin user
        admin_user = User.objects.get(username='admin')
        
        # Get maintenance activities
        activities = MaintenanceActivity.objects.all()
        
        if not activities:
            self.stdout.write('No maintenance activities found. Please run populate_maintenance_activities first.')
            return
        
        entries_created = 0
        
        for activity in activities:
            # Create timeline entries based on activity status
            if activity.status == 'completed':
                # Create a complete timeline for completed activities
                timeline_data = [
                    ('created', f'Activity created for {activity.equipment.name}', 
                     f'Maintenance activity "{activity.title}" was created and scheduled for {activity.scheduled_start.strftime("%Y-%m-%d %H:%M")}'),
                    ('assigned', f'Activity assigned to {activity.assigned_to.username if activity.assigned_to else "Unassigned"}', 
                     f'Activity was assigned to {activity.assigned_to.username if activity.assigned_to else "Unassigned"} for execution'),
                    ('started', f'Activity started at {activity.actual_start.strftime("%Y-%m-%d %H:%M") if activity.actual_start else "Unknown"}', 
                     f'Maintenance work began on {activity.equipment.name}'),
                    ('completed', f'Activity completed successfully', 
                     f'Maintenance activity completed successfully. {activity.completion_notes or "No issues encountered."}'),
                ]
            elif activity.status == 'pending':
                # Create timeline for pending activities
                timeline_data = [
                    ('created', f'Activity created for {activity.equipment.name}', 
                     f'Maintenance activity "{activity.title}" was created and scheduled for {activity.scheduled_start.strftime("%Y-%m-%d %H:%M")}'),
                    ('assigned', f'Activity assigned to {activity.assigned_to.username if activity.assigned_to else "Unassigned"}', 
                     f'Activity was assigned to {activity.assigned_to.username if activity.assigned_to else "Unassigned"} for execution'),
                ]
            elif activity.status == 'overdue':
                # Create timeline for overdue activities
                timeline_data = [
                    ('created', f'Activity created for {activity.equipment.name}', 
                     f'Maintenance activity "{activity.title}" was created and scheduled for {activity.scheduled_start.strftime("%Y-%m-%d %H:%M")}'),
                    ('assigned', f'Activity assigned to {activity.assigned_to.username if activity.assigned_to else "Unassigned"}', 
                     f'Activity was assigned to {activity.assigned_to.username if activity.assigned_to else "Unassigned"} for execution'),
                    ('issue', f'Activity is overdue - requires immediate attention', 
                     f'Maintenance activity is overdue by {(datetime.now() - activity.scheduled_start).days} days. Requires immediate attention.', 'high'),
                ]
            else:
                # Default timeline for other statuses
                timeline_data = [
                    ('created', f'Activity created for {activity.equipment.name}', 
                     f'Maintenance activity "{activity.title}" was created and scheduled for {activity.scheduled_start.strftime("%Y-%m-%d %H:%M")}'),
                ]
            
            # Create timeline entries
            for i, (entry_type, title, description, *extra) in enumerate(timeline_data):
                # Calculate timestamp based on activity schedule and entry order
                if entry_type == 'created':
                    timestamp = activity.scheduled_start - timedelta(days=7)  # Created 1 week before
                elif entry_type == 'assigned':
                    timestamp = activity.scheduled_start - timedelta(days=3)  # Assigned 3 days before
                elif entry_type == 'started':
                    timestamp = activity.actual_start if activity.actual_start else activity.scheduled_start
                elif entry_type == 'completed':
                    timestamp = activity.actual_end if activity.actual_end else activity.scheduled_end
                elif entry_type == 'issue':
                    timestamp = activity.scheduled_start + timedelta(days=1)  # Issue reported 1 day after due
                else:
                    timestamp = activity.scheduled_start - timedelta(days=5 - i)
                
                # Create timeline entry
                entry_data = {
                    'activity': activity,
                    'entry_type': entry_type,
                    'title': title,
                    'description': description,
                    'created_by': admin_user,
                }
                
                # Add optional fields for issue entries
                if entry_type == 'issue' and extra:
                    entry_data['issue_severity'] = extra[0]
                
                # Override created_at timestamp
                entry, created = MaintenanceTimelineEntry.objects.get_or_create(
                    activity=activity,
                    entry_type=entry_type,
                    title=title,
                    defaults=entry_data
                )
                
                if created:
                    # Manually set the created_at timestamp
                    entry.created_at = timestamp
                    entry.save(update_fields=['created_at'])
                    entries_created += 1
                    self.stdout.write(f'Created timeline entry: {entry_type} for {activity.title}')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully populated timeline entries with:\n'
                f'- {entries_created} timeline entries created\n'
                f'- Entries cover activity lifecycle (created, assigned, started, completed, issues)\n'
                f'- Proper timestamps for realistic timeline progression'
            )
        ) 