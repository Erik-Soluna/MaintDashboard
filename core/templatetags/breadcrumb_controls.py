from django import template
from django.template import Context, Template

register = template.Library()

@register.simple_tag(takes_context=True)
def breadcrumb_control(context, action='show', **kwargs):
    """
    Template tag to control breadcrumb display on individual pages.
    
    Usage:
    {% breadcrumb_control 'hide' %}  # Hide breadcrumbs for this page
    {% breadcrumb_control 'show' %}  # Show breadcrumbs for this page (default)
    {% breadcrumb_control 'custom' home_text='Dashboard' separator='|' %}  # Custom settings
    """
    request = context.get('request')
    if not request:
        return ''
    
    # Store breadcrumb control in request for this page
    if not hasattr(request, 'breadcrumb_control'):
        request.breadcrumb_control = {}
    
    if action == 'hide':
        request.breadcrumb_control['enabled'] = False
    elif action == 'show':
        request.breadcrumb_control['enabled'] = True
    elif action == 'custom':
        request.breadcrumb_control.update(kwargs)
    
    return ''

@register.simple_tag(takes_context=True)
def get_breadcrumb_setting(context, setting_name):
    """
    Get breadcrumb setting with page-level override support.
    """
    request = context.get('request')
    if not request:
        return context.get(f'breadcrumb_{setting_name}', '')
    
    # Check for page-level override
    if hasattr(request, 'breadcrumb_control') and setting_name in request.breadcrumb_control:
        return request.breadcrumb_control[setting_name]
    
    # Return global setting
    return context.get(f'breadcrumb_{setting_name}', '')
