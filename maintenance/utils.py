"""
Utility functions for maintenance app.
"""

from django.utils import timezone
from core.models import DashboardSettings


def generate_activity_title(template, activity_type=None, equipment=None, scheduled_start=None, priority=None, status=None):
    """
    Generate a maintenance activity title from a template.
    
    Available template variables:
    - {Activity_Type}: Activity type name
    - {Equipment}: Equipment name
    - {Date}: Scheduled start date (formatted as YYYY-MM-DD)
    - {Priority}: Priority display name
    - {Status}: Status display name
    
    Args:
        template: Template string with variables
        activity_type: MaintenanceActivityType instance or name string
        equipment: Equipment instance or name string
        scheduled_start: datetime object
        priority: Priority value (will be converted to display name)
        status: Status value (will be converted to display name)
    
    Returns:
        Generated title string
    """
    if not template:
        # Get default template from settings
        try:
            dashboard_settings = DashboardSettings.get_active()
            template = dashboard_settings.activity_title_template
        except Exception:
            template = "{Activity_Type} - {Equipment}"
    
    # Get activity type name
    activity_type_name = ""
    if activity_type:
        if hasattr(activity_type, 'name'):
            activity_type_name = activity_type.name
        else:
            activity_type_name = str(activity_type)
    
    # Get equipment name
    equipment_name = ""
    if equipment:
        if hasattr(equipment, 'name'):
            equipment_name = equipment.name
        else:
            equipment_name = str(equipment)
    
    # Format date
    date_str = ""
    if scheduled_start:
        if hasattr(scheduled_start, 'strftime'):
            date_str = scheduled_start.strftime('%Y-%m-%d')
        else:
            date_str = str(scheduled_start)
    
    # Get priority display name
    priority_display = ""
    if priority:
        priority_map = {
            'low': 'Low',
            'medium': 'Medium',
            'high': 'High',
            'critical': 'Critical',
        }
        priority_display = priority_map.get(priority, priority.capitalize())
    
    # Get status display name
    status_display = ""
    if status:
        status_map = {
            'scheduled': 'Scheduled',
            'pending': 'Pending',
            'in_progress': 'In Progress',
            'completed': 'Completed',
            'cancelled': 'Cancelled',
            'overdue': 'Overdue',
        }
        status_display = status_map.get(status, status.capitalize())
    
    # Replace template variables
    title = template
    title = title.replace('{Activity_Type}', activity_type_name)
    title = title.replace('{Equipment}', equipment_name)
    title = title.replace('{Date}', date_str)
    title = title.replace('{Priority}', priority_display)
    title = title.replace('{Status}', status_display)
    
    return title

