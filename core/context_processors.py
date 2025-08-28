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
                # Clear site selection (All Sites) - use special marker
                request.session['selected_site_id'] = 'all'
                context['selected_site_id'] = None
            else:
                # Set specific site selection
                request.session['selected_site_id'] = selected_site_id
                context['selected_site_id'] = selected_site_id
        else:
            # No site_id in request, check session or default
            selected_site_id = request.session.get('selected_site_id')
            
            # If session has 'all', keep it as None (All Sites)
            if selected_site_id == 'all':
                context['selected_site_id'] = None
            elif selected_site_id:
                # Use session value
                context['selected_site_id'] = selected_site_id
            elif user_profile.default_site:
                # Use default site only if no explicit selection was made
                selected_site_id = str(user_profile.default_site.id)
                request.session['selected_site_id'] = selected_site_id
                context['selected_site_id'] = selected_site_id
            else:
                context['selected_site_id'] = None
        
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
        import json
        import os
        from django.conf import settings
        
        # First try to read from version.json file
        version_file = settings.BASE_DIR / "version.json"
        if version_file.exists():
            with open(version_file, 'r') as f:
                version_info = json.load(f)
            
            return {
                'app_version': version_info.get('version', 'v0.0.0'),
                'app_version_full': version_info.get('full_version', 'v0.0.0 (Development)'),
                'app_commit_hash': version_info.get('commit_hash', 'unknown'),
                'app_branch': version_info.get('branch', 'unknown'),
                'app_commit_date': version_info.get('commit_date', 'unknown'),
            }
        
        # Fallback to environment variables
        commit_count = os.environ.get('GIT_COMMIT_COUNT', '0')
        commit_hash = os.environ.get('GIT_COMMIT_HASH', 'unknown')
        branch = os.environ.get('GIT_BRANCH', 'unknown')
        commit_date = os.environ.get('GIT_COMMIT_DATE', 'unknown')
        
        if commit_hash != 'unknown':
            return {
                'app_version': f"v{commit_count}.{commit_hash}",
                'app_version_full': f"v{commit_count}.{commit_hash} ({branch}) - {commit_date}",
                'app_commit_hash': commit_hash,
                'app_branch': branch,
                'app_commit_date': commit_date,
            }
        
        # Final fallback to version.py module
        import importlib.util
        spec = importlib.util.spec_from_file_location("version_module", settings.BASE_DIR / "version.py")
        version_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(version_module)
        
        version_info = version_module.get_git_version()
        return {
            'app_version': version_info['version'],
            'app_version_full': version_info['full_version'],
            'app_commit_hash': version_info['commit_hash'],
            'app_branch': version_info['branch'],
            'app_commit_date': version_info['commit_date'],
        }
        
    except Exception as e:
        # Fallback version information
        return {
            'app_version': 'v0.0.0',
            'app_version_full': 'v0.0.0 (Development)',
            'app_commit_hash': 'unknown',
            'app_branch': 'unknown',
            'app_commit_date': 'unknown',
        }


def logo_processor(request):
    """Add the active logo to the template context"""
    try:
        from .models import Logo
        active_logo = Logo.objects.filter(is_active=True).first()
        return {'site_logo': active_logo}
    except Exception:
        return {'site_logo': None}