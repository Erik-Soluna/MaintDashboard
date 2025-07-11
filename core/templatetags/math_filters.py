from django import template

register = template.Library()

@register.filter
def mul(value, arg):
    """Multiply the value by the argument."""
    try:
        return int(value) * int(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def div(value, arg):
    """Divide the value by the argument."""
    try:
        return int(value) / int(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.filter
def add_int(value, arg):
    """Add the argument to the value and return as integer."""
    try:
        return int(value) + int(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def sub(value, arg):
    """Subtract the argument from the value."""
    try:
        return int(value) - int(arg)
    except (ValueError, TypeError):
        return 0