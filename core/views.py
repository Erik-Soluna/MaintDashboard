"""
Views for core app.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth.models import User
from equipment.models import Equipment
from maintenance.models import MaintenanceActivity
from events.models import CalendarEvent
from core.models import Location, EquipmentCategory, Role, Permission, UserProfile
from core.forms import LocationForm, EquipmentCategoryForm
from django.utils import timezone
from django.db.models import Q, Count
from datetime import datetime, timedelta, date
from django.http import JsonResponse, HttpResponseRedirect
from django.core.paginator import Paginator
from django.urls import reverse
import json
import csv
import io
import re
from django.http import HttpResponse
from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods


def natural_sort_key(text):
    """Generate a key for natural sorting (handles numbers in strings correctly)."""
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r'(\d+)', str(text))]


@login_required
def dashboard(request):
    """Enhanced dashboard view with comprehensive maintenance, calendar, and pod status data."""
    
    # Ensure user has a profile
    from core.models import UserProfile
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    # Get selected site from request, session, or user default
    selected_site_id = request.GET.get('site_id')
    if not selected_site_id:
        selected_site_id = request.session.get('selected_site_id')
    if not selected_site_id and user_profile.default_site:
        selected_site_id = str(user_profile.default_site.id)
    
    if selected_site_id:
        request.session['selected_site_id'] = selected_site_id
    
    # Get all sites for the site selector
    sites = Location.objects.filter(is_site=True, is_active=True).order_by('name')
    selected_site = None
    if selected_site_id:
        try:
            selected_site = sites.get(id=selected_site_id)
        except Location.DoesNotExist:
            pass
    
    # Get today's date for various calculations
    today = timezone.now().date()
    urgent_cutoff = today + timedelta(days=7)
    upcoming_cutoff = today + timedelta(days=30)
    
    # Base equipment and maintenance queries
    equipment_query = Equipment.objects.all()
    maintenance_query = MaintenanceActivity.objects.all()
    calendar_query = CalendarEvent.objects.all()
    
    # Apply site filtering if selected
    if selected_site:
        site_filter = Q(location__parent_location=selected_site) | Q(location=selected_site)
        equipment_query = equipment_query.filter(site_filter)
        maintenance_query = maintenance_query.filter(Q(equipment__location__parent_location=selected_site) | Q(equipment__location=selected_site))
        calendar_query = calendar_query.filter(Q(equipment__location__parent_location=selected_site) | Q(equipment__location=selected_site))
    
    # Get locations (pods) with natural sorting
    if selected_site:
        locations = Location.objects.filter(
            parent_location=selected_site,
            is_active=True
        ).select_related('parent_location')
        # Apply natural sorting to pod names
        locations = sorted(locations, key=lambda loc: natural_sort_key(loc.name))
    else:
        # Show top-level locations if no site selected
        locations = Location.objects.filter(
            is_site=False,
            is_active=True
        ).select_related('parent_location')[:8]  # Limit for layout
        locations = sorted(locations, key=lambda loc: natural_sort_key(loc.name))
    
    # === URGENT ITEMS ===
    urgent_maintenance = maintenance_query.filter(
        Q(scheduled_end__lte=urgent_cutoff) & Q(scheduled_end__gte=today),
        status__in=['pending', 'in_progress', 'overdue']
    ).select_related('equipment', 'equipment__location').order_by('scheduled_end')[:15]
    
    urgent_calendar = calendar_query.filter(
        event_date__lte=urgent_cutoff,
        event_date__gte=today,
        is_completed=False
    ).select_related('equipment', 'equipment__location').order_by('event_date')[:10]
    
    # === UPCOMING ITEMS ===
    upcoming_maintenance = maintenance_query.filter(
        scheduled_end__gt=urgent_cutoff,
        scheduled_end__lte=upcoming_cutoff,
        status__in=['pending', 'scheduled']
    ).select_related('equipment', 'equipment__location').order_by('scheduled_end')[:15]
    
    upcoming_calendar = calendar_query.filter(
        event_date__gt=urgent_cutoff,
        event_date__lte=upcoming_cutoff,
        is_completed=False
    ).select_related('equipment', 'equipment__location').order_by('event_date')[:10]
    
    # === POD STATUS DATA ===
    pod_status_data = []
    for location in locations:
        # Equipment counts by status
        location_equipment = equipment_query.filter(location=location)
        
        # Maintenance statistics for this pod
        pod_maintenance = maintenance_query.filter(equipment__location=location)
        
        # Calendar events for this pod
        pod_calendar = calendar_query.filter(equipment__location=location)
        
        # Current status
        equipment_in_maintenance = location_equipment.filter(status='maintenance').count()
        active_equipment = location_equipment.filter(status='active').count()
        total_equipment = location_equipment.count()
        
        # Upcoming maintenance in next 7 days
        upcoming_maintenance_count = pod_maintenance.filter(
            scheduled_start__date__lte=urgent_cutoff,
            scheduled_start__date__gte=today,
            status__in=['scheduled', 'pending']
        ).count()
        
        # Recent activities (last 30 days)
        recent_activities = pod_maintenance.filter(
            actual_end__gte=today - timedelta(days=30),
            status='completed'
        ).order_by('-actual_end')[:3]
        
        # Next scheduled events
        next_events = pod_calendar.filter(
            event_date__gte=today,
            is_completed=False
        ).order_by('event_date')[:3]
        
        # Calculate pod health status
        if equipment_in_maintenance > 0:
            pod_status = 'maintenance'
        elif upcoming_maintenance_count > 2:
            pod_status = 'warning'
        elif active_equipment == total_equipment:
            pod_status = 'healthy'
        else:
            pod_status = 'caution'
        
        pod_status_data.append({
            'location': location,
            'pod_status': pod_status,
            'total_equipment': total_equipment,
            'active_equipment': active_equipment,
            'equipment_in_maintenance': equipment_in_maintenance,
            'upcoming_maintenance_count': upcoming_maintenance_count,
            'recent_activities': recent_activities,
            'next_events': next_events,
        })
    
    # === OVERALL SITE STATISTICS ===
    site_stats = {
        'total_equipment': equipment_query.count(),
        'active_equipment': equipment_query.filter(status='active').count(),
        'equipment_in_maintenance': equipment_query.filter(status='maintenance').count(),
        'inactive_equipment': equipment_query.filter(status='inactive').count(),
        
        # Maintenance statistics
        'total_maintenance_activities': maintenance_query.count(),
        'pending_maintenance': maintenance_query.filter(status='pending').count(),
        'in_progress_maintenance': maintenance_query.filter(status='in_progress').count(),
        'overdue_maintenance': maintenance_query.filter(
            scheduled_end__lt=timezone.now(),
            status__in=['pending', 'scheduled']
        ).count(),
        'completed_this_month': maintenance_query.filter(
            status='completed',
            actual_end__gte=today.replace(day=1)
        ).count(),
        
        # Calendar statistics
        'total_calendar_events': calendar_query.count(),
        'events_this_week': calendar_query.filter(
            event_date__gte=today,
            event_date__lt=today + timedelta(days=7)
        ).count(),
        'completed_events': calendar_query.filter(is_completed=True).count(),
        'pending_events': calendar_query.filter(
            is_completed=False,
            event_date__gte=today
        ).count(),
    }
    
    # Calculate overall site health
    equipment_health_ratio = site_stats['active_equipment'] / max(site_stats['total_equipment'], 1)
    maintenance_load = site_stats['pending_maintenance'] + site_stats['overdue_maintenance']
    
    if site_stats['overdue_maintenance'] > 0:
        site_health = 'critical'
    elif maintenance_load > 10 or equipment_health_ratio < 0.8:
        site_health = 'warning'
    elif equipment_health_ratio > 0.95 and maintenance_load < 5:
        site_health = 'excellent'
    else:
        site_health = 'good'
    
    context = {
        'sites': sites,
        'selected_site': selected_site,
        'site_health': site_health,
        'site_stats': site_stats,
        
        # Urgent and upcoming items
        'urgent_maintenance': urgent_maintenance,
        'urgent_calendar': urgent_calendar,
        'upcoming_maintenance': upcoming_maintenance,
        'upcoming_calendar': upcoming_calendar,
        
        # Pod status data (naturally sorted)
        'pod_status_data': pod_status_data,
        'total_pods': len(pod_status_data),
        
        # Legacy data for backwards compatibility
        'locations': locations,
        'urgent_items': urgent_maintenance,
        'upcoming_items': upcoming_maintenance,
        'total_equipment': site_stats['total_equipment'],
        'active_equipment': site_stats['active_equipment'],
        'pending_maintenance': site_stats['pending_maintenance'],
    }
    return render(request, 'core/dashboard.html', context)


@login_required
def profile_view(request):
    """User profile view."""
    # Ensure user has a profile
    from core.models import UserProfile
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        action = request.POST.get('action', 'update_profile')
        
        if action == 'update_profile':
            user = request.user
            user.first_name = request.POST.get('first_name', '')
            user.last_name = request.POST.get('last_name', '')
            user.email = request.POST.get('email', '')
            user.save()
            
            profile = user.userprofile
            profile.phone_number = request.POST.get('phone_number', '')
            profile.department = request.POST.get('department', '')
            
            # Handle default site selection
            default_site_id = request.POST.get('default_site')
            if default_site_id:
                try:
                    profile.default_site = Location.objects.get(id=default_site_id, is_site=True)
                except Location.DoesNotExist:
                    profile.default_site = None
            else:
                profile.default_site = None
            
            # Handle default location selection
            default_location_id = request.POST.get('default_location')
            if default_location_id:
                try:
                    profile.default_location = Location.objects.get(id=default_location_id)
                except Location.DoesNotExist:
                    profile.default_location = None
            else:
                profile.default_location = None
            
            # Handle theme preference
            theme_preference = request.POST.get('theme_preference', 'dark')
            if theme_preference in ['dark', 'light']:
                profile.theme_preference = theme_preference
            
            # Handle notification preferences
            profile.notifications_enabled = 'notifications_enabled' in request.POST
            profile.email_notifications = 'email_notifications' in request.POST
            profile.sms_notifications = 'sms_notifications' in request.POST
            
            profile.save()
            
            messages.success(request, 'Profile updated successfully!')
            return redirect('core:profile')
            
        elif action == 'change_password':
            from django.contrib.auth import update_session_auth_hash
            from django.contrib.auth.forms import PasswordChangeForm
            
            form = PasswordChangeForm(request.user, request.POST)
            if form.is_valid():
                user = form.save()
                update_session_auth_hash(request, user)  # Important for keeping user logged in
                messages.success(request, 'Password changed successfully!')
                return redirect('core:profile')
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f'{field}: {error}')
    
    # Get data for the template
    sites = Location.objects.filter(is_site=True, is_active=True).order_by('name')
    locations = Location.objects.filter(is_active=True).order_by('name')
    
    context = {
        'user': request.user,
        'sites': sites,
        'locations': locations,
    }
    return render(request, 'core/profile.html', context)


def is_staff_or_superuser(user):
    """Check if user is staff or superuser."""
    return user.is_staff or user.is_superuser


@login_required
def map_view(request):
    """Map view showing all locations and equipment."""
    locations = Location.objects.filter(is_active=True).select_related('parent_location')
    equipment = Equipment.objects.filter(is_active=True).select_related('location')
    
    context = {
        'locations': locations,
        'equipment': equipment,
    }
    return render(request, 'core/map.html', context)


@login_required
@user_passes_test(is_staff_or_superuser)
def settings_view(request):
    """General settings view with user preferences."""
    # Ensure user has a profile
    from core.models import UserProfile
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        # Handle user preferences update
        user = request.user
        profile = user_profile
        
        # Update user preferences
        profile.default_location_id = request.POST.get('default_location')
        profile.notifications_enabled = 'notifications_enabled' in request.POST
        profile.email_notifications = 'email_notifications' in request.POST
        profile.sms_notifications = 'sms_notifications' in request.POST
        profile.save()
        
        messages.success(request, 'Settings updated successfully!')
        return redirect('core:settings')
    
    locations = Location.objects.filter(is_active=True).order_by('name')
    context = {
        'locations': locations,
        'user': request.user,
    }
    return render(request, 'core/settings.html', context)


@login_required
@user_passes_test(is_staff_or_superuser)
def locations_settings(request):
    """Locations management view."""
    locations = Location.objects.all().order_by('name')
    sites = Location.objects.filter(is_site=True, is_active=True).order_by('name')
    
    context = {
        'locations': locations,
        'sites': sites,
    }
    return render(request, 'core/locations_settings.html', context)


@login_required
@user_passes_test(is_staff_or_superuser)
def equipment_items_settings(request):
    """Equipment items management view."""
    equipment_items = Equipment.objects.select_related('location', 'category').order_by('name')
    categories = EquipmentCategory.objects.filter(is_active=True).order_by('name')
    locations = Location.objects.filter(is_active=True).order_by('name')
    
    # Pagination
    paginator = Paginator(equipment_items, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'equipment_items': equipment_items,
        'categories': categories,
        'locations': locations,
    }
    return render(request, 'core/equipment_items_settings.html', context)


@login_required
@user_passes_test(is_staff_or_superuser)
def user_management(request):
    """Enhanced user management view with role assignment."""
    if request.method == 'POST':
        action = request.POST.get('action')
        user_id = request.POST.get('user_id')
        
        if action == 'toggle_active' and user_id:
            user = get_object_or_404(User, id=user_id)
            user.is_active = not user.is_active
            user.save()
            status = 'activated' if user.is_active else 'deactivated'
            messages.success(request, f'User {user.username} has been {status}.')
        
        elif action == 'toggle_staff' and user_id:
            user = get_object_or_404(User, id=user_id)
            user.is_staff = not user.is_staff
            user.save()
            status = 'granted' if user.is_staff else 'revoked'
            messages.success(request, f'Staff privileges {status} for {user.username}.')
        
        elif action == 'assign_role' and user_id:
            user = get_object_or_404(User, id=user_id)
            role_id = request.POST.get('role_id')
            
            # Get or create user profile
            profile, created = UserProfile.objects.get_or_create(user=user)
            
            if role_id:
                role = get_object_or_404(Role, id=role_id)
                profile.role = role
                profile.save()
                messages.success(request, f'Role "{role.display_name}" assigned to {user.username}.')
            else:
                profile.role = None
                profile.save()
                messages.success(request, f'Role removed from {user.username}.')
        
        return redirect('core:user_management')
    
    users = User.objects.all().select_related('userprofile', 'userprofile__role').order_by('username')
    roles = Role.objects.filter(is_active=True).order_by('display_name')
    
    # Get user statistics
    total_users = users.count()
    active_users = users.filter(is_active=True).count()
    staff_users = users.filter(is_staff=True).count()
    superusers = users.filter(is_superuser=True).count()
    
    # Pagination
    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'users': users,
        'roles': roles,
        'total_users': total_users,
        'active_users': active_users,
        'staff_users': staff_users,
        'superusers': superusers,
    }
    return render(request, 'core/user_management.html', context)


# API endpoints for settings management
@login_required
@user_passes_test(is_staff_or_superuser)
def locations_api(request):
    """API endpoint for locations management."""
    if request.method == 'GET':
        locations = Location.objects.all().values(
            'id', 'name', 'description', 'is_site', 'is_active', 'parent_location__name'
        )
        return JsonResponse(list(locations), safe=False)
    
    elif request.method == 'POST':
        data = json.loads(request.body)
        location = Location.objects.create(
            name=data.get('name'),
            description=data.get('description', ''),
            is_site=data.get('is_site', False),
            parent_location_id=data.get('parent_location_id')
        )
        return JsonResponse({
            'id': location.id,
            'name': location.name,
            'message': 'Location created successfully'
        })


@login_required
@user_passes_test(is_staff_or_superuser)
def location_detail_api(request, location_id):
    """API endpoint for individual location management."""
    location = get_object_or_404(Location, id=location_id)
    
    if request.method == 'PUT':
        data = json.loads(request.body)
        location.name = data.get('name', location.name)
        location.description = data.get('description', location.description)
        location.is_site = data.get('is_site', location.is_site)
        location.is_active = data.get('is_active', location.is_active)
        if data.get('parent_location_id'):
            location.parent_location_id = data.get('parent_location_id')
        location.save()
        return JsonResponse({'message': 'Location updated successfully'})
    
    elif request.method == 'DELETE':
        location_name = location.name
        
        # Check if location has any equipment or child locations
        if location.equipment.exists():
            return JsonResponse({
                'error': f'Cannot delete location "{location_name}" because it has equipment assigned to it.'
            }, status=400)
        
        if location.child_locations.exists():
            return JsonResponse({
                'error': f'Cannot delete location "{location_name}" because it has child locations.'
            }, status=400)
        
        location.delete()
        return JsonResponse({'message': f'Location "{location_name}" deleted successfully!'})


@login_required
@user_passes_test(is_staff_or_superuser)
def equipment_items_api(request):
    """API endpoint for equipment items management."""
    if request.method == 'GET':
        equipment = Equipment.objects.select_related('location', 'category').values(
            'id', 'name', 'asset_tag', 'location__name', 'category__name', 
            'status', 'is_active', 'serial_number'
        )
        return JsonResponse(list(equipment), safe=False)


@login_required
@user_passes_test(is_staff_or_superuser)
def users_api(request):
    """API endpoint for user management."""
    if request.method == 'GET':
        users = User.objects.select_related('userprofile').values(
            'id', 'username', 'first_name', 'last_name', 'email',
            'is_active', 'is_staff', 'is_superuser', 'last_login',
            'userprofile__department', 'userprofile__phone_number'
        )
        return JsonResponse(list(users), safe=False)


@login_required
@user_passes_test(is_staff_or_superuser)
def roles_permissions_management(request):
    """Role and permission management view."""
    roles = Role.objects.all().prefetch_related('permissions').order_by('display_name')
    permissions = Permission.objects.filter(is_active=True).order_by('module', 'name')
    
    # Group permissions by module
    permissions_by_module = {}
    for permission in permissions:
        if permission.module not in permissions_by_module:
            permissions_by_module[permission.module] = []
        permissions_by_module[permission.module].append(permission)
    
    context = {
        'roles': roles,
        'permissions': permissions,
        'permissions_by_module': permissions_by_module,
    }
    return render(request, 'core/roles_permissions_management.html', context)


@login_required
@user_passes_test(is_staff_or_superuser)
def role_detail_api(request, role_id):
    """API endpoint for role management."""
    role = get_object_or_404(Role, id=role_id)
    
    if request.method == 'GET':
        # Return role details with permissions
        permissions = list(role.permissions.values('id', 'name', 'codename', 'module'))
        return JsonResponse({
            'id': role.id,
            'name': role.name,
            'display_name': role.display_name,
            'description': role.description,
            'is_active': role.is_active,
            'is_system_role': role.is_system_role,
            'permissions': permissions
        })
    
    elif request.method == 'PUT':
        # Update role
        data = json.loads(request.body)
        
        role.name = data.get('name', role.name)
        role.display_name = data.get('display_name', role.display_name)
        role.description = data.get('description', role.description)
        role.is_active = data.get('is_active', role.is_active)
        role.save()
        
        # Update permissions
        if 'permission_ids' in data:
            permission_ids = data['permission_ids']
            role.permissions.set(permission_ids)
        
        return JsonResponse({'message': 'Role updated successfully'})
    
    elif request.method == 'DELETE':
        # Delete role (only if not system role)
        if role.is_system_role:
            return JsonResponse({'error': 'Cannot delete system role'}, status=400)
        
        # Check if any users have this role
        users_with_role = UserProfile.objects.filter(role=role).count()
        if users_with_role > 0:
            return JsonResponse({
                'error': f'Cannot delete role. {users_with_role} users are assigned to this role.'
            }, status=400)
        
        role.delete()
        return JsonResponse({'message': 'Role deleted successfully'})


@login_required
@user_passes_test(is_staff_or_superuser)
def roles_api(request):
    """API endpoint for role management."""
    if request.method == 'GET':
        roles = Role.objects.all().values(
            'id', 'name', 'display_name', 'description', 'is_active', 'is_system_role'
        )
        return JsonResponse(list(roles), safe=False)
    
    elif request.method == 'POST':
        # Create new role
        data = json.loads(request.body)
        
        role = Role.objects.create(
            name=data.get('name'),
            display_name=data.get('display_name'),
            description=data.get('description', ''),
            is_active=data.get('is_active', True),
            created_by=request.user,
            updated_by=request.user
        )
        
        # Assign permissions
        if 'permission_ids' in data:
            permission_ids = data['permission_ids']
            role.permissions.set(permission_ids)
        
        return JsonResponse({
            'id': role.id,
            'name': role.name,
            'display_name': role.display_name,
            'message': 'Role created successfully'
        })


@login_required
@user_passes_test(is_staff_or_superuser)
def add_location(request):
    """Add new location."""
    if request.method == 'POST':
        form = LocationForm(request.POST)
        if form.is_valid():
            location = form.save(commit=False)
            location.created_by = request.user
            location.updated_by = request.user
            location.save()
            
            messages.success(request, f'Location "{location.name}" added successfully!')
            return redirect('core:locations_settings')
    else:
        form = LocationForm()
    
    context = {
        'form': form,
        'title': 'Add New Location',
    }
    return render(request, 'core/add_location.html', context)


@login_required
@user_passes_test(is_staff_or_superuser)
def edit_location(request, location_id):
    """Edit existing location."""
    location = get_object_or_404(Location, id=location_id)
    
    if request.method == 'POST':
        form = LocationForm(request.POST, instance=location)
        if form.is_valid():
            location = form.save(commit=False)
            location.updated_by = request.user
            location.save()
            
            messages.success(request, f'Location "{location.name}" updated successfully!')
            return redirect('core:locations_settings')
    else:
        form = LocationForm(instance=location)
    
    context = {
        'form': form,
        'location': location,
        'title': 'Edit Location',
    }
    return render(request, 'core/edit_location.html', context)


@login_required
@user_passes_test(is_staff_or_superuser)
def add_equipment_category(request):
    """Add new equipment category."""
    if request.method == 'POST':
        form = EquipmentCategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.created_by = request.user
            category.updated_by = request.user
            category.save()
            
            messages.success(request, f'Equipment category "{category.name}" added successfully!')
            return redirect('core:equipment_categories_settings')
    else:
        form = EquipmentCategoryForm()
    
    context = {
        'form': form,
        'title': 'Add New Equipment Category',
    }
    return render(request, 'core/add_equipment_category.html', context)


@login_required
@user_passes_test(is_staff_or_superuser)
def edit_equipment_category(request, category_id):
    """Edit existing equipment category."""
    category = get_object_or_404(EquipmentCategory, id=category_id)
    
    if request.method == 'POST':
        form = EquipmentCategoryForm(request.POST, instance=category)
        if form.is_valid():
            category = form.save(commit=False)
            category.updated_by = request.user
            category.save()
            
            messages.success(request, f'Equipment category "{category.name}" updated successfully!')
            return redirect('core:equipment_categories_settings')
    else:
        form = EquipmentCategoryForm(instance=category)
    
    context = {
        'form': form,
        'category': category,
        'title': 'Edit Equipment Category',
    }
    return render(request, 'core/edit_equipment_category.html', context)


@login_required
@user_passes_test(is_staff_or_superuser)
def equipment_categories_settings(request):
    """Equipment categories management view."""
    categories = EquipmentCategory.objects.all().order_by('name')
    
    # Pagination
    paginator = Paginator(categories, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'categories': categories,
    }
    return render(request, 'core/equipment_categories_settings.html', context)


@login_required
def export_sites_csv(request):
    """Export sites data to CSV file."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="sites_export.csv"'
    
    writer = csv.writer(response)
    
    # Write header
    writer.writerow([
        'Name',
        'Latitude',
        'Longitude',
        'Address',
        'Is Active',
        'Created At'
    ])
    
    # Get sites data (locations marked as sites)
    from .models import Location
    sites = Location.objects.filter(is_site=True).order_by('name')
    
    # Write data rows
    for site in sites:
        writer.writerow([
            site.name,
            site.latitude or '',
            site.longitude or '',
            site.address,
            site.is_active,
            site.created_at.isoformat() if site.created_at else ''
        ])
    
    return response


