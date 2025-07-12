"""
Middleware for handling forced password changes and other core functionality.
"""

from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from django.utils.deprecation import MiddlewareMixin


class ForcePasswordChangeMiddleware(MiddlewareMixin):
    """
    Middleware to force password change for users on their first login.
    
    This middleware checks if:
    1. User is authenticated
    2. User has never logged in before (last_login is None)
    3. User is not already on password change page
    4. User is not accessing admin logout or certain exempt URLs
    
    If conditions are met, redirects to password change page.
    """
    
    # URLs that should be exempt from forced password change
    EXEMPT_URLS = [
        'admin:logout',
        'admin:password_change',
        'admin:password_change_done',
        'password_change',
        'password_change_done',
        'logout',
        '/admin/logout/',
        '/admin/password_change/',
        '/admin/password_change/done/',
        '/auth/logout/',
        '/auth/password_change/',
        '/auth/password_change/done/',
    ]
    
    # URL patterns that should be exempt (for static files, media, etc.)
    EXEMPT_PATTERNS = [
        '/static/',
        '/media/',
        '/favicon.ico',
    ]

    def process_request(self, request):
        """Process each request to check for forced password change requirement."""
        
        # Skip if user is not authenticated
        if not request.user.is_authenticated:
            return None
            
        # Check if user has a profile and if password change is forced
        force_password_change = False
        
        try:
            # Check if user profile exists and force_password_change is True
            if hasattr(request.user, 'userprofile') and request.user.userprofile:
                force_password_change = getattr(request.user.userprofile, 'force_password_change', False)
        except:
            # If UserProfile doesn't exist, check last_login (fallback behavior)
            force_password_change = request.user.last_login is None
            
        # Also check for first-time login (when last_login is None)
        if request.user.last_login is None:
            force_password_change = True
            
        # Skip if password change is not required
        if not force_password_change:
            return None
            
        # Check if current URL should be exempt
        if self._is_exempt_url(request):
            return None
            
        # Check if this is an AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return None
            
        # User needs to change password - redirect to password change page
        if request.user.last_login is None:
            messages.warning(
                request,
                'This is your first login. You must change your password before continuing.'
            )
        else:
            messages.warning(
                request,
                'You are required to change your password before continuing.'
            )
        
        # Try to use Django admin password change first, fallback to custom if needed
        try:
            password_change_url = reverse('admin:password_change')
        except:
            # If admin password change is not available, use auth URLs
            try:
                password_change_url = reverse('password_change')
            except:
                # Fallback to hardcoded admin URL
                password_change_url = '/admin/password_change/'
        
        return redirect(password_change_url)

    def _is_exempt_url(self, request):
        """Check if the current URL should be exempt from password change requirement."""
        
        # Check exact URL matches
        if request.path in self.EXEMPT_URLS:
            return True
            
        # Check URL patterns
        for pattern in self.EXEMPT_PATTERNS:
            if request.path.startswith(pattern):
                return True
                
        # Check if URL name is exempt
        if hasattr(request, 'resolver_match') and request.resolver_match:
            url_name = request.resolver_match.url_name
            if url_name in self.EXEMPT_URLS:
                return True
                
            # Check for admin URLs
            if (hasattr(request.resolver_match, 'namespace') and 
                request.resolver_match.namespace == 'admin'):
                if url_name in ['password_change', 'password_change_done', 'logout']:
                    return True
        
        return False


class LoginTrackingMiddleware(MiddlewareMixin):
    """
    Middleware to track user login and update last_login field properly.
    This ensures the ForcePasswordChangeMiddleware works correctly.
    """
    
    def process_response(self, request, response):
        """Update last_login when user successfully logs in."""
        
        # Check if this is a successful login
        if (hasattr(request, 'user') and 
            request.user.is_authenticated and 
            request.user.last_login is None and
            not self._is_password_change_request(request)):
            
            # Don't update last_login until password is actually changed
            # The admin interface or custom views should handle this
            pass
            
        return response
    
    def _is_password_change_request(self, request):
        """Check if this is a password change request."""
        return (
            'password_change' in request.path or
            (hasattr(request, 'resolver_match') and 
             request.resolver_match and
             'password_change' in str(request.resolver_match.url_name))
        )