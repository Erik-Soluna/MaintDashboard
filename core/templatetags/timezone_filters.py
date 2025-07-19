from django import template
from django.utils import timezone

try:
    import pytz
    PYTZ_AVAILABLE = True
except ImportError:
    PYTZ_AVAILABLE = False

register = template.Library()

@register.filter
def user_timezone(datetime_obj, user):
    """
    Convert a datetime object to the user's preferred timezone.
    Usage: {{ some_datetime|user_timezone:user }}
    """
    if not PYTZ_AVAILABLE:
        return datetime_obj
    
    if not datetime_obj or not user or not hasattr(user, 'userprofile'):
        return datetime_obj
    
    try:
        return user.userprofile.convert_to_user_timezone(datetime_obj)
    except Exception:
        return datetime_obj

@register.filter
def user_timezone_format(datetime_obj, user, format_string="M d, Y H:i"):
    """
    Convert a datetime object to user's timezone and format it.
    Usage: {{ some_datetime|user_timezone_format:user:"M d, Y H:i" }}
    """
    if not PYTZ_AVAILABLE:
        if datetime_obj:
            return datetime_obj.strftime(format_string)
        return datetime_obj
    
    converted_time = user_timezone(datetime_obj, user)
    if converted_time:
        return converted_time.strftime(format_string)
    return datetime_obj 