@login_required
@require_http_methods(["POST"])
def import_sites_csv(request):
    """Import sites data from CSV file."""
    if 'csv_file' not in request.FILES:
        messages.error(request, 'No CSV file provided.')
        return redirect('core:locations_settings')
    
    csv_file = request.FILES['csv_file']
    
    if not csv_file.name.endswith('.csv'):
        messages.error(request, 'Please upload a CSV file.')
        return redirect('core:locations_settings')
    
    try:
        # Read CSV file
        file_data = csv_file.read().decode('utf-8')
        csv_data = csv.reader(io.StringIO(file_data))
        
        # Skip header row
        header = next(csv_data)
        
        # Import data
        from .models import Location
        
        imported_count = 0
        error_count = 0
        
        for row_num, row in enumerate(csv_data, start=2):
            try:
                if len(row) < 1:  # Must have at least name
                    continue
                
                name = row[0].strip()
                if not name:
                    continue
                
                # Check if site already exists
                if Location.objects.filter(name=name, is_site=True).exists():
                    error_count += 1
                    continue
                
                # Parse data
                latitude = None
                longitude = None
                
                try:
                    if len(row) > 1 and row[1].strip():
                        latitude = float(row[1].strip())
                except (ValueError, IndexError):
                    pass
                
                try:
                    if len(row) > 2 and row[2].strip():
                        longitude = float(row[2].strip())
                except (ValueError, IndexError):
                    pass
                
                address = row[3].strip() if len(row) > 3 else ''
                is_active = True
                if len(row) > 4:
                    is_active = str(row[4]).lower() in ['true', '1', 'yes', 'active']
                
                # Create site
                Location.objects.create(
                    name=name,
                    is_site=True,
                    latitude=latitude,
                    longitude=longitude,
                    address=address,
                    is_active=is_active,
                    created_by=request.user
                )
                
                imported_count += 1
                
            except Exception as e:
                error_count += 1
                print(f"Error importing site row {row_num}: {str(e)}")
                continue
        
        if imported_count > 0:
            messages.success(request, f'Successfully imported {imported_count} sites.')
        if error_count > 0:
            messages.warning(request, f'{error_count} rows had errors and were skipped.')
            
    except Exception as e:
        messages.error(request, f'Error reading CSV file: {str(e)}')
    
    return redirect('core:locations_settings')


