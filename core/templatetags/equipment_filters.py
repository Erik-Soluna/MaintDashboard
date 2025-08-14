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
