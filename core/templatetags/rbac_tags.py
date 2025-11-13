from django import template
from core.rbac import user_has_permission

register = template.Library()

@register.filter
def has_permission(user, permission_codename):
    """Check if user has a specific permission."""
    if not user or not user.is_authenticated:
        return False
    return user_has_permission(user, permission_codename)