@login_required
def profile(request):
    """Alias for profile_view to match URL pattern."""
    return profile_view(request)


@login_required
@user_passes_test(is_staff_or_superuser)
def settings(request):
    """Alias for settings_view to match URL pattern."""
    return settings_view(request)


@login_required
@user_passes_test(is_staff_or_superuser)
def delete_location(request, location_id):
    """Delete location."""
    location = get_object_or_404(Location, id=location_id)
    
    if request.method == 'POST':
        location_name = location.name
        
        # Check if location has any equipment or child locations
        if location.equipment.exists():
            messages.error(request, f'Cannot delete location "{location_name}" because it has equipment assigned to it.')
            return redirect('core:locations_settings')
        
        if location.child_locations.exists():
            messages.error(request, f'Cannot delete location "{location_name}" because it has child locations.')
            return redirect('core:locations_settings')
        
        location.delete()
        messages.success(request, f'Location "{location_name}" deleted successfully!')
        return redirect('core:locations_settings')
    
    context = {'location': location}
    return render(request, 'core/delete_location.html', context)


@login_required
@user_passes_test(is_staff_or_superuser)
def delete_equipment_category(request, category_id):
    """Delete equipment category."""
    category = get_object_or_404(EquipmentCategory, id=category_id)
    
    if request.method == 'POST':
        category_name = category.name
        
        # Check if category has any equipment
        if category.equipment.exists():
            messages.error(request, f'Cannot delete category "{category_name}" because it has equipment assigned to it.')
            return redirect('core:equipment_categories_settings')
        
        category.delete()
        messages.success(request, f'Equipment category "{category_name}" deleted successfully!')
        return redirect('core:equipment_categories_settings')
    
    context = {'category': category}
    return render(request, 'core/delete_equipment_category.html', context)


