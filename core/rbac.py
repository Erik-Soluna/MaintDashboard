"""
Role-Based Access Control (RBAC) utilities and decorators.
"""

from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages
from django.http import JsonResponse
from django.conf import settings
from .models import Permission, Role, UserProfile


def permission_required(permission_codename, login_url=None, raise_exception=False):
    """
    Decorator for views that checks if user has a specific permission.
    
    Args:
        permission_codename: The permission codename to check (e.g., 'equipment.create')
        login_url: URL to redirect if user is not logged in
        raise_exception: Whether to raise PermissionDenied exception or redirect
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required(login_url=login_url)
        def _wrapped_view(request, *args, **kwargs):
            # Ensure user has profile
            profile, created = UserProfile.objects.get_or_create(user=request.user)
            
            # Check permission
            if not profile.has_permission(permission_codename):
                if raise_exception:
                    raise PermissionDenied(
                        f"You do not have permission to access this resource. "
                        f"Required permission: {permission_codename}"
                    )
                
                # Check if this is an AJAX request
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'error': 'Permission denied',
                        'message': f'You do not have permission to perform this action. Required permission: {permission_codename}'
                    }, status=403)
                
                messages.error(
                    request, 
                    f"You do not have permission to access this page. Required permission: {permission_codename}"
                )
                return redirect('core:dashboard')
            
            return view_func(request, *args, **kwargs)
        
        return _wrapped_view
    return decorator


def user_has_permission(user, permission_codename):
    """
    Check if a user has a specific permission.
    
    Args:
        user: Django User instance
        permission_codename: Permission codename to check
    
    Returns:
        bool: True if user has permission, False otherwise
    """
    try:
        profile = user.userprofile
        return profile.has_permission(permission_codename)
    except UserProfile.DoesNotExist:
        # Create profile if it doesn't exist
        profile = UserProfile.objects.create(user=user)
        return profile.has_permission(permission_codename)


def get_user_permissions(user):
    """
    Get all permissions for a user.
    
    Args:
        user: Django User instance
    
    Returns:
        QuerySet: User's permissions
    """
    try:
        profile = user.userprofile
        return profile.get_permissions()
    except UserProfile.DoesNotExist:
        # Create profile if it doesn't exist
        profile = UserProfile.objects.create(user=user)
        return profile.get_permissions()


def admin_required(view_func):
    """Decorator that requires admin permissions."""
    return permission_required('admin.full_access')(view_func)


def manager_required(view_func):
    """Decorator that requires manager permissions."""
    return permission_required('maintenance.manage_all')(view_func)


def equipment_create_required(view_func):
    """Decorator that requires equipment creation permissions."""
    return permission_required('equipment.create')(view_func)


def equipment_edit_required(view_func):
    """Decorator that requires equipment editing permissions."""
    return permission_required('equipment.edit')(view_func)


def equipment_delete_required(view_func):
    """Decorator that requires equipment deletion permissions."""
    return permission_required('equipment.delete')(view_func)


def maintenance_manage_required(view_func):
    """Decorator that requires maintenance management permissions."""
    return permission_required('maintenance.manage')(view_func)


def user_management_required(view_func):
    """Decorator that requires user management permissions."""
    return permission_required('users.manage')(view_func)


def settings_manage_required(view_func):
    """Decorator that requires settings management permissions."""
    return permission_required('settings.manage')(view_func)


def initialize_default_permissions():
    """Initialize default permissions and roles."""
    
    # Define default permissions
    default_permissions = [
        # Admin permissions
        ('admin.full_access', 'Full System Access', 'Complete access to all system functions', 'administration'),
        
        # Administration permissions (Settings, Users, System Config)
        ('administration.read', 'Administration Read', 'View system settings, users, and configuration', 'administration'),
        ('administration.write', 'Administration Write', 'Manage system settings, users, and configuration', 'administration'),
        
        # Events permissions  
        ('events.read', 'Events Read', 'View calendar events and schedules', 'events'),
        ('events.write', 'Events Write', 'Create, edit, and manage calendar events', 'events'),
        
        # Site Map permissions
        ('site_map.read', 'Site Map Read', 'View site map, locations, and equipment positions', 'site_map'),
        ('site_map.write', 'Site Map Write', 'Edit locations and equipment positions on site map', 'site_map'),
        
        # Maintenance/Calendar permissions
        ('maintenance_calendar.read', 'Maintenance/Calendar Read', 'View maintenance activities and calendar', 'maintenance_calendar'),
        ('maintenance_calendar.write', 'Maintenance/Calendar Write', 'Create and manage maintenance activities and calendar items', 'maintenance_calendar'),
        
        # Legacy Equipment permissions (for backward compatibility)
        ('equipment.view', 'View Equipment', 'View equipment details and lists', 'equipment'),
        ('equipment.create', 'Create Equipment', 'Create new equipment records', 'equipment'),
        ('equipment.edit', 'Edit Equipment', 'Edit existing equipment records', 'equipment'),
        ('equipment.delete', 'Delete Equipment', 'Delete equipment records', 'equipment'),
        ('equipment.documents.delete', 'Delete Documents', 'Delete equipment documents', 'equipment'),
        
        # Legacy Maintenance permissions (for backward compatibility)
        ('maintenance.view', 'View Maintenance', 'View maintenance activities and schedules', 'maintenance'),
        ('maintenance.create', 'Create Maintenance', 'Create maintenance activities', 'maintenance'),
        ('maintenance.edit', 'Edit Maintenance', 'Edit maintenance activities', 'maintenance'),
        ('maintenance.delete', 'Delete Maintenance', 'Delete maintenance activities', 'maintenance'),
        ('maintenance.assign', 'Assign Maintenance', 'Assign maintenance to users', 'maintenance'),
        ('maintenance.complete', 'Complete Maintenance', 'Mark maintenance as completed', 'maintenance'),
        ('maintenance.manage', 'Manage Maintenance', 'Manage own maintenance activities', 'maintenance'),
        ('maintenance.manage_all', 'Manage All Maintenance', 'Manage all maintenance activities', 'maintenance'),
        
        # Legacy User permissions (for backward compatibility)
        ('users.view', 'View Users', 'View user profiles and information', 'users'),
        ('users.manage', 'Manage Users', 'Create, edit, and manage user accounts', 'users'),
        
        # Legacy Settings permissions (for backward compatibility)
        ('settings.view', 'View Settings', 'View system settings', 'settings'),
        ('settings.manage', 'Manage Settings', 'Manage system settings and configuration', 'settings'),
        
        # Legacy Calendar permissions (for backward compatibility)
        ('calendar.view', 'View Calendar', 'View calendar events', 'calendar'),
        ('calendar.create', 'Create Calendar Events', 'Create calendar events', 'calendar'),
        ('calendar.edit', 'Edit Calendar Events', 'Edit calendar events', 'calendar'),
        ('calendar.delete', 'Delete Calendar Events', 'Delete calendar events', 'calendar'),
        
        # Legacy Reports permissions (for backward compatibility)
        ('reports.view', 'View Reports', 'View system reports', 'reports'),
        ('reports.generate', 'Generate Reports', 'Generate system reports', 'reports'),
        
        # Equipment Issues permissions
        ('issues.view', 'View Issues', 'View equipment issues', 'equipment'),
        ('issues.create', 'Create Issues', 'Create equipment issues', 'equipment'),
        ('issues.edit', 'Edit Issues', 'Edit equipment issues', 'equipment'),
        ('issues.delete', 'Delete Issues', 'Delete equipment issues', 'equipment'),
    ]
    
    # Create permissions
    created_permissions = []
    for codename, name, description, module in default_permissions:
        permission, created = Permission.objects.get_or_create(
            codename=codename,
            defaults={
                'name': name,
                'description': description,
                'module': module,
                'is_active': True
            }
        )
        created_permissions.append(permission)
    
    # Define default roles
    default_roles = [
        {
            'name': 'admin',
            'display_name': 'Administrator',
            'description': 'Full system access with all permissions',
            'is_system_role': True,
            'permissions': ['admin.full_access']
        },
        {
            'name': 'manager',
            'display_name': 'Maintenance Manager',
            'description': 'Full read/write access to all sections except administration',
            'is_system_role': True,
            'permissions': [
                'events.read', 'events.write',
                'site_map.read', 'site_map.write',
                'maintenance_calendar.read', 'maintenance_calendar.write',
                'administration.read',
                # Legacy permissions for backward compatibility
                'equipment.view', 'equipment.create', 'equipment.edit',
                'equipment.documents.delete',
                'issues.view', 'issues.create', 'issues.edit', 'issues.delete',
                'maintenance.view', 'maintenance.create', 'maintenance.edit', 
                'maintenance.assign', 'maintenance.complete', 'maintenance.manage_all',
                'calendar.view', 'calendar.create', 'calendar.edit', 'calendar.delete',
                'reports.view', 'reports.generate',
                'settings.view'
            ]
        },
        {
            'name': 'technician',
            'display_name': 'Maintenance Technician',
            'description': 'Read/write access to maintenance and events, read-only for other sections',
            'is_system_role': True,
            'permissions': [
                'events.read', 'events.write',
                'site_map.read',
                'maintenance_calendar.read', 'maintenance_calendar.write',
                # Legacy permissions for backward compatibility
                'equipment.view', 'equipment.edit',
                'issues.view', 'issues.create',
                'maintenance.view', 'maintenance.edit', 'maintenance.complete', 'maintenance.manage',
                'calendar.view', 'calendar.create', 'calendar.edit',
                'reports.view'
            ]
        },
        {
            'name': 'viewer',
            'display_name': 'Read-Only Viewer',
            'description': 'Read-only access to all sections',
            'is_system_role': True,
            'permissions': [
                'events.read',
                'site_map.read', 
                'maintenance_calendar.read',
                # Legacy permissions for backward compatibility
                'equipment.view',
                'maintenance.view',
                'calendar.view',
                'reports.view'
            ]
        },
        {
            'name': 'admin_user',
            'display_name': 'System Administrator',
            'description': 'Full read/write access to all sections including administration',
            'is_system_role': True,
            'permissions': [
                'events.read', 'events.write',
                'site_map.read', 'site_map.write',
                'maintenance_calendar.read', 'maintenance_calendar.write',
                'administration.read', 'administration.write',
                'admin.full_access'
            ]
        }
    ]
    
    # Create roles and assign permissions
    for role_data in default_roles:
        role, created = Role.objects.get_or_create(
            name=role_data['name'],
            defaults={
                'display_name': role_data['display_name'],
                'description': role_data['description'],
                'is_system_role': role_data['is_system_role'],
                'is_active': True
            }
        )
        
        # Assign permissions to role
        for perm_codename in role_data['permissions']:
            try:
                permission = Permission.objects.get(codename=perm_codename)
                role.permissions.add(permission)
            except Permission.DoesNotExist:
                print(f"Permission {perm_codename} not found for role {role.name}")
    
    return created_permissions


def assign_default_roles():
    """Assign default roles to users who don't have roles."""
    
    # Initialize permissions and roles first
    initialize_default_permissions()
    
    # Get default roles
    viewer_role = Role.objects.get(name='viewer')
    admin_role = Role.objects.get(name='admin')
    
    # Assign roles to users without profiles or roles
    from django.contrib.auth.models import User
    
    for user in User.objects.all():
        profile, created = UserProfile.objects.get_or_create(user=user)
        
        if not profile.role:
            # Assign admin role to superusers, viewer role to others
            if user.is_superuser:
                profile.role = admin_role
            else:
                profile.role = viewer_role
            profile.save()