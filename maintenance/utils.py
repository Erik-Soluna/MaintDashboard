"""
Utility functions for maintenance app.

Timezone convention (see also CalendarEvent.set_times_from_activity):
- All DateTimeFields are stored UTC-aware (USE_TZ=True, TIME_ZONE='UTC').
- ``MaintenanceActivity.timezone`` is the display timezone for that activity.
- User-entered wall-clock times are interpreted in the activity's timezone and
  converted to UTC for storage via ``parse_wallclock_to_utc``; display converts
  the stored UTC instant back to the activity/user timezone.
"""

import pytz
from datetime import datetime, timedelta

from django.utils import timezone
from core.models import DashboardSettings

# Fallback timezone for activities/schedules that don't carry an explicit one.
# Matches MaintenanceActivity.timezone's model default.
DEFAULT_ACTIVITY_TIMEZONE = 'America/Chicago'


def parse_wallclock_to_utc(value, timezone_str):
    """Interpret a wall-clock time as being in ``timezone_str`` and return it as
    a UTC-aware datetime for storage.

    - ``value`` may be a naive/aware ``datetime`` or a string from a
      ``datetime-local`` input (e.g. ``'2026-05-29T19:00'``).
    - Naive values are localized to ``timezone_str`` (DST-safe via pytz
      ``localize``); aware values are converted to UTC.
    - Returns ``None`` when ``value`` is falsy.
    """
    if not value:
        return None

    if isinstance(value, str):
        parsed = None
        for fmt in ('%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M',
                    '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M'):
            try:
                parsed = datetime.strptime(value, fmt)
                break
            except ValueError:
                continue
        if parsed is None:
            from django.utils.dateparse import parse_datetime
            parsed = parse_datetime(value)
        if parsed is None:
            raise ValueError(f"Could not parse datetime string: {value!r}")
        value = parsed

    try:
        target_tz = pytz.timezone(timezone_str) if timezone_str else pytz.UTC
    except Exception:
        target_tz = pytz.UTC

    if timezone.is_naive(value):
        # Interpret the wall-clock time as being in the target timezone.
        return target_tz.localize(value).astimezone(pytz.UTC)
    return value.astimezone(pytz.UTC)


def local_date_tomorrow(timezone_str):
    """Return the date that is 'tomorrow' in ``timezone_str`` (DST-aware)."""
    try:
        tz = pytz.timezone(timezone_str) if timezone_str else pytz.UTC
    except Exception:
        tz = pytz.UTC
    return (timezone.now().astimezone(tz) + timedelta(days=1)).date()


def generate_activity_title(template, activity_type=None, equipment=None, scheduled_start=None, priority=None, status=None):
    """
    Generate a maintenance activity title from a template.
    
    Available template variables:
    - {Activity_Type}: Activity type name
    - {Equipment}: Equipment name
    - {POD}: POD number (location name) where equipment is located
    - {Date}: Scheduled start date (formatted as YYYY-MM-DD)
    - {Priority}: Priority display name
    - {Status}: Status display name
    
    Args:
        template: Template string with variables. If None, uses Dashboard Settings template.
        activity_type: MaintenanceActivityType instance or name string
        equipment: Equipment instance or name string
        scheduled_start: datetime object
        priority: Priority value (will be converted to display name)
        status: Status value (will be converted to display name)
    
    Returns:
        Generated title string
    """
    if not template:
        # Get default template from Dashboard Settings
        try:
            dashboard_settings = DashboardSettings.get_active()
            if dashboard_settings and dashboard_settings.activity_title_template:
                template = dashboard_settings.activity_title_template
            else:
                # Fallback to default template if no settings found
                template = "{Activity_Type} - {POD} - {Equipment}"
        except Exception:
            # Fallback to default template if error getting settings
            template = "{Activity_Type} - {POD} - {Equipment}"
    
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
    
    # Get POD (location) name
    pod_name = ""
    if equipment and hasattr(equipment, 'location') and equipment.location:
        pod_name = equipment.location.name
    elif not pod_name:
        pod_name = "Unknown"
    
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
    title = title.replace('{POD}', pod_name)
    title = title.replace('{Date}', date_str)
    title = title.replace('{Priority}', priority_display)
    title = title.replace('{Status}', status_display)
    
    return title

