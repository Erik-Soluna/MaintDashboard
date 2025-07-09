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
from core.models import Location, EquipmentCategory
from django.utils import timezone
from django.db.models import Q, Count
from datetime import datetime, timedelta, date
from django.http import JsonResponse, HttpResponseRedirect
from django.core.paginator import Paginator
from django.urls import reverse
import json


@login_required
def dashboard(request):
    """Enhanced dashboard view with location-based data layout."""
    
    # Get selected site from request, session, or user default
    selected_site_id = request.GET.get('site_id')
    if not selected_site_id:
        selected_site_id = request.session.get('selected_site_id')
    if not selected_site_id and hasattr(request.user, 'userprofile') and request.user.userprofile.default_site:
        selected_site_id = str(request.user.userprofile.default_site.id)
    
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
    
    # Get locations to display (filtered by site if selected)
    if selected_site:
        locations = Location.objects.filter(
            Q(parent_location=selected_site) | Q(id=selected_site.id),
            is_active=True
        ).order_by('name')
    else:
        # Show all non-site locations if no specific site selected
        locations = Location.objects.filter(
            is_site=False, 
            is_active=True
        ).order_by('name')[:5]  # Limit to 5 for layout
    
    # Get urgent items (overdue or due soon)
    today = timezone.now().date()
    urgent_cutoff = today + timedelta(days=7)  # Items due within 7 days
    
    urgent_items = MaintenanceActivity.objects.filter(
        Q(scheduled_end__lte=urgent_cutoff) & Q(scheduled_end__gte=today),
        status__in=['pending', 'in_progress']
    ).select_related('equipment', 'equipment__location').order_by('scheduled_end')[:10]
    
    # Get upcoming items (due within next 30 days)
    upcoming_cutoff = today + timedelta(days=30)
    upcoming_items = MaintenanceActivity.objects.filter(
        scheduled_end__gt=urgent_cutoff,
        scheduled_end__lte=upcoming_cutoff,
        status__in=['pending', 'scheduled']
    ).select_related('equipment', 'equipment__location').order_by('scheduled_end')[:10]
    
    # Build location-based data
    location_data = []
    for location in locations:
        # Get scheduled downtimes for this location
        downtimes = MaintenanceActivity.objects.filter(
            equipment__location=location,
            status__in=['scheduled', 'in_progress'],
            scheduled_end__gte=today
        ).select_related('equipment').order_by('scheduled_start')[:5]
        
        # Get equipment in repair for this location
        equipment_in_repair = Equipment.objects.filter(
            location=location,
            status='maintenance'
        ).order_by('name')[:5]
        
        location_data.append({
            'location': location,
            'downtimes': downtimes,
            'equipment_in_repair': equipment_in_repair,
        })
    
    context = {
        'sites': sites,
        'selected_site': selected_site,
        'locations': locations,
        'location_data': location_data,
        'urgent_items': urgent_items,
        'upcoming_items': upcoming_items,
        'total_equipment': Equipment.objects.count(),
        'active_equipment': Equipment.objects.filter(is_active=True).count(),
        'pending_maintenance': MaintenanceActivity.objects.filter(
            status='pending'
        ).count(),
    }
    return render(request, 'core/dashboard.html', context)


@login_required
def profile_view(request):
    """User profile view."""
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
    if request.method == 'POST':
        # Handle user preferences update
        user = request.user
        profile = user.userprofile
        
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
    """User management view."""
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
        
        return redirect('core:user_management')
    
    users = User.objects.all().select_related('userprofile').order_by('username')
    
    # Pagination
    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'users': users,
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
        location.is_active = False
        location.save()
        return JsonResponse({'message': 'Location deactivated successfully'})


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