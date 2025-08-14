from django import template

register = template.Library()

@register.filter
def get_custom_value(equipment, field_name):
    """Get the value of a custom field for equipment."""
    try:
        return equipment.get_custom_value(field_name)
    except:
        return None