@login_required
def export_locations_csv(request):
    """Export all locations (map data) to CSV file."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="locations_export.csv"'
    
    writer = csv.writer(response)
    
    # Write header
    writer.writerow([
        'Name',
        'Parent Location',
        'Is Site',
        'Latitude',
        'Longitude',
        'Address',
        'Is Active',
        'Full Path',
        'Created At'
    ])
    
    # Get all locations
    from .models import Location
    locations = Location.objects.select_related('parent_location').order_by('name')
    
    # Apply site filter if provided
    site_id = request.GET.get('site_id')
    if site_id:
        from django.db.models import Q
        locations = locations.filter(
            Q(parent_location_id=site_id) | Q(id=site_id)
        )
    
    # Write data rows
    for location in locations:
        writer.writerow([
            location.name,
            location.parent_location.name if location.parent_location else '',
            location.is_site,
            location.latitude or '',
            location.longitude or '',
            location.address,
            location.is_active,
            location.get_full_path(),
            location.created_at.isoformat() if location.created_at else ''
        ])
    
    return response


@login_required
@require_http_methods(["POST"])
def import_locations_csv(request):
    """Import locations (map data) from CSV file."""
    if 'csv_file' not in request.FILES:
        messages.error(request, 'No CSV file provided.')
        return redirect('core:locations_settings')
    
    csv_file = request.FILES['csv_file']
    
    if not csv_file.name.endswith('.csv'):
        messages.error(request, 'Please upload a CSV file.')
        return redirect('core:locations_settings')
    
    try:
        # Read CSV file
        file_data = csv_file.read().decode('utf-8')
        csv_data = csv.reader(io.StringIO(file_data))
        
        # Skip header row
        header = next(csv_data)
        
        # Import data
        from .models import Location
        
        imported_count = 0
        error_count = 0
        
        # First pass: create all locations without parent relationships
        locations_to_create = []
        for row_num, row in enumerate(csv_data, start=2):
            try:
                if len(row) < 1:  # Must have at least name
                    continue
                
                name = row[0].strip()
                if not name:
                    continue
                
                parent_name = row[1].strip() if len(row) > 1 else ''
                is_site = str(row[2]).lower() in ['true', '1', 'yes'] if len(row) > 2 else False
                
                # Parse coordinates
                latitude = None
                longitude = None
                
                try:
                    if len(row) > 3 and row[3].strip():
                        latitude = float(row[3].strip())
                except (ValueError, IndexError):
                    pass
                
                try:
                    if len(row) > 4 and row[4].strip():
                        longitude = float(row[4].strip())
                except (ValueError, IndexError):
                    pass
                
                address = row[5].strip() if len(row) > 5 else ''
                is_active = True
                if len(row) > 6:
                    is_active = str(row[6]).lower() in ['true', '1', 'yes', 'active']
                
                locations_to_create.append({
                    'name': name,
                    'parent_name': parent_name,
                    'is_site': is_site,
                    'latitude': latitude,
                    'longitude': longitude,
                    'address': address,
                    'is_active': is_active,
                    'row_num': row_num
                })
                
            except Exception as e:
                error_count += 1
                print(f"Error parsing location row {row_num}: {str(e)}")
                continue
        
        # Second pass: create locations, handling parent relationships
        created_locations = {}
        
        # First create all sites (no parents)
        for location_data in locations_to_create:
            if location_data['is_site']:
                try:
                    # Check if location already exists
                    if Location.objects.filter(name=location_data['name']).exists():
                        error_count += 1
                        continue
                    
                    location = Location.objects.create(
                        name=location_data['name'],
                        is_site=True,
                        latitude=location_data['latitude'],
                        longitude=location_data['longitude'],
                        address=location_data['address'],
                        is_active=location_data['is_active'],
                        created_by=request.user
                    )
                    
                    created_locations[location_data['name']] = location
                    imported_count += 1
                    
                except Exception as e:
                    error_count += 1
                    print(f"Error creating site {location_data['name']}: {str(e)}")
                    continue
        
        # Then create non-site locations with parent relationships
        for location_data in locations_to_create:
            if not location_data['is_site']:
                try:
                    # Check if location already exists
                    if Location.objects.filter(name=location_data['name']).exists():
                        error_count += 1
                        continue
                    
                    parent_location = None
                    if location_data['parent_name']:
                        # Look for parent in created locations first
                        parent_location = created_locations.get(location_data['parent_name'])
                        if not parent_location:
                            # Look for existing parent
                            try:
                                parent_location = Location.objects.get(name=location_data['parent_name'])
                            except Location.DoesNotExist:
                                error_count += 1
                                continue
                    
                    location = Location.objects.create(
                        name=location_data['name'],
                        parent_location=parent_location,
                        is_site=False,
                        latitude=location_data['latitude'],
                        longitude=location_data['longitude'],
                        address=location_data['address'],
                        is_active=location_data['is_active'],
                        created_by=request.user
                    )
                    
                    created_locations[location_data['name']] = location
                    imported_count += 1
                    
                except Exception as e:
                    error_count += 1
                    print(f"Error creating location {location_data['name']}: {str(e)}")
                    continue
        
        if imported_count > 0:
            messages.success(request, f'Successfully imported {imported_count} locations.')
        if error_count > 0:
            messages.warning(request, f'{error_count} rows had errors and were skipped.')
            
    except Exception as e:
        messages.error(request, f'Error reading CSV file: {str(e)}')
    
    return redirect('core:locations_settings')