"""
Context processors for core app.
"""

from django.conf import settings
from .models import Location, UserProfile, BrandingSettings, CSSCustomization


def site_context(request):
    """
    Context processor to provide site information to all templates.
    """
    context = {
        'sites': [],
        'selected_site': None,
        'selected_site_id': None,
        'is_all_sites': False,
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
                context['is_all_sites'] = True
            else:
                # Set specific site selection
                request.session['selected_site_id'] = selected_site_id
                context['selected_site_id'] = selected_site_id
                context['is_all_sites'] = False
        else:
            # No site_id in request, check session or default
            selected_site_id = request.session.get('selected_site_id')
            
            # If session has 'all', keep it as None (All Sites)
            if selected_site_id == 'all':
                context['selected_site_id'] = None
                context['is_all_sites'] = True
            elif selected_site_id:
                # Use session value
                context['selected_site_id'] = selected_site_id
                context['is_all_sites'] = False
            elif user_profile.default_site:
                # Use default site only if no explicit selection was made
                selected_site_id = str(user_profile.default_site.id)
                request.session['selected_site_id'] = selected_site_id
                context['selected_site_id'] = selected_site_id
                context['is_all_sites'] = False
            else:
                context['selected_site_id'] = None
                context['is_all_sites'] = True
        
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
                context['is_all_sites'] = True
        
        # Add a display name for the current selection
        if context['is_all_sites']:
            context['current_site_display'] = 'All Sites'
        elif context['selected_site']:
            context['current_site_display'] = context['selected_site'].name
        else:
            context['current_site_display'] = 'All Sites'
    
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
        # Check if the logo table exists by trying to access it directly
        from django.db import connection
        from django.db.utils import ProgrammingError
        
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM core_logo LIMIT 1")
                logo_table_exists = True
        except (ProgrammingError, Exception):
            logo_table_exists = False
        
        if logo_table_exists:
            from .models import Logo
            active_logo = Logo.objects.filter(is_active=True).first()
            return {'site_logo': active_logo}
        else:
            return {'site_logo': None}
    except Exception:
        return {'site_logo': None}


def branding_processor(request):
    """Context processor for branding settings and CSS customizations"""
    try:
        # Check if the branding tables exist by trying to access them
        # This prevents errors when migrations haven't been run yet
        from django.db import connection
        from django.db.utils import ProgrammingError
        
        branding_table_exists = False
        css_table_exists = False
        
        try:
            # Try to access the tables directly - this will fail if they don't exist
            with connection.cursor() as cursor:
                # Check branding table
                cursor.execute("SELECT COUNT(*) FROM core_brandingsettings LIMIT 1")
                branding_table_exists = True
        except (ProgrammingError, Exception):
            branding_table_exists = False
        
        try:
            # Check CSS table
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM core_csscustomization LIMIT 1")
                css_table_exists = True
        except (ProgrammingError, Exception):
            css_table_exists = False
        
        branding = None
        css_customizations = []
        css_code = ''
        
        if branding_table_exists:
            try:
                branding = BrandingSettings.objects.get(is_active=True)
            except BrandingSettings.DoesNotExist:
                branding = None
        
        if css_table_exists:
            try:
                css_customizations = CSSCustomization.objects.filter(is_active=True).order_by('-priority', 'order')
                # Build CSS string from customizations
                for css in css_customizations:
                    css_code += f"/* {css.name} - {css.description} */\n{css.css_code}\n\n"
            except Exception:
                css_customizations = []
                css_code = ''
        
    except Exception:
        # If anything goes wrong, provide default values
        branding = None
        css_customizations = []
        css_code = ''
    
    return {
        'branding': branding,
        'css_customizations': css_customizations,
        'custom_css': css_code,
        'site_name': branding.site_name if branding else 'Maintenance Dashboard',
        'site_tagline': branding.site_tagline if branding else '',
        'window_title_prefix': branding.window_title_prefix if branding else '',
        'window_title_suffix': branding.window_title_suffix if branding else '',
        'header_brand_text': branding.header_brand_text if branding else 'Maintenance Dashboard',
        'navigation_overview_label': branding.navigation_overview_label if branding else 'Overview',
        'navigation_equipment_label': branding.navigation_equipment_label if branding else 'Equipment',
        'navigation_maintenance_label': branding.navigation_maintenance_label if branding else 'Maintenance',
        'navigation_calendar_label': branding.navigation_calendar_label if branding else 'Calendar',
        'navigation_map_label': branding.navigation_map_label if branding else 'Map',
        'navigation_settings_label': branding.navigation_settings_label if branding else 'Settings',
        'navigation_debug_label': branding.navigation_debug_label if branding else 'Debug',
        'footer_copyright_text': branding.footer_copyright_text if branding else '© 2025 Maintenance Dashboard. All rights reserved.',
        'footer_powered_by_text': branding.footer_powered_by_text if branding else 'Powered by Django',
        'primary_color': branding.primary_color if branding else '#4299e1',
        'secondary_color': branding.secondary_color if branding else '#2d3748',
        'accent_color': branding.accent_color if branding else '#3182ce',
        'header_background_color': branding.header_background_color if branding else '#0f1419',
        'header_text_color': branding.header_text_color if branding else '#ffffff',
        'header_border_color': branding.header_border_color if branding else '#4a5568',
        'navigation_background_color': branding.navigation_background_color if branding else '#2d3748',
        'navigation_text_color': branding.navigation_text_color if branding else '#e2e8f0',
        'navigation_hover_color': branding.navigation_hover_color if branding else '#4299e1',
        'content_background_color': branding.content_background_color if branding else '#1a2238',
        'content_text_color': branding.content_text_color if branding else '#e2e8f0',
        'card_background_color': branding.card_background_color if branding else '#2d3748',
        'card_border_color': branding.card_border_color if branding else '#4a5568',
        'button_primary_color': branding.button_primary_color if branding else '#4299e1',
        'button_primary_text_color': branding.button_primary_text_color if branding else '#ffffff',
        'button_secondary_color': branding.button_secondary_color if branding else '#718096',
        'button_secondary_text_color': branding.button_secondary_text_color if branding else '#ffffff',
        'form_background_color': branding.form_background_color if branding else '#2d3748',
        'form_border_color': branding.form_border_color if branding else '#4a5568',
        'form_text_color': branding.form_text_color if branding else '#e2e8f0',
        'success_color': branding.success_color if branding else '#48bb78',
        'warning_color': branding.warning_color if branding else '#ed8936',
        'danger_color': branding.danger_color if branding else '#f56565',
        'info_color': branding.info_color if branding else '#4299e1',
        'dropdown_background_color': branding.dropdown_background_color if branding else '#2d3748',
        'dropdown_background_opacity': float(branding.dropdown_background_opacity) if branding else 0.95,
        'dropdown_text_color': branding.dropdown_text_color if branding else '#e2e8f0',
        'dropdown_border_color': branding.dropdown_border_color if branding else '#4a5568',
        'dropdown_hover_background_color': branding.dropdown_hover_background_color if branding else '#4a5568',
        'dropdown_hover_text_color': branding.dropdown_hover_text_color if branding else '#ffffff',
    }