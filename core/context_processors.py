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
        if not selected_site_id:
            selected_site_id = request.session.get('selected_site_id')
        if not selected_site_id and user_profile.default_site:
            selected_site_id = str(user_profile.default_site.id)
        
        if selected_site_id:
            request.session['selected_site_id'] = selected_site_id
            context['selected_site_id'] = selected_site_id
            
            # Get the selected site object
            try:
                selected_site = sites.get(id=selected_site_id)
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