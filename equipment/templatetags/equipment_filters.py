from django import template
import logging

register = template.Library()

logger = logging.getLogger(__name__)

@register.filter
def get_custom_value(equipment, field_name):
    """Get the value of a custom field for equipment."""
    try:
        return equipment.get_custom_value(field_name)
    except AttributeError as e:
        logger.warning(f"Equipment object missing get_custom_value method: {e}")
        return None
    except Exception as e:
        logger.error(f"Error getting custom value for field '{field_name}' on equipment '{equipment}': {e}")
        return None

@register.filter
def get_equipment_status_badge_class(status):
    """Get the appropriate Bootstrap badge class for equipment status."""
    status_classes = {
        'active': 'badge-success',
        'maintenance': 'badge-warning',
        'inactive': 'badge-secondary',
        'retired': 'badge-dark',
    }
    return status_classes.get(status, 'badge-secondary')

@register.filter
def get_maintenance_status_badge_class(status):
    """Get the appropriate Bootstrap badge class for maintenance status."""
    status_classes = {
        'completed': 'badge-success',
        'overdue': 'badge-danger',
        'in_progress': 'badge-warning',
        'scheduled': 'badge-info',
        'cancelled': 'badge-secondary',
    }
    return status_classes.get(status, 'badge-secondary')

@register.filter
def format_equipment_date(date, format_string="M d, Y"):
    """Format equipment dates with fallback for None values."""
    if date:
        try:
            return date.strftime(format_string)
        except AttributeError:
            return str(date)
    return "Not specified"

@register.filter
def get_equipment_location_path(location):
    """Get the full path of an equipment location."""
    if location:
        try:
            return location.get_full_path()
        except AttributeError:
            return location.name
    return "Not specified"

@register.filter
def get_field(form, field_name):
    """Get a form field by name."""
    if hasattr(form, field_name):
        return form[field_name]
    return None

@register.filter
def get_field_errors(form, field_name):
    """Get errors for a form field by name."""
    if hasattr(form, field_name):
        return form[field_name].errors
    return []