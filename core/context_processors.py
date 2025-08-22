"""
Context processors for core app.
"""

from django.conf import settings
from .models import Location, UserProfile


def site_context(request):
    """
    Context processor to provide site information to all templates.
    """
    context = {
        'sites': [],
        'selected_site': None,
        'selected_site_id': None,
    }
    
    # Get all sites
    sites = Location.objects.filter(is_site=True, is_active=True).order_by('name')
    context['sites'] = sites
    
    if request.user.is_authenticated:
        # Ensure user has profile
        user_profile, created = UserProfile.objects.get_or_create(user=request.user)
        
        # Get selected site from request, session, or user default
        selected_site_id = request.GET.get('site_id')
        if selected_site_id is not None:
            # If site_id is explicitly provided (even if empty), use it
            if selected_site_id == '':
                # Clear site selection (All Sites)
                if 'selected_site_id' in request.session:
                    del request.session['selected_site_id']
                context['selected_site_id'] = None
            else:
                # Set specific site selection
                request.session['selected_site_id'] = selected_site_id
                context['selected_site_id'] = selected_site_id
        else:
            # No site_id in request, check session or default
            selected_site_id = request.session.get('selected_site_id')
            if not selected_site_id and user_profile.default_site:
                selected_site_id = str(user_profile.default_site.id)
                request.session['selected_site_id'] = selected_site_id
            context['selected_site_id'] = selected_site_id
        
        # Get the selected site object if we have a valid ID
        if context['selected_site_id']:
            try:
                selected_site = sites.get(id=context['selected_site_id'])
                context['selected_site'] = selected_site
            except (Location.DoesNotExist, ValueError):
                # Invalid site ID, clear it
                if 'selected_site_id' in request.session:
                    del request.session['selected_site_id']
                context['selected_site_id'] = None
    
    return context


def user_context(request):
    """
    Context processor to provide user profile information to all templates.
    """
    context = {
        'user_profile': None,
        'user_permissions': [],
    }
    
    if request.user.is_authenticated:
        # Ensure user has profile
        user_profile, created = UserProfile.objects.get_or_create(user=request.user)
        context['user_profile'] = user_profile
        
        # Get user permissions
        context['user_permissions'] = user_profile.get_permissions()
    
    return context


def version_context(request):
    """
    Context processor to provide version information to all templates.
    """
    try:
        from version import get_git_version
        version_info = get_git_version()
        return {
            'app_version': version_info['version'],
            'app_version_full': version_info['full_version'],
            'app_commit_hash': version_info['commit_hash'],
            'app_branch': version_info['branch'],
            'app_commit_date': version_info['commit_date'],
        }
    except ImportError:
        return {
            'app_version': 'v0.0.0',
            'app_version_full': 'v0.0.0 (Development)',
            'app_commit_hash': 'unknown',
            'app_branch': 'unknown',
            'app_commit_date': 'unknown',
        }