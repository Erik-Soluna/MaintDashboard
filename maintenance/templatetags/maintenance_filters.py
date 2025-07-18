"""
Template filters for maintenance app.
"""

from django import template

register = template.Library()


@register.filter
def timeline_color(entry_type):
    """Get Bootstrap color class for timeline entry type."""
    color_map = {
        'created': 'primary',
        'assigned': 'info',
        'started': 'warning',
        'paused': 'secondary',
        'resumed': 'info',
        'completed': 'success',
        'cancelled': 'danger',
        'note': 'light',
        'issue': 'danger',
        'resolution': 'success',
    }
    return color_map.get(entry_type, 'secondary')


@register.filter
def timeline_icon(entry_type):
    """Get FontAwesome icon class for timeline entry type."""
    icon_map = {
        'created': 'fa-plus',
        'assigned': 'fa-user',
        'started': 'fa-play',
        'paused': 'fa-pause',
        'resumed': 'fa-play',
        'completed': 'fa-check',
        'cancelled': 'fa-times',
        'note': 'fa-sticky-note',
        'issue': 'fa-exclamation-triangle',
        'resolution': 'fa-check-circle',
    }
    return icon_map.get(entry_type, 'fa-circle')


@register.filter
def status_color(status):
    """Get Bootstrap color class for maintenance status."""
    color_map = {
        'scheduled': 'secondary',
        'pending': 'warning',
        'in_progress': 'info',
        'completed': 'success',
        'cancelled': 'danger',
        'overdue': 'danger',
    }
    return color_map.get(status, 'secondary')


@register.filter
def priority_color(priority):
    """Get Bootstrap color class for priority."""
    color_map = {
        'low': 'secondary',
        'medium': 'info',
        'high': 'warning',
        'critical': 'danger',
    }
    return color_map.get(priority, 'secondary') 