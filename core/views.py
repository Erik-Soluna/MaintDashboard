"""
Views for core app.
Enhanced with monitoring and health check functionality.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth.models import User
from equipment.models import Equipment
from maintenance.models import MaintenanceActivity
from events.models import CalendarEvent
from core.models import Location, EquipmentCategory, Role, Permission, UserProfile, Customer
from core.forms import LocationForm, EquipmentCategoryForm, CustomerForm
from django.utils import timezone
from django.db.models import Q, Count
from datetime import datetime, timedelta, date
from django.http import JsonResponse, HttpResponseRedirect, HttpResponse
from django.core.paginator import Paginator
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST, require_GET
from django.core.management import call_command
from django.core.cache import cache
from django.db import connection
from django.conf import settings
from io import StringIO
import json
import csv
import re
import time
import psutil
import logging
import os
import shutil
import redis
from django_celery_beat.models import PeriodicTask
import requests
from django.test import RequestFactory
from .models import PlaywrightDebugLog
from core.tasks import run_playwright_debug
from .playwright_orchestrator import run_natural_language_test, run_rbac_test_suite
from .tasks import run_natural_language_test_task, run_rbac_test_suite_task
import asyncio
from django.contrib.admin.views.decorators import staff_member_required
import hmac
import hashlib
import os
import time

logger = logging.getLogger(__name__)


def natural_sort_key(text):
    """Generate a key for natural sorting (handles numbers in strings correctly)."""
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r'(\d+)', str(text))]


def is_staff_or_superuser(user):
    """Check if user is staff or superuser."""
    return user.is_staff or user.is_superuser


@login_required
def dashboard(request):
    """Enhanced dashboard view with comprehensive maintenance, calendar, and pod status data."""
    from django.core.cache import cache
    from django.db.models import Count, Q, Prefetch
    import hashlib
    
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
    
    # Create cache key for this dashboard view
    cache_key = f"dashboard_data_{selected_site_id or 'all'}_{request.user.id}"
    cache_timeout = 300  # 5 minutes
    
    # Try to get cached data
    cached_data = cache.get(cache_key)
    if cached_data:
        return render(request, 'core/dashboard.html', cached_data)
    
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
    
    # ===== OPTIMIZED BULK QUERIES =====
    
    # Build optimized base queries with proper joins
    if selected_site:
        # Site-specific queries with optimized joins
        site_filter = Q(location__parent_location=selected_site) | Q(location=selected_site)
        equipment_query = Equipment.objects.filter(site_filter).select_related('location', 'category')
        
        maintenance_site_filter = Q(equipment__location__parent_location=selected_site) | Q(equipment__location=selected_site)
        maintenance_query = MaintenanceActivity.objects.filter(maintenance_site_filter).select_related(
            'equipment', 'equipment__location', 'equipment__category', 'assigned_to'
        )
        
        calendar_site_filter = Q(equipment__location__parent_location=selected_site) | Q(equipment__location=selected_site)
        calendar_query = CalendarEvent.objects.filter(calendar_site_filter).select_related(
            'equipment', 'equipment__location', 'assigned_to'
        )
        
        # Get locations (pods) with natural sorting and prefetch related data
        locations_queryset = Location.objects.filter(
            parent_location=selected_site,
            is_active=True
        ).select_related('parent_location', 'customer').prefetch_related(
            Prefetch('equipment', queryset=Equipment.objects.select_related('category')),
            Prefetch('equipment__maintenance_activities', 
                    queryset=MaintenanceActivity.objects.select_related('assigned_to'))
        )
        locations = list(locations_queryset)
        locations.sort(key=lambda loc: natural_sort_key(loc.name))
        
    else:
        # Global queries
        equipment_query = Equipment.objects.select_related('location', 'category')
        maintenance_query = MaintenanceActivity.objects.select_related(
            'equipment', 'equipment__location', 'equipment__category', 'assigned_to'
        )
        calendar_query = CalendarEvent.objects.select_related(
            'equipment', 'equipment__location', 'assigned_to'
        )
        
        # Show top-level locations if no site selected
        locations_queryset = Location.objects.filter(
            is_site=False,
            is_active=True
        ).select_related('parent_location', 'customer')[:8]
        locations = list(locations_queryset)
        locations.sort(key=lambda loc: natural_sort_key(loc.name))
    
    # ===== BULK STATISTICS CALCULATION =====
    
    # Calculate urgent items with single queries
    urgent_maintenance = list(maintenance_query.filter(
        Q(scheduled_end__lte=urgent_cutoff) & Q(scheduled_end__gte=today),
        status__in=['pending', 'in_progress', 'overdue']
    ).order_by('scheduled_end')[:15])
    
    urgent_calendar = list(calendar_query.filter(
        event_date__lte=urgent_cutoff,
        event_date__gte=today,
        is_completed=False
    ).order_by('event_date')[:10])
    
    # Calculate upcoming items with single queries
    upcoming_maintenance = list(maintenance_query.filter(
        scheduled_end__gt=urgent_cutoff,
        scheduled_end__lte=upcoming_cutoff,
        status__in=['pending', 'scheduled']
    ).order_by('scheduled_end')[:15])
    
    upcoming_calendar = list(calendar_query.filter(
        event_date__gt=urgent_cutoff,
        event_date__lte=upcoming_cutoff,
        is_completed=False
    ).order_by('event_date')[:10])
    
    # ===== OPTIMIZED OVERVIEW DATA CALCULATION =====
    
    if selected_site:
        # POD STATUS - Use prefetched data to avoid N+1 queries
        overview_data = []
        
        # Get all equipment and maintenance data in bulk
        pod_equipment = {loc.id: [] for loc in locations}
        pod_maintenance = {loc.id: [] for loc in locations}
        pod_calendar = {loc.id: [] for loc in locations}
        
        # Organize equipment by location
        for equipment in equipment_query:
            if equipment.location.id in pod_equipment:
                pod_equipment[equipment.location.id].append(equipment)
        
        # Organize maintenance by location
        for maintenance in maintenance_query:
            if maintenance.equipment.location.id in pod_maintenance:
                pod_maintenance[maintenance.equipment.location.id].append(maintenance)
        
        # Organize calendar by location
        for calendar_event in calendar_query:
            if calendar_event.equipment.location.id in pod_calendar:
                pod_calendar[calendar_event.equipment.location.id].append(calendar_event)
        
        # Process each location with bulk data
        for location in locations:
            location_equipment = pod_equipment.get(location.id, [])
            location_maintenance = pod_maintenance.get(location.id, [])
            location_calendar = pod_calendar.get(location.id, [])
            
            # Calculate counts from in-memory data
            equipment_in_maintenance = sum(1 for eq in location_equipment if eq.status == 'maintenance')
            active_equipment = sum(1 for eq in location_equipment if eq.status == 'active')
            total_equipment = len(location_equipment)
            
            # Calculate maintenance counts
            upcoming_maintenance_count = sum(
                1 for ma in location_maintenance
                if (ma.scheduled_start and 
                    today <= ma.scheduled_start.date() <= urgent_cutoff and
                    ma.status in ['scheduled', 'pending'])
            )
            
            # Get recent activities
            recent_activities = [
                ma for ma in location_maintenance
                if (ma.actual_end and 
                    ma.actual_end.date() >= today - timedelta(days=30) and
                    ma.status == 'completed')
            ]
            recent_activities.sort(key=lambda x: x.actual_end, reverse=True)
            recent_activities = recent_activities[:3]
            
            # Get next events
            next_events = [
                ce for ce in location_calendar
                if (ce.event_date >= today and not ce.is_completed)
            ]
            next_events.sort(key=lambda x: x.event_date)
            next_events = next_events[:3]
            
            # Calculate pod health status
            if equipment_in_maintenance > 0:
                status = 'maintenance'
            elif upcoming_maintenance_count > 2:
                status = 'warning'
            elif active_equipment == total_equipment:
                status = 'healthy'
            else:
                status = 'caution'
            
            overview_data.append({
                'location': location,
                'status': status,
                'total_equipment': total_equipment,
                'active_equipment': active_equipment,
                'equipment_in_maintenance': equipment_in_maintenance,
                'upcoming_maintenance_count': upcoming_maintenance_count,
                'recent_activities': recent_activities,
                'next_events': next_events,
                'customer': location.get_effective_customer(),
                'customer_display': location.get_customer_display(),
            })
        overview_type = 'pods'
        
    else:
        # SITE STATUS - Use aggregate queries for better performance
        overview_data = []
        all_sites = Location.objects.filter(is_site=True, is_active=True).order_by('name')
        
        # Get aggregated data for all sites in bulk
        site_equipment_data = {}
        site_maintenance_data = {}
        site_calendar_data = {}
        
        for site in all_sites:
            site_equipment_filter = Q(location__parent_location=site) | Q(location=site)
            site_equipment_counts = Equipment.objects.filter(site_equipment_filter).values('status').annotate(count=Count('id'))
            
            # Convert to dict for easy lookup
            equipment_counts = {item['status']: item['count'] for item in site_equipment_counts}
            
            # Maintenance aggregation
            site_maintenance_filter = Q(equipment__location__parent_location=site) | Q(equipment__location=site)
            maintenance_counts = MaintenanceActivity.objects.filter(site_maintenance_filter).values('status').annotate(count=Count('id'))
            maintenance_counts_dict = {item['status']: item['count'] for item in maintenance_counts}
            
            # Calendar aggregation
            site_calendar_filter = Q(equipment__location__parent_location=site) | Q(equipment__location=site)
            calendar_counts = CalendarEvent.objects.filter(site_calendar_filter).aggregate(
                total=Count('id'),
                pending=Count('id', filter=Q(is_completed=False, event_date__gte=today)),
                completed=Count('id', filter=Q(is_completed=True))
            )
            
            # Calculate derived values
            total_equipment = sum(equipment_counts.values())
            active_equipment = equipment_counts.get('active', 0)
            equipment_in_maintenance = equipment_counts.get('maintenance', 0)
            inactive_equipment = equipment_counts.get('inactive', 0)
            
            pending_maintenance = maintenance_counts_dict.get('pending', 0)
            in_progress_maintenance = maintenance_counts_dict.get('in_progress', 0)
            
            # Get overdue maintenance count
            overdue_maintenance = MaintenanceActivity.objects.filter(
                site_maintenance_filter,
                scheduled_end__lt=timezone.now(),
                status__in=['pending', 'scheduled']
            ).count()
            
            # Get upcoming maintenance count
            upcoming_maintenance_count = MaintenanceActivity.objects.filter(
                site_maintenance_filter,
                scheduled_start__date__lte=urgent_cutoff,
                scheduled_start__date__gte=today,
                status__in=['scheduled', 'pending']
            ).count()
            
            # Get recent activities
            recent_activities = list(MaintenanceActivity.objects.filter(
                site_maintenance_filter,
                actual_end__gte=today - timedelta(days=30),
                status='completed'
            ).select_related('equipment', 'assigned_to').order_by('-actual_end')[:3])
            
            # Get next events
            next_events = list(CalendarEvent.objects.filter(
                site_calendar_filter,
                event_date__gte=today,
                is_completed=False
            ).select_related('equipment', 'assigned_to').order_by('event_date')[:3])
            
            # Calculate site health status
            equipment_health_ratio = active_equipment / max(total_equipment, 1)
            maintenance_load = pending_maintenance + overdue_maintenance
            
            if overdue_maintenance > 0:
                status = 'critical'
            elif equipment_in_maintenance > total_equipment * 0.3 or maintenance_load > 10:
                status = 'warning'
            elif inactive_equipment > total_equipment * 0.2:
                status = 'caution'
            elif equipment_health_ratio > 0.9 and maintenance_load < 3:
                status = 'healthy'
            else:
                status = 'good'
            
            # Get pod count
            pod_count = Location.objects.filter(parent_location=site, is_active=True).count()
            
            overview_data.append({
                'site': site,
                'status': status,
                'total_equipment': total_equipment,
                'active_equipment': active_equipment,
                'equipment_in_maintenance': equipment_in_maintenance,
                'inactive_equipment': inactive_equipment,
                'pending_maintenance': pending_maintenance,
                'in_progress_maintenance': in_progress_maintenance,
                'overdue_maintenance': overdue_maintenance,
                'upcoming_maintenance_count': upcoming_maintenance_count,
                'pending_events': calendar_counts['pending'],
                'pod_count': pod_count,
                'recent_activities': recent_activities,
                'next_events': next_events,
                'equipment_health_ratio': round(equipment_health_ratio * 100, 1),
            })
        overview_type = 'sites'
    
    # ===== OPTIMIZED OVERALL SITE STATISTICS =====
    
    # Use aggregate queries for statistics
    equipment_stats = equipment_query.values('status').annotate(count=Count('id'))
    equipment_counts = {item['status']: item['count'] for item in equipment_stats}
    
    maintenance_stats = maintenance_query.values('status').annotate(count=Count('id'))
    maintenance_counts = {item['status']: item['count'] for item in maintenance_stats}
    
    calendar_stats = calendar_query.aggregate(
        total=Count('id'),
        events_this_week=Count('id', filter=Q(
            event_date__gte=today,
            event_date__lt=today + timedelta(days=7)
        )),
        completed=Count('id', filter=Q(is_completed=True)),
        pending=Count('id', filter=Q(is_completed=False, event_date__gte=today))
    )
    
    # Calculate overdue maintenance
    overdue_count = maintenance_query.filter(
        scheduled_end__lt=timezone.now(),
        status__in=['pending', 'scheduled']
    ).count()
    
    # Calculate completed this month
    completed_this_month = maintenance_query.filter(
        status='completed',
        actual_end__gte=today.replace(day=1)
    ).count()
    
    site_stats = {
        'total_equipment': sum(equipment_counts.values()),
        'active_equipment': equipment_counts.get('active', 0),
        'equipment_in_maintenance': equipment_counts.get('maintenance', 0),
        'inactive_equipment': equipment_counts.get('inactive', 0),
        
        # Maintenance statistics
        'total_maintenance_activities': sum(maintenance_counts.values()),
        'pending_maintenance': maintenance_counts.get('pending', 0),
        'in_progress_maintenance': maintenance_counts.get('in_progress', 0),
        'overdue_maintenance': overdue_count,
        'completed_this_month': completed_this_month,
        
        # Calendar statistics
        'total_calendar_events': calendar_stats['total'],
        'events_this_week': calendar_stats['events_this_week'],
        'completed_events': calendar_stats['completed'],
        'pending_events': calendar_stats['pending'],
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
    
    # Build final context
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
        
        # Overview data (either pods or sites based on selection)
        'overview_data': overview_data,
        'overview_type': overview_type,
        'total_overview_items': len(overview_data),
        
        # Legacy data for backwards compatibility
        'pod_status_data': overview_data if overview_type == 'pods' else [],
        'total_pods': len(overview_data) if overview_type == 'pods' else 0,
        'locations': locations,
        'urgent_items': urgent_maintenance,
        'upcoming_items': upcoming_maintenance,
        'total_equipment': site_stats['total_equipment'],
        'active_equipment': site_stats['active_equipment'],
        'pending_maintenance': site_stats['pending_maintenance'],
    }
    
    # Cache the result
    cache.set(cache_key, context, cache_timeout)
    
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


@login_required
def map_view(request):
    """Map view showing all locations and equipment."""
    locations = Location.objects.filter(is_active=True).select_related('parent_location', 'customer')
    equipment = Equipment.objects.filter(is_active=True).select_related('location')
    customers = Customer.objects.filter(is_active=True).order_by('name')
    
    context = {
        'locations': locations,
        'equipment': equipment,
        'customers': customers,
    }
    return render(request, 'core/map.html', context)


@login_required
@user_passes_test(is_staff_or_superuser)
def settings_view(request):
    # Fetch health data from the health_check view
    from django.test import RequestFactory
    rf = RequestFactory()
    health_response = health_check(rf.get('/core/health/'))
    health_data = health_response.content.decode('utf-8')
    import json
    health = json.loads(health_data)
    return render(request, 'core/settings.html', {'health': health})


@login_required
@user_passes_test(is_staff_or_superuser)
def locations_settings(request):
    """Locations management view."""
    # Get all locations and apply natural sorting
    locations = list(Location.objects.all())
    locations.sort(key=lambda loc: natural_sort_key(loc.name))
    
    # Get sites with natural sorting
    sites = list(Location.objects.filter(is_site=True, is_active=True).prefetch_related('child_locations__child_locations'))
    sites.sort(key=lambda site: natural_sort_key(site.name))
    
    # Apply natural sorting to child locations for each site
    for site in sites:
        site.child_locations_sorted = sorted(site.child_locations.all(), key=lambda loc: natural_sort_key(loc.name))
        # Also sort nested child locations
        for child in site.child_locations_sorted:
            child.child_locations_sorted = sorted(child.child_locations.all(), key=lambda loc: natural_sort_key(loc.name))
    
    customers = Customer.objects.filter(is_active=True).order_by('name')
    
    context = {
        'locations': locations,
        'sites': sites,
        'customers': customers,
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
        try:
            locations = Location.objects.all().values(
                'id', 'name', 'address', 'is_site', 'is_active', 'parent_location__name'
            )
            return JsonResponse(list(locations), safe=False)
        except Exception as e:
            return JsonResponse({
                'error': f'Error fetching locations: {str(e)}'
            }, status=500)
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Validate required fields
            name = data.get('name', '').strip()
            if not name:
                return JsonResponse({
                    'error': 'Location name is required'
                }, status=400)
            
            is_site = data.get('is_site', False)
            parent_location_id = data.get('parent_location_id')
            
            # Validate site/location rules
            if is_site and parent_location_id:
                return JsonResponse({
                    'error': 'Site locations cannot have a parent location'
                }, status=400)
            
            if not is_site and not parent_location_id:
                return JsonResponse({
                    'error': 'Equipment locations must have a parent site'
                }, status=400)
            
            # Check for duplicate names at the same level
            if is_site:
                if Location.objects.filter(name=name, is_site=True).exists():
                    return JsonResponse({
                        'error': f'A site with the name "{name}" already exists'
                    }, status=400)
            else:
                if Location.objects.filter(
                    name=name, 
                    parent_location_id=parent_location_id,
                    is_site=False
                ).exists():
                    return JsonResponse({
                        'error': f'A location with the name "{name}" already exists at this site'
                    }, status=400)
            
            # Create location
            location = Location.objects.create(
                name=name,
                address=data.get('address', ''),
                is_site=is_site,
                parent_location_id=parent_location_id,
                customer_id=data.get('customer_id') or None,
                created_by=request.user,
                updated_by=request.user
            )
            
            return JsonResponse({
                'id': location.id,
                'name': location.name,
                'message': f'{"Site" if is_site else "Location"} created successfully'
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'error': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'error': f'Error creating location: {str(e)}'
            }, status=500)


@login_required
@user_passes_test(is_staff_or_superuser)
def location_detail_api(request, location_id):
    """API endpoint for individual location management."""
    location = get_object_or_404(Location, id=location_id)
    
    if request.method == 'PUT':
        try:
            data = json.loads(request.body)
            
            # Validate required fields
            name = data.get('name', '').strip()
            if not name:
                return JsonResponse({
                    'error': 'Location name is required'
                }, status=400)
            
            # Check for duplicate names at the same level (excluding current location)
            if location.is_site:
                if Location.objects.filter(name=name, is_site=True).exclude(id=location.id).exists():
                    return JsonResponse({
                        'error': f'A site with the name "{name}" already exists'
                    }, status=400)
            else:
                parent_location_id = data.get('parent_location_id', location.parent_location_id)
                if Location.objects.filter(
                    name=name, 
                    parent_location_id=parent_location_id,
                    is_site=False
                ).exclude(id=location.id).exists():
                    return JsonResponse({
                        'error': f'A location with the name "{name}" already exists at this site'
                    }, status=400)
            
            # Update location
            location.name = name
            location.address = data.get('address', location.address)
            location.is_active = data.get('is_active', location.is_active)
            
            # Update customer assignment
            if 'customer_id' in data:
                location.customer_id = data.get('customer_id') or None
            
            # Only update parent if provided and location is not a site
            if not location.is_site and 'parent_location_id' in data:
                location.parent_location_id = data.get('parent_location_id')
            
            location.updated_by = request.user
            location.save()
            
            return JsonResponse({
                'message': f'{"Site" if location.is_site else "Location"} updated successfully'
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'error': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'error': f'Error updating location: {str(e)}'
            }, status=500)
    
    elif request.method == 'DELETE':
        try:
            location_name = location.name
            
            # Check if location has any equipment or child locations
            if hasattr(location, 'equipment') and location.equipment.exists():
                return JsonResponse({
                    'error': f'Cannot delete location "{location_name}" because it has equipment assigned to it.'
                }, status=400)
            
            if location.child_locations.exists():
                return JsonResponse({
                    'error': f'Cannot delete location "{location_name}" because it has child locations.'
                }, status=400)
            
            location.delete()
            return JsonResponse({
                'message': f'{"Site" if location.is_site else "Location"} "{location_name}" deleted successfully!'
            })
            
        except Exception as e:
            return JsonResponse({
                'error': f'Error deleting location: {str(e)}'
            }, status=500)


@login_required
@user_passes_test(is_staff_or_superuser)
def equipment_items_api(request):
    """API endpoint for equipment items management."""
    if request.method == 'GET':
        try:
            equipment = Equipment.objects.select_related('location', 'category').values(
                'id', 'name', 'asset_tag', 'location__name', 'category__name', 
                'status', 'is_active', 'manufacturer_serial'
            )
            return JsonResponse(list(equipment), safe=False)
        except Exception as e:
            return JsonResponse({
                'error': f'Error fetching equipment: {str(e)}'
            }, status=500)


@login_required
@user_passes_test(is_staff_or_superuser)
def users_api(request):
    """API endpoint for user management."""
    if request.method == 'GET':
        try:
            users = User.objects.select_related('userprofile').values(
                'id', 'username', 'first_name', 'last_name', 'email',
                'is_active', 'is_staff', 'is_superuser', 'last_login',
                'userprofile__department', 'userprofile__phone_number'
            )
            return JsonResponse(list(users), safe=False)
        except Exception as e:
            return JsonResponse({
                'error': f'Error fetching users: {str(e)}'
            }, status=500)


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
        try:
            data = json.loads(request.body)
            
            # Validate required fields
            name = data.get('name', role.name).strip()
            display_name = data.get('display_name', role.display_name).strip()
            
            if not name:
                return JsonResponse({
                    'error': 'Role name is required'
                }, status=400)
            
            if not display_name:
                return JsonResponse({
                    'error': 'Display name is required'
                }, status=400)
            
            # Check for duplicate role names (excluding current role)
            if Role.objects.filter(name=name).exclude(id=role.id).exists():
                return JsonResponse({
                    'error': f'A role with the name "{name}" already exists'
                }, status=400)
            
            # Update role
            role.name = name
            role.display_name = display_name
            role.description = data.get('description', role.description)
            role.is_active = data.get('is_active', role.is_active)
            role.updated_by = request.user
            role.save()
            
            # Update permissions
            if 'permission_ids' in data:
                permission_ids = data['permission_ids']
                role.permissions.set(permission_ids)
            
            return JsonResponse({'message': 'Role updated successfully'})
            
        except json.JSONDecodeError:
            return JsonResponse({
                'error': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'error': f'Error updating role: {str(e)}'
            }, status=500)
    
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
        try:
            data = json.loads(request.body)
            
            # Validate required fields
            name = data.get('name', '').strip()
            display_name = data.get('display_name', '').strip()
            
            if not name:
                return JsonResponse({
                    'error': 'Role name is required'
                }, status=400)
            
            if not display_name:
                return JsonResponse({
                    'error': 'Display name is required'
                }, status=400)
            
            # Check for duplicate role names
            if Role.objects.filter(name=name).exists():
                return JsonResponse({
                    'error': f'A role with the name "{name}" already exists'
                }, status=400)
            
            # Create role
            role = Role.objects.create(
                name=name,
                display_name=display_name,
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
            
        except json.JSONDecodeError:
            return JsonResponse({
                'error': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'error': f'Error creating role: {str(e)}'
            }, status=500)


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


@login_required
@user_passes_test(is_staff_or_superuser)
def customers_settings(request):
    """Customer management view."""
    customers = Customer.objects.all().order_by('name')
    
    # Pagination
    paginator = Paginator(customers, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'customers': customers,
    }
    return render(request, 'core/customers_settings.html', context)


@login_required
@user_passes_test(is_staff_or_superuser)
def add_customer(request):
    """Add new customer."""
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save(commit=False)
            customer.created_by = request.user
            customer.save()
            messages.success(request, f'Customer "{customer.name}" has been created successfully.')
            return redirect('core:customers_settings')
    else:
        form = CustomerForm()
    
    context = {
        'form': form,
        'title': 'Add Customer',
        'action': 'Add'
    }
    return render(request, 'core/customer_form.html', context)


@login_required
@user_passes_test(is_staff_or_superuser)
@require_http_methods(["POST"])
def add_customer_ajax(request):
    """Add new customer via AJAX for modal form."""
    try:
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save(commit=False)
            customer.created_by = request.user
            customer.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Customer "{customer.name}" has been created successfully.',
                'customer': {
                    'id': customer.id,
                    'name': customer.name,
                    'code': customer.code
                }
            })
        else:
            # Return form errors
            errors = {}
            for field, field_errors in form.errors.items():
                errors[field] = field_errors[0] if field_errors else 'Invalid input'
            
            return JsonResponse({
                'success': False,
                'error': 'Please correct the errors below.',
                'field_errors': errors
            }, status=400)
            
    except Exception as e:
        logger.error(f"Error creating customer via AJAX: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while creating the customer.'
        }, status=500)


@login_required
@user_passes_test(is_staff_or_superuser)
def edit_customer(request, customer_id):
    """Edit existing customer."""
    customer = get_object_or_404(Customer, id=customer_id)
    
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            customer = form.save(commit=False)
            customer.updated_by = request.user
            customer.save()
            messages.success(request, f'Customer "{customer.name}" has been updated successfully.')
            return redirect('core:customers_settings')
    else:
        form = CustomerForm(instance=customer)
    
    context = {
        'form': form,
        'customer': customer,
        'title': f'Edit Customer: {customer.name}',
        'action': 'Edit'
    }
    return render(request, 'core/customer_form.html', context)


@login_required
@user_passes_test(is_staff_or_superuser)
def delete_customer(request, customer_id):
    """Delete customer."""
    customer = get_object_or_404(Customer, id=customer_id)
    
    if request.method == 'POST':
        # Check if customer has associated locations
        location_count = customer.locations.count()
        if location_count > 0:
            messages.error(
                request, 
                f'Cannot delete customer "{customer.name}" because it has {location_count} associated location(s). '
                'Please reassign or remove the locations first.'
            )
        else:
            customer_name = customer.name
            customer.delete()
            messages.success(request, f'Customer "{customer_name}" has been deleted successfully.')
        
        return redirect('core:customers_settings')
    
    # Get associated locations for confirmation
    associated_locations = customer.locations.all()
    
    context = {
        'customer': customer,
        'associated_locations': associated_locations,
        'location_count': associated_locations.count()
    }
    return render(request, 'core/delete_customer.html', context)


# ========================================
# MONITORING AND HEALTH CHECK VIEWS
# ========================================

@login_required
@user_passes_test(is_staff_or_superuser)
def monitoring_dashboard(request):
    """Display monitoring dashboard."""
    try:
        # Get system metrics
        system_metrics = get_system_metrics()
        
        # Get endpoint metrics
        endpoint_metrics = get_endpoint_metrics()
        
        # Get database health
        db_health = check_database_health()
        
        # Get cache health
        cache_health = check_cache_health()
        
        context = {
            'system_metrics': system_metrics,
            'endpoint_metrics': endpoint_metrics,
            'db_health': db_health,
            'cache_health': cache_health,
            'monitoring_enabled': getattr(settings, 'MONITORING_ENABLED', True)
        }
        
        return render(request, 'core/monitoring_dashboard.html', context)
        
    except Exception as e:
        logger.error(f"Error in monitoring dashboard: {str(e)}")
        return render(request, 'core/monitoring_dashboard.html', {
            'error': str(e),
            'monitoring_enabled': getattr(settings, 'MONITORING_ENABLED', True)
        })


@csrf_exempt
@require_http_methods(["GET"])
def health_check_api(request):
    """API endpoint for health checks."""
    try:
        # Basic health check
        health_data = {
            'timestamp': timezone.now().isoformat(),
            'status': 'healthy',
            'system_metrics': get_system_metrics(),
            'database_health': check_database_health(),
            'cache_health': check_cache_health(),
        }
        
        # Determine overall status
        overall_status = 'healthy'
        
        if health_data['database_health'].get('status') == 'unhealthy':
            overall_status = 'critical'
        elif health_data['cache_health'].get('status') == 'unhealthy':
            overall_status = 'warning'
        
        health_data['overall_status'] = overall_status
        
        return JsonResponse(health_data)
        
    except Exception as e:
        logger.error(f"Error in health check API: {str(e)}")
        return JsonResponse({
            'timestamp': timezone.now().isoformat(),
            'status': 'error',
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def endpoint_metrics_api(request):
    """API endpoint for endpoint metrics."""
    try:
        endpoint_metrics = get_endpoint_metrics()
        return JsonResponse({
            'timestamp': timezone.now().isoformat(),
            'endpoint_metrics': endpoint_metrics
        })
    except Exception as e:
        logger.error(f"Error in endpoint metrics API: {str(e)}")
        return JsonResponse({
            'timestamp': timezone.now().isoformat(),
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def toggle_monitoring(request):
    """Toggle monitoring on/off."""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Insufficient permissions'}, status=403)
    
    try:
        data = json.loads(request.body)
        enabled = data.get('enabled', True)
        
        # Store monitoring state in cache
        cache.set('monitoring_enabled', enabled, timeout=86400)  # 24 hours
        
        return JsonResponse({
            'status': 'success',
            'monitoring_enabled': enabled
        })
        
    except Exception as e:
        logger.error(f"Error toggling monitoring: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@user_passes_test(is_staff_or_superuser)
def run_health_check(request):
    """Run comprehensive health check."""
    try:
        # Capture management command output
        output = StringIO()
        call_command('health_check', stdout=output, stderr=output)
        
        health_output = output.getvalue()
        
        return HttpResponse(health_output, content_type='text/plain')
        
    except Exception as e:
        logger.error(f"Error running health check: {str(e)}")
        return HttpResponse(f"Error running health check: {str(e)}", 
                          content_type='text/plain', status=500)


def get_system_metrics():
    """Get current system metrics."""
    try:
        return {
            'cpu_percent': psutil.cpu_percent(interval=0.1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent,
            'load_average': psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None,
            'process_count': len(psutil.pids()),
            'timestamp': timezone.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting system metrics: {str(e)}")
        return {'error': str(e)}


def get_endpoint_metrics():
    """Get endpoint performance metrics from cache."""
    try:
        # Get all endpoint metrics from cache
        all_keys = cache.keys('endpoint_metrics:*')
        endpoint_metrics = {}
        
        for key in all_keys:
            if isinstance(key, str) and key.startswith('endpoint_metrics:'):
                endpoint_name = key.replace('endpoint_metrics:', '')
                metrics = cache.get(key)
                if metrics:
                    endpoint_metrics[endpoint_name] = metrics
        
        return endpoint_metrics
    except Exception as e:
        logger.error(f"Error getting endpoint metrics: {str(e)}")
        return {'error': str(e)}


def check_database_health():
    """Check database connection and performance."""
    try:
        start_time = time.time()
        
        # Test connection
        connection.ensure_connection()
        
        # Test query performance
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        
        response_time = time.time() - start_time
        
        return {
            'status': 'healthy',
            'response_time': response_time,
            'timestamp': timezone.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return {
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }


def check_cache_health():
    """Check cache functionality."""
    try:
        test_key = 'health_check_test'
        test_value = 'test_value'
        
        start_time = time.time()
        
        # Test cache write
        cache.set(test_key, test_value, 60)
        
        # Test cache read
        cached_value = cache.get(test_key)
        
        # Clean up
        cache.delete(test_key)
        
        response_time = time.time() - start_time
        
        if cached_value == test_value:
            return {
                'status': 'healthy',
                'response_time': response_time,
                'timestamp': timezone.now().isoformat()
            }
        else:
            return {
                'status': 'unhealthy',
                'error': 'Cache read/write mismatch',
                'timestamp': timezone.now().isoformat()
            }
    except Exception as e:
        logger.error(f"Cache health check failed: {str(e)}")
        return {
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }


import os
import shutil
import redis
from django_celery_beat.models import PeriodicTask
from django.utils import timezone

HEALTH_LOG_FILE = os.path.join(os.path.dirname(__file__), '../health_failures.log')


def log_health_failure(component, message):
    with open(HEALTH_LOG_FILE, 'a') as f:
        f.write(f"{timezone.now().isoformat()} | {component} | {message}\n")

def get_recent_health_failures(limit=10):
    if not os.path.exists(HEALTH_LOG_FILE):
        return []
    with open(HEALTH_LOG_FILE, 'r') as f:
        lines = f.readlines()[-limit:]
    return [
        dict(zip(['timestamp', 'component', 'message'], line.strip().split(' | ', 2)))
        for line in lines
    ]

def health_check(request):
    """Comprehensive health check endpoint that returns JSON with detailed status."""
    checks = []
    status = 'ok'
    # DB check
    try:
        from django.db import connection
        connection.ensure_connection()
        checks.append({'name': 'Database', 'status': 'ok', 'message': 'Connected'})
    except Exception as e:
        checks.append({'name': 'Database', 'status': 'error', 'message': str(e)})
        log_health_failure('Database', str(e))
        status = 'error'
    # Redis check
    try:
        from django.conf import settings
        if getattr(settings, 'USE_REDIS', True):
            r = redis.Redis.from_url(settings.REDIS_URL)
            r.ping()
            checks.append({'name': 'Redis', 'status': 'ok', 'message': 'Connected'})
        else:
            checks.append({'name': 'Redis', 'status': 'info', 'message': 'Redis disabled for development'})
    except Exception as e:
        checks.append({'name': 'Redis', 'status': 'error', 'message': str(e)})
        log_health_failure('Redis', str(e))
        status = 'error'
    # Celery check (beat task heartbeat)
    try:
        from django_celery_beat.models import PeriodicTask
        enabled_tasks = PeriodicTask.objects.filter(enabled=True)
        if not enabled_tasks.exists():
            msg = 'No periodic tasks enabled'
            checks.append({'name': 'Celery Beat', 'status': 'info', 'message': msg})
        else:
            recent = None
            for task in enabled_tasks:
                if task.last_run_at and (recent is None or task.last_run_at > recent):
                    recent = task.last_run_at
            if recent:
                seconds_since = (timezone.now() - recent).total_seconds()
                if seconds_since < 600:
                    checks.append({'name': 'Celery Beat', 'status': 'ok', 'message': f'Recent heartbeat ({int(seconds_since)}s ago)'})
                else:
                    msg = f'No recent heartbeat (last was {int(seconds_since//60)} min ago)'
                    checks.append({'name': 'Celery Beat', 'status': 'warning', 'message': msg})
                    log_health_failure('Celery Beat', msg)
                    if status != 'error':
                        status = 'warning'
            else:
                msg = 'No periodic tasks have ever run'
                checks.append({'name': 'Celery Beat', 'status': 'warning', 'message': msg})
                log_health_failure('Celery Beat', msg)
                if status != 'error':
                    status = 'warning'
    except Exception as e:
        checks.append({'name': 'Celery Beat', 'status': 'error', 'message': str(e)})
        log_health_failure('Celery Beat', str(e))
        status = 'error'
    # Disk space check
    try:
        total, used, free = shutil.disk_usage('/')
        percent_free = free / total * 100
        if percent_free < 10:
            msg = f'Low disk space: {percent_free:.1f}% free'
            checks.append({'name': 'Disk Space', 'status': 'warning', 'message': msg})
            log_health_failure('Disk Space', msg)
            if status != 'error':
                status = 'warning'
        else:
            checks.append({'name': 'Disk Space', 'status': 'ok', 'message': f'{percent_free:.1f}% free'})
    except Exception as e:
        checks.append({'name': 'Disk Space', 'status': 'error', 'message': str(e)})
        log_health_failure('Disk Space', str(e))
        status = 'error'
    # Add more checks as needed
    return JsonResponse({
        'status': status,
        'checks': checks,
        'last_failure_log': get_recent_health_failures(10)
    })


def simple_health_check(request):
    """Simple health check endpoint for Docker health checks - returns 200 OK."""
    try:
        # Basic database connection check
        from django.db import connection
        connection.ensure_connection()
        
        # Basic Redis check (only if enabled and Redis is available)
        from django.conf import settings
        if getattr(settings, 'USE_REDIS', True):
            try:
                r = redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=2, socket_timeout=2)
                r.ping()
            except Exception as redis_error:
                # Log the Redis error but don't fail the health check
                logger.warning(f"Redis connection failed: {redis_error}. Falling back to memory broker.")
                # Continue with health check - Redis failure shouldn't break the app
        
        return JsonResponse({'status': 'ok'}, status=200)
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@require_POST
def clear_health_logs(request):
    """Clear the recent health failure log (from cache and file)."""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    cache.delete('health_failure_log')
    # Also clear the log file
    try:
        if os.path.exists(HEALTH_LOG_FILE):
            with open(HEALTH_LOG_FILE, 'w') as f:
                f.truncate(0)
    except Exception as e:
        return JsonResponse({'error': f'Failed to clear log file: {str(e)}'}, status=500)
    return JsonResponse({'success': True})


@login_required
def api_explorer(request):
    """API Explorer: Tree view of all models and API documentation with live data."""
    from django.db.models import Count, Q
    from django.urls import reverse
    from equipment.models import Equipment
    from maintenance.models import MaintenanceActivity, MaintenanceActivityType, ActivityTypeCategory
    from events.models import CalendarEvent
    from django.contrib.auth.models import User
    
    # Get live data counts and samples
    context = {
        # Core models
        'customers': {
            'count': Customer.objects.filter(is_active=True).count(),
            'sample': list(Customer.objects.filter(is_active=True)[:5].values('id', 'name', 'code')),
            'model_name': 'Customer',
            # 'admin_url': reverse('admin:core_customer_changelist'),  # Removed, not registered in admin
            'description': 'Customer/client information and contact details'
        },
        'locations': {
            'count': Location.objects.filter(is_active=True).count(),
            'sample': list(Location.objects.filter(is_active=True)[:5].values('id', 'name', 'is_site', 'customer__name')),
            'model_name': 'Location',
            'admin_url': reverse('admin:core_location_changelist'),
            'description': 'Hierarchical locations including sites and equipment locations'
        },
        'equipment_categories': {
            'count': EquipmentCategory.objects.filter(is_active=True).count(),
            'sample': list(EquipmentCategory.objects.filter(is_active=True)[:5].values('id', 'name', 'description')),
            'model_name': 'EquipmentCategory',
            'admin_url': reverse('admin:core_equipmentcategory_changelist'),
            'description': 'Categories for organizing equipment types'
        },
        'users': {
            'count': User.objects.filter(is_active=True).count(),
            'sample': list(User.objects.filter(is_active=True)[:5].values('id', 'username', 'first_name', 'last_name')),
            'model_name': 'User',
            'admin_url': reverse('admin:auth_user_changelist'),
            'description': 'System users with roles and permissions'
        },
        'roles': {
            'count': Role.objects.filter(is_active=True).count(),
            'sample': list(Role.objects.filter(is_active=True)[:5].values('id', 'name', 'display_name')),
            'model_name': 'Role',
            'admin_url': reverse('admin:core_role_changelist'),
            'description': 'User roles with associated permissions'
        },
        'permissions': {
            'count': Permission.objects.filter(is_active=True).count(),
            'sample': list(Permission.objects.filter(is_active=True)[:5].values('id', 'name', 'module')),
            'model_name': 'Permission',
            'admin_url': reverse('admin:core_permission_changelist'),
            'description': 'System permissions for role-based access control'
        },
        
        # Equipment models
        'equipment': {
            'count': Equipment.objects.filter(is_active=True).count(),
            'sample': list(Equipment.objects.filter(is_active=True).select_related('category', 'location')[:5].values(
                'id', 'name', 'category__name', 'location__name'
            )),
            'model_name': 'Equipment',
            'admin_url': reverse('admin:equipment_equipment_changelist'),
            'description': 'Equipment items with categories and locations'
        },
        
        # Maintenance models
        'maintenance_activities': {
            'count': MaintenanceActivity.objects.count(),
            'sample': list(MaintenanceActivity.objects.select_related('equipment', 'assigned_to')[:5].values(
                'id', 'title', 'equipment__name', 'status', 'assigned_to__username'
            )),
            'model_name': 'MaintenanceActivity',
            'admin_url': reverse('admin:maintenance_maintenanceactivity_changelist'),
            'description': 'Maintenance activities and tasks'
        },
        'maintenance_activity_types': {
            'count': MaintenanceActivityType.objects.filter(is_active=True).count(),
            'sample': list(MaintenanceActivityType.objects.filter(is_active=True)[:5].values('id', 'name', 'description')),
            'model_name': 'MaintenanceActivityType',
            'admin_url': reverse('admin:maintenance_maintenanceactivitytype_changelist'),
            'description': 'Types of maintenance activities'
        },
        'activity_type_categories': {
            'count': ActivityTypeCategory.objects.filter(is_active=True).count(),
            'sample': list(ActivityTypeCategory.objects.filter(is_active=True)[:5].values('id', 'name', 'description')),
            'model_name': 'ActivityTypeCategory',
            'admin_url': reverse('admin:maintenance_activitytypecategory_changelist'),
            'description': 'Categories for organizing maintenance activity types'
        },
        
        # Events models
        'calendar_events': {
            'count': CalendarEvent.objects.count(),
            'sample': list(CalendarEvent.objects.select_related('equipment', 'assigned_to')[:5].values(
                'id', 'title', 'equipment__name', 'event_date', 'assigned_to__username'
            )),
            'model_name': 'CalendarEvent',
            'admin_url': reverse('admin:events_calendarevent_changelist'),
            'description': 'Calendar events and scheduling'
        },
        
        # API Endpoints
        'api_endpoints': [
            {
                'name': 'Health Check',
                'url': reverse('core:health_check'),
                'method': 'GET',
                'description': 'System health status and metrics',
                'auth_required': False
            },
            {
                'name': 'Health Check API',
                'url': reverse('core:health_check_api'),
                'method': 'GET',
                'description': 'JSON health check endpoint',
                'auth_required': False
            },
            {
                'name': 'Locations API',
                'url': reverse('core:locations_api'),
                'method': 'GET',
                'description': 'Get all locations with filtering',
                'auth_required': True
            },
            {
                'name': 'Equipment Items API',
                'url': reverse('core:equipment_items_api'),
                'method': 'GET',
                'description': 'Get all equipment items',
                'auth_required': True
            },
            {
                'name': 'Users API',
                'url': reverse('core:users_api'),
                'method': 'GET',
                'description': 'Get all users',
                'auth_required': True
            },
            {
                'name': 'Roles API',
                'url': reverse('core:roles_api'),
                'method': 'GET',
                'description': 'Get all roles and permissions',
                'auth_required': True
            },
            {
                'name': 'Playwright Debug API',
                'url': reverse('core:playwright_debug_api'),
                'method': 'GET/POST',
                'description': 'Playwright test execution and debugging',
                'auth_required': True
            },
            {
                'name': 'Natural Language Test API',
                'url': reverse('core:run_natural_language_test_api'),
                'method': 'POST',
                'description': 'Execute natural language Playwright tests',
                'auth_required': True
            },
            {
                'name': 'RBAC Test Suite API',
                'url': reverse('core:run_rbac_test_suite_api'),
                'method': 'POST',
                'description': 'Execute RBAC test suite',
                'auth_required': True
            },
            {
                'name': 'Test Results API',
                'url': reverse('core:get_test_results_api'),
                'method': 'GET',
                'description': 'Get Playwright test results',
                'auth_required': True
            },
            {
                'name': 'Test Screenshots API',
                'url': reverse('core:get_test_screenshots_api'),
                'method': 'GET',
                'description': 'Get Playwright test screenshots',
                'auth_required': True
            },
            {
                'name': 'Test Scenario API',
                'url': reverse('core:run_test_scenario_api'),
                'method': 'POST',
                'description': 'Execute specific test scenarios',
                'auth_required': True
            }
        ],
        
        # System Information
        'system_info': {
            'total_models': 12,  # Count of all models
            'total_endpoints': 12,  # Count of API endpoints
            'database_tables': 15,  # Approximate count of database tables
            'last_updated': timezone.now()
        }
    }
    
    return render(request, 'core/api_explorer.html', context)


@login_required
def system_health(request):
    """System health/diagnostics page for superusers/admins."""
    if not request.user.is_superuser:
        return redirect('core:dashboard')
    return render(request, 'core/system_health.html')


@login_required
def debug(request):
    """Debug and diagnostics page with collapsible sections."""
    if not request.user.is_superuser:
        return redirect('core:dashboard')
    
    try:
        context = {}
        return render(request, 'core/debug.html', context)
    except Exception as e:
        import traceback
        logger.error(f"Error in debug view: {str(e)}")
        logger.error(traceback.format_exc())
        # Return a simple error page instead of 500
        return render(request, 'core/debug.html', {
            'error': f'Debug page error: {str(e)}',
            'traceback': traceback.format_exc() if request.user.is_superuser else None
        })


@login_required
@user_passes_test(is_staff_or_superuser)
@require_http_methods(["POST"])
def generate_pods(request):
    """Generate PODs for selected sites or all sites."""
    try:
        from django.core.management import call_command
        from io import StringIO
        
        # Get parameters from the form
        site_id = request.POST.get('site_id', '').strip()
        pod_count = int(request.POST.get('pod_count', 11))
        mdcs_per_pod = int(request.POST.get('mdcs_per_pod', 2))
        force = request.POST.get('force', 'false').lower() == 'true'
        
        # Capture command output
        output = StringIO()
        
        # Build command arguments
        args = ['generate_pods']
        
        if site_id:
            # Generate for specific site
            args.extend(['--site-id', site_id])
        else:
            # Generate for all sites
            args.append('--all-sites')
        
        # Add other parameters
        args.extend(['--pod-count', str(pod_count)])
        args.extend(['--mdcs-per-pod', str(mdcs_per_pod)])
        
        if force:
            args.append('--force')
        
        # Call the generate pods command
        call_command(*args, stdout=output, verbosity=2)
        
        result = output.getvalue()
        output.close()
        
        # Parse the output to extract generated count
        generated_count = 0
        
        # Look for patterns in the output
        import re
        generated_matches = re.findall(r'Generated (\d+)', result)
        
        if generated_matches:
            generated_count = sum(int(x) for x in generated_matches)
        
        # Determine target description
        if site_id:
            try:
                site = Location.objects.get(id=site_id, is_site=True)
                target_desc = f"site '{site.name}'"
            except Location.DoesNotExist:
                target_desc = "selected site"
        else:
            target_desc = "all sites"
        
        return JsonResponse({
            'success': True,
            'message': f'POD generation completed successfully for {target_desc}! Generated: {generated_count} PODs',
            'generated_count': generated_count,
            'output': result
        })
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return JsonResponse({
            'success': False,
            'error': f'Error generating PODs: {str(e)}',
            'details': error_details
        }, status=500)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def playwright_debug_api(request):
    if request.method == "GET":
        # Return the latest 10 logs
        logs = PlaywrightDebugLog.objects.all()[:10]
        return JsonResponse({
            "logs": [
                {
                    "id": log.id,
                    "timestamp": log.timestamp,
                    "prompt": log.prompt,
                    "status": log.status,
                    "output": log.output,
                    "error_message": log.error_message,
                    "result_json": log.result_json,
                    "started_at": log.started_at,
                    "finished_at": log.finished_at,
                }
                for log in logs
            ]
        })
    elif request.method == "POST":
        import json
        data = json.loads(request.body.decode())
        prompt = data.get("prompt", "").strip()
        if not prompt:
            return JsonResponse({"error": "Prompt is required."}, status=400)
        log = PlaywrightDebugLog.objects.create(prompt=prompt, status="pending")
        # Trigger Celery task
        run_playwright_debug.delay(log.id)
        return JsonResponse({"id": log.id, "status": log.status, "prompt": log.prompt})


@login_required
@user_passes_test(is_staff_or_superuser)
@require_http_methods(["POST"])
def populate_demo_data(request):
    """Populate the database with comprehensive demo data."""
    try:
        from django.core.management import call_command
        from io import StringIO
        
        # Get parameters from request
        clear_first = request.POST.get('clear_first', 'false').lower() == 'true'
        include_maintenance = request.POST.get('include_maintenance', 'true').lower() == 'true'
        include_events = request.POST.get('include_events', 'true').lower() == 'true'
        
        # Capture command output
        output = StringIO()
        
        # Build command arguments
        args = ['populate_comprehensive_demo_data']
        
        if clear_first:
            args.append('--reset')
        
        if include_maintenance:
            args.append('--include-maintenance')
        
        if include_events:
            args.append('--include-events')
        
        # Call the comprehensive demo data command
        call_command(*args, stdout=output, verbosity=2)
        
        result = output.getvalue()
        output.close()
        
        # Parse the output to extract counts
        created_count = 0
        deleted_count = 0
        
        # Look for patterns in the output
        import re
        created_matches = re.findall(r'Created (\d+)', result)
        deleted_matches = re.findall(r'Deleted (\d+)', result)
        
        if created_matches:
            created_count = sum(int(x) for x in created_matches)
        if deleted_matches:
            deleted_count = sum(int(x) for x in deleted_matches)
        
        return JsonResponse({
            'success': True,
            'message': f'Demo data populated successfully! Created: {created_count} items, Deleted: {deleted_count} items',
            'created_count': created_count,
            'deleted_count': deleted_count,
            'output': result
        })
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return JsonResponse({
            'success': False,
            'error': f'Error populating demo data: {str(e)}',
            'details': error_details
        }, status=500)


@login_required
@user_passes_test(is_staff_or_superuser)
@csrf_exempt
@require_http_methods(["POST"])
def clear_database(request):
    """Clear the database with safety confirmations."""
    try:
        from django.core.management import call_command
        from io import StringIO
        import json
        
        # Get parameters from request
        keep_users = request.POST.get('keep_users', 'false').lower() == 'true'
        keep_admin = request.POST.get('keep_admin', 'false').lower() == 'true'
        dry_run = request.POST.get('dry_run', 'false').lower() == 'true'
        
        # Capture command output
        output = StringIO()
        
        # Build command arguments
        args = ['clear_database', '--force']  # Skip confirmation prompts
        
        if keep_users:
            args.append('--keep-users')
        if keep_admin:
            args.append('--keep-admin')
        if dry_run:
            args.append('--dry-run')
        
        # Call the management command
        call_command(*args, stdout=output, verbosity=2)
        
        # Get the output
        command_output = output.getvalue()
        output.close()
        
        return JsonResponse({
            'success': True,
            'message': 'Database clear operation completed',
            'output': command_output,
            'dry_run': dry_run
        })
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return JsonResponse({
            'success': False,
            'error': f'Error clearing database: {str(e)}',
            'details': error_details
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def run_natural_language_test_api(request):
    """
    Run a natural language test via API.
    
    Expected JSON payload:
    {
        "prompt": "Clear database with keep users option",
        "user_role": "admin",
        "username": "admin",
        "password": "temppass123",
        "async": false
    }
    """
    import json
    try:
        data = json.loads(request.body)
        prompt = data.get('prompt', '')
        user_role = data.get('user_role', 'admin')
        username = data.get('username', 'admin')
        password = data.get('password', 'temppass123')
        run_async = data.get('async', False)
        if not prompt:
            return JsonResponse({'success': False, 'error': 'Prompt is required'}, status=400)
        
        if run_async:
            # Run as Celery task
            task = run_natural_language_test_task.delay(
                prompt=prompt,
                user_role=user_role,
                username=username,
                password=password
            )
            
            return JsonResponse({
                'success': True,
                'task_id': task.id,
                'status': 'queued',
                'message': 'Test queued for execution'
            })
        else:
            # Run synchronously
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(
                    run_natural_language_test(prompt, user_role, username, password)
                )
                
                return JsonResponse({
                    'success': True,
                    'result': result,
                    'status': 'completed'
                })
            finally:
                loop.close()
                
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON payload'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def run_rbac_test_suite_api(request):
    """
    Run comprehensive RBAC test suite via API.
    
    Expected JSON payload:
    {
        "async": false
    }
    """
    try:
        data = json.loads(request.body) if request.body else {}
        run_async = data.get('async', False)
        
        if run_async:
            # Run as Celery task
            task = run_rbac_test_suite_task.delay()
            
            return JsonResponse({
                'success': True,
                'task_id': task.id,
                'status': 'queued',
                'message': 'RBAC test suite queued for execution'
            })
        else:
            # Run synchronously
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(run_rbac_test_suite())
                
                return JsonResponse({
                    'success': True,
                    'result': result,
                    'status': 'completed'
                })
            finally:
                loop.close()
                
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON payload'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def get_test_results_api(request):
    """
    Get test results and logs.
    
    Query parameters:
    - log_id: Specific log ID to retrieve
    - limit: Number of recent logs to retrieve (default: 10)
    - status: Filter by status (pending, running, done, error)
    """
    try:
        log_id = request.GET.get('log_id')
        limit = int(request.GET.get('limit', 10))
        status = request.GET.get('status')
        
        if log_id:
            # Get specific log
            try:
                log = PlaywrightDebugLog.objects.get(id=log_id)
                return JsonResponse({
                    'success': True,
                    'log': {
                        'id': log.id,
                        'prompt': log.prompt,
                        'status': log.status,
                        'started_at': log.started_at.isoformat() if log.started_at else None,
                        'finished_at': log.finished_at.isoformat() if log.finished_at else None,
                        'output': log.output,
                        'result_json': log.result_json,
                        'error_message': log.error_message
                    }
                })
            except PlaywrightDebugLog.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'Log not found'
                }, status=404)
        else:
            # Get recent logs
            queryset = PlaywrightDebugLog.objects.all().order_by('-created_at')
            
            if status:
                queryset = queryset.filter(status=status)
            
            logs = queryset[:limit]
            
            return JsonResponse({
                'success': True,
                'logs': [{
                    'id': log.id,
                    'prompt': log.prompt,
                    'status': log.status,
                    'started_at': log.started_at.isoformat() if log.started_at else None,
                    'finished_at': log.finished_at.isoformat() if log.finished_at else None,
                    'created_at': log.created_at.isoformat(),
                    'error_message': log.error_message
                } for log in logs]
            })
            
    except ValueError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid limit parameter'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def get_test_screenshots_api(request):
    """
    Get test screenshots and HTML dumps.
    
    Query parameters:
    - log_id: Specific log ID to retrieve screenshots for
    - test_name: Filter by test name
    """
    try:
        log_id = request.GET.get('log_id')
        test_name = request.GET.get('test_name')
        
        if not log_id:
            return JsonResponse({
                'success': False,
                'error': 'log_id parameter is required'
            }, status=400)
        
        # Get the log
        try:
            log = PlaywrightDebugLog.objects.get(id=log_id)
        except PlaywrightDebugLog.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Log not found'
            }, status=404)
        
        # Extract screenshots and HTML dumps from result_json
        screenshots = []
        html_dumps = []
        
        if log.result_json:
            result = log.result_json
            screenshots = result.get('screenshots', [])
            html_dumps = result.get('html_dumps', [])
            
            # Filter by test name if specified
            if test_name:
                screenshots = [s for s in screenshots if test_name in s.get('name', '')]
                html_dumps = [h for h in html_dumps if test_name in h.get('name', '')]
        
        return JsonResponse({
            'success': True,
            'log_id': log_id,
            'screenshots': screenshots,
            'html_dumps': html_dumps,
            'total_screenshots': len(screenshots),
            'total_html_dumps': len(html_dumps)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def run_test_scenario_api(request):
    """
    Run a predefined test scenario.
    
    Expected JSON payload:
    {
        "scenario": "admin_tools",
        "user_role": "admin",
        "async": false
    }
    
    Available scenarios:
    - admin_tools: Test admin functionality (clear database, populate demo)
    - rbac_basic: Test basic RBAC permissions
    - equipment_management: Test equipment CRUD operations
    - maintenance_workflow: Test maintenance activity workflow
    """
    try:
        data = json.loads(request.body)
        scenario = data.get('scenario', '')
        user_role = data.get('user_role', 'admin')
        run_async = data.get('async', False)
        
        if not scenario:
            return JsonResponse({
                'success': False,
                'error': 'Scenario is required'
            }, status=400)
        
        # Define test scenarios
        scenarios = {
            'admin_tools': [
                'Test admin user can clear database with keep users option',
                'Test admin user can populate demo data with 5 users and 10 equipment'
            ],
            'rbac_basic': [
                'Test admin user can access settings page',
                'Test technician user cannot access admin tools',
                'Test manager user can view equipment list'
            ],
            'equipment_management': [
                'Test creating equipment called Test Transformer in default location',
                'Test viewing equipment list page',
                'Test equipment detail page loads correctly'
            ],
            'maintenance_workflow': [
                'Test maintenance activity list page',
                'Test creating maintenance activity',
                'Test maintenance report generation'
            ]
        }
        
        if scenario not in scenarios:
            return JsonResponse({
                'success': False,
                'error': f'Unknown scenario: {scenario}. Available: {list(scenarios.keys())}'
            }, status=400)
        
        test_prompts = scenarios[scenario]
        results = []
        
        if run_async:
            # Queue all tests as Celery tasks
            task_ids = []
            for prompt in test_prompts:
                task = run_natural_language_test_task.delay(
                    prompt=prompt,
                    user_role=user_role,
                    username='admin',
                    password='temppass123'
                )
                task_ids.append(task.id)
            
            return JsonResponse({
                'success': True,
                'scenario': scenario,
                'task_ids': task_ids,
                'status': 'queued',
                'message': f'Scenario {scenario} queued with {len(task_ids)} tests'
            })
        else:
            # Run tests synchronously
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                for prompt in test_prompts:
                    result = loop.run_until_complete(
                        run_natural_language_test(prompt, user_role, 'admin', 'temppass123')
                    )
                    results.append({
                        'prompt': prompt,
                        'result': result
                    })
                
                # Calculate scenario summary
                total_tests = len(results)
                passed_tests = sum(1 for r in results if r['result'].get('success', False))
                
                scenario_summary = {
                    'scenario': scenario,
                    'total_tests': total_tests,
                    'passed_tests': passed_tests,
                    'failed_tests': total_tests - passed_tests,
                    'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0,
                    'results': results
                }
                
                return JsonResponse({
                    'success': True,
                    'scenario_summary': scenario_summary,
                    'status': 'completed'
                })
            finally:
                loop.close()
                
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON payload'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@require_GET
def test_health(request):
    """Minimal health check endpoint for debug page AJAX."""
    import psutil
    try:
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent
        return JsonResponse({
            'status': 'ok',
            'cpu': cpu,
            'memory': mem,
            'disk': disk
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'error': str(e)}, status=500)

@require_GET
def test_database(request):
    """Database health check endpoint for debug page AJAX."""
    try:
        from django.db import connection
        from django.db.utils import OperationalError
        
        # Test database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
        
        # Get database stats
        from django.contrib.auth.models import User
        from core.models import Location, Customer
        from equipment.models import Equipment
        from maintenance.models import MaintenanceActivity
        
        stats = {
            'users': User.objects.count(),
            'locations': Location.objects.count(),
            'customers': Customer.objects.count(),
            'equipment': Equipment.objects.count(),
            'maintenance_activities': MaintenanceActivity.objects.count(),
        }
        
        return JsonResponse({
            'status': 'ok',
            'connection': 'healthy',
            'stats': stats
        })
    except OperationalError as e:
        return JsonResponse({
            'status': 'error',
            'error': f'Database connection failed: {str(e)}'
        }, status=500)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        }, status=500)

@require_GET
def test_cache(request):
    """Cache health check endpoint for debug page AJAX."""
    try:
        from django.core.cache import cache
        from django.conf import settings
        
        # Test cache connection
        test_key = 'debug_cache_test'
        test_value = 'test_value_123'
        
        # Set a test value
        cache.set(test_key, test_value, 60)
        
        # Get the test value
        retrieved_value = cache.get(test_key)
        
        # Clean up
        cache.delete(test_key)
        
        if retrieved_value == test_value:
            cache_status = 'healthy'
        else:
            cache_status = 'unhealthy'
        
        return JsonResponse({
            'status': 'ok',
            'cache': cache_status,
            'backend': getattr(settings, 'CACHES', {}).get('default', {}).get('BACKEND', 'unknown')
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        }, status=500)


# ========================================
# BULK LOCATION MANAGEMENT VIEWS
# ========================================

@login_required
@user_passes_test(is_staff_or_superuser)
@require_http_methods(["GET", "POST"])
def bulk_edit_locations(request):
    """Bulk edit locations (sites and sub-locations)."""
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode())
            action = data.get('action')
            location_ids = data.get('location_ids', [])
            
            if not location_ids:
                return JsonResponse({'success': False, 'error': 'No locations selected'})
            
            locations = Location.objects.filter(id__in=location_ids)
            
            if action == 'edit':
                # Bulk edit fields
                updates = data.get('updates', {})
                updated_count = 0
                
                for location in locations:
                    if 'name' in updates and updates['name'].strip():
                        location.name = updates['name'].strip()
                    if 'customer_id' in updates:
                        if updates['customer_id']:
                            location.customer_id = updates['customer_id']
                        else:
                            location.customer = None
                    if 'is_active' in updates:
                        location.is_active = updates['is_active']
                    
                    location.updated_by = request.user
                    location.save()
                    updated_count += 1
                
                return JsonResponse({
                    'success': True, 
                    'message': f'Successfully updated {updated_count} location(s)',
                    'updated_count': updated_count
                })
            
            elif action == 'move':
                # Move locations to new parent
                new_parent_id = data.get('new_parent_id')
                moved_count = 0
                
                for location in locations:
                    if new_parent_id:
                        new_parent = Location.objects.get(id=new_parent_id)
                        location.parent_location = new_parent
                    else:
                        location.parent_location = None
                    
                    location.updated_by = request.user
                    location.save()
                    moved_count += 1
                
                return JsonResponse({
                    'success': True,
                    'message': f'Successfully moved {moved_count} location(s)',
                    'moved_count': moved_count
                })
            
            elif action == 'delete':
                # Bulk delete locations
                deleted_count = 0
                errors = []
                
                for location in locations:
                    try:
                        # Check if location has children
                        if location.child_locations.exists():
                            errors.append(f'Cannot delete "{location.name}" - has child locations')
                            continue
                        
                        # Check if location has equipment
                        if hasattr(location, 'equipment_set') and location.equipment_set.exists():
                            errors.append(f'Cannot delete "{location.name}" - has associated equipment')
                            continue
                        
                        location_name = location.name
                        location.delete()
                        deleted_count += 1
                        
                    except Exception as e:
                        errors.append(f'Error deleting "{location.name}": {str(e)}')
                
                if errors:
                    return JsonResponse({
                        'success': False,
                        'message': f'Deleted {deleted_count} location(s). Errors: {"; ".join(errors)}',
                        'deleted_count': deleted_count,
                        'errors': errors
                    })
                else:
                    return JsonResponse({
                        'success': True,
                        'message': f'Successfully deleted {deleted_count} location(s)',
                        'deleted_count': deleted_count
                    })
            
            elif action == 'generate_pods':
                # Bulk generate pods for sites
                generated_count = 0
                errors = []
                
                for location in locations:
                    if not location.is_site:
                        errors.append(f'"{location.name}" is not a site - skipping pod generation')
                        continue
                    
                    try:
                        from django.core.management import call_command
                        from io import StringIO
                        
                        output = StringIO()
                        call_command('generate_pods', '--site-id', str(location.id), stdout=output)
                        output.close()
                        generated_count += 1
                        
                    except Exception as e:
                        errors.append(f'Error generating pods for "{location.name}": {str(e)}')
                
                if errors:
                    return JsonResponse({
                        'success': False,
                        'message': f'Generated pods for {generated_count} site(s). Errors: {"; ".join(errors)}',
                        'generated_count': generated_count,
                        'errors': errors
                    })
                else:
                    return JsonResponse({
                        'success': True,
                        'message': f'Successfully generated pods for {generated_count} site(s)',
                        'generated_count': generated_count
                    })
            
            else:
                return JsonResponse({'success': False, 'error': f'Unknown action: {action}'})
                
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    # GET request - return form data
    sites = Location.objects.filter(is_site=True, is_active=True).order_by('name')
    customers = Customer.objects.filter(is_active=True).order_by('name')
    
    return JsonResponse({
        'sites': [{'id': site.id, 'name': site.name} for site in sites],
        'customers': [{'id': customer.id, 'name': customer.name} for customer in customers]
    })


@login_required
@user_passes_test(is_staff_or_superuser)
def bulk_locations_view(request):
    """View for bulk location management interface."""
    # Get all locations with natural sorting
    locations = list(Location.objects.all().select_related('parent_location', 'customer'))
    locations.sort(key=lambda loc: natural_sort_key(loc.name))
    
    # Separate sites and sub-locations with natural sorting
    sites = [loc for loc in locations if loc.is_site]
    sites.sort(key=lambda site: natural_sort_key(site.name))
    
    sub_locations = [loc for loc in locations if not loc.is_site]
    sub_locations.sort(key=lambda loc: natural_sort_key(loc.name))
    
    # Add full path information to sub-locations
    for location in sub_locations:
        location.full_path = location.get_full_path()
        # Determine location type based on hierarchy
        if location.parent_location and location.parent_location.is_site:
            location.location_type = "POD"
        elif location.parent_location and location.parent_location.parent_location and location.parent_location.parent_location.is_site:
            location.location_type = "MDC"
        else:
            location.location_type = "Location"
    
    # Get customers for dropdowns
    customers = Customer.objects.filter(is_active=True).order_by('name')
    
    context = {
        'sites': sites,
        'sub_locations': sub_locations,
        'customers': customers,
        'total_locations': len(locations),
        'total_sites': len(sites),
        'total_sub_locations': len(sub_locations),
    }
    
    return render(request, 'core/bulk_locations.html', context)


@staff_member_required
def playwright_slideshow(request):
    """
    Display a slideshow of the latest Playwright test run steps/screenshots.
    """
    import json
    report_path = os.path.join(settings.BASE_DIR, 'playwright', 'smart-test-report.json')
    screenshots = []
    captions = []
    if os.path.exists(report_path):
        with open(report_path, 'r', encoding='utf-8') as f:
            report = json.load(f)
            for i, result in enumerate(report.get('results', [])):
                for j, screenshot in enumerate(result.get('screenshots', [])):
                    # Only use the filename for static serving
                    filename = os.path.basename(screenshot)
                    step_caption = f"Step {len(screenshots)+1}: {result.get('testName', 'Step')}"
                    if result.get('errors'):
                        step_caption += f" (Error: {result['errors'][0]})"
                    screenshots.append(filename)
                    captions.append(step_caption)
    context = {
        'screenshots': screenshots,
        'captions': captions,
    }
    return render(request, 'core/playwright_slideshow.html', context)


def get_comprehensive_system_health():
    """Get comprehensive system health (no Docker/container status)."""
    health_data = {
        'timestamp': timezone.now().isoformat(),
        'overall_status': 'healthy',
        'components': {}
    }
    
    # Database health
    db_health = check_database_health()
    health_data['components']['database'] = db_health
    
    # Cache health
    cache_health = check_cache_health()
    health_data['components']['cache'] = cache_health
    
    # Celery worker health
    celery_health = check_celery_worker_health()
    health_data['components']['celery_worker'] = celery_health
    
    # Celery beat health
    celery_beat_health = check_celery_beat_health()
    health_data['components']['celery_beat'] = celery_beat_health
    
    # System metrics
    try:
        system_metrics = get_system_metrics()
        health_data['components']['system'] = system_metrics
    except Exception as e:
        health_data['components']['system'] = {'error': str(e)}
    
    # Determine overall status
    if db_health.get('status') == 'unhealthy':
        health_data['overall_status'] = 'critical'
    elif cache_health.get('status') == 'unhealthy':
        health_data['overall_status'] = 'warning'
    elif celery_health.get('status') == 'unhealthy' or celery_beat_health.get('status') == 'unhealthy':
        health_data['overall_status'] = 'warning'
    
    return health_data


def check_celery_worker_health():
    """Check Celery worker health by running inspect ping."""
    try:
        import subprocess
        result = subprocess.run([
            'celery', '-A', 'maintenance_dashboard', 'inspect', 'ping'
        ], capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and 'pong' in result.stdout:
            return {'status': 'healthy', 'output': result.stdout}
        else:
            return {'status': 'unhealthy', 'output': result.stdout + result.stderr}
    except Exception as e:
        return {'status': 'unhealthy', 'error': str(e)}


def check_celery_beat_health():
    """Check Celery beat health by checking last run of periodic tasks."""
    try:
        from django_celery_beat.models import PeriodicTask
        from django.utils import timezone
        enabled_tasks = PeriodicTask.objects.filter(enabled=True)
        if not enabled_tasks.exists():
            return {'status': 'warning', 'message': 'No periodic tasks enabled'}
        recent = None
        for task in enabled_tasks:
            if task.last_run_at and (recent is None or task.last_run_at > recent):
                recent = task.last_run_at
        if recent:
            seconds_since = (timezone.now() - recent).total_seconds()
            if seconds_since < 600:
                return {'status': 'healthy', 'message': f'Recent heartbeat ({int(seconds_since)}s ago)'}
            else:
                return {'status': 'warning', 'message': f'No recent heartbeat (last was {int(seconds_since//60)} min ago)'}
        else:
            return {'status': 'warning', 'message': 'No periodic tasks have ever run'}
    except Exception as e:
        return {'status': 'unhealthy', 'error': str(e)}


@csrf_exempt
@require_http_methods(["GET"])
def comprehensive_health_check(request):
    """Comprehensive health check including container status."""
    try:
        health_data = get_comprehensive_system_health()
        return JsonResponse(health_data)
    except Exception as e:
        return JsonResponse({
            'timestamp': timezone.now().isoformat(),
            'overall_status': 'error',
            'error': str(e)
        }, status=500)


@login_required
@user_passes_test(is_staff_or_superuser)
@require_http_methods(["GET"])
def database_stats(request):
    """Get database statistics and information."""
    try:
        from django.db import connection
        from django.db.models import Count
        from .models import Location, Customer
        from equipment.models import Equipment
        from maintenance.models import MaintenanceActivity
        from events.models import CalendarEvent
        
        # Get basic counts
        stats = {
            'locations': {
                'total': Location.objects.count(),
                'sites': Location.objects.filter(is_site=True).count(),
                'sub_locations': Location.objects.filter(is_site=False).count(),
                'active': Location.objects.filter(is_active=True).count(),
            },
            'customers': {
                'total': Customer.objects.count(),
                'active': Customer.objects.filter(is_active=True).count(),
            },
            'equipment': {
                'total': Equipment.objects.count(),
                'active': Equipment.objects.filter(is_active=True).count(),
            },
            'maintenance': {
                'total': MaintenanceActivity.objects.count(),
                'completed': MaintenanceActivity.objects.filter(status='completed').count(),
                'pending': MaintenanceActivity.objects.filter(status='pending').count(),
            },
            'events': {
                'total': CalendarEvent.objects.count(),
                'recent': CalendarEvent.objects.filter(created_at__gte=timezone.now() - timezone.timedelta(days=7)).count(),
            }
        }
        
        # Get database size info
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    pg_size_pretty(pg_database_size(current_database())) as db_size,
                    pg_size_pretty(pg_total_relation_size('core_location')) as locations_size,
                    pg_size_pretty(pg_total_relation_size('core_customer')) as customers_size,
                    pg_size_pretty(pg_total_relation_size('equipment_equipment')) as equipment_size
            """)
            db_info = cursor.fetchone()
            
        stats['database'] = {
            'total_size': db_info[0] if db_info else 'Unknown',
            'locations_table_size': db_info[1] if db_info else 'Unknown',
            'customers_table_size': db_info[2] if db_info else 'Unknown',
            'equipment_table_size': db_info[3] if db_info else 'Unknown',
        }
        
        return JsonResponse({
            'success': True,
            'stats': stats,
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@user_passes_test(is_staff_or_superuser)
@require_http_methods(["POST"])
def backup_database(request):
    """Create a database backup."""
    try:
        from django.core.management import call_command
        from io import StringIO
        import os
        from django.conf import settings
        
        # Create backup directory if it doesn't exist
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        # Generate backup filename with timestamp
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'backup_{timestamp}.json'
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # Capture command output
        output = StringIO()
        
        # Call the dumpdata command
        call_command('dumpdata', 
                    '--exclude', 'contenttypes',
                    '--exclude', 'auth.Permission',
                    '--exclude', 'sessions',
                    '--indent', '2',
                    '--output', backup_path,
                    stdout=output,
                    verbosity=2)
        
        result = output.getvalue()
        output.close()
        
        # Get file size
        file_size = os.path.getsize(backup_path) if os.path.exists(backup_path) else 0
        
        return JsonResponse({
            'success': True,
            'message': f'Database backup created successfully: {backup_filename}',
            'filename': backup_filename,
            'file_size': file_size,
            'file_size_pretty': f'{file_size / 1024 / 1024:.2f} MB' if file_size > 0 else '0 B',
            'output': result
        })
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return JsonResponse({
            'success': False,
            'error': f'Error creating database backup: {str(e)}',
            'details': error_details
        }, status=500)


@login_required
@user_passes_test(is_staff_or_superuser)
@require_http_methods(["POST"])
def populate_sample_data(request):
    """Populate the database with sample data."""
    try:
        from django.core.management import call_command
        from io import StringIO
        
        # Capture command output
        output = StringIO()
        
        # Call the populate sample data command
        call_command('populate_sample_data', stdout=output, verbosity=2)
        
        result = output.getvalue()
        output.close()
        
        # Parse the output to extract counts
        created_count = 0
        
        # Look for patterns in the output
        import re
        created_matches = re.findall(r'Created (\d+)', result)
        
        if created_matches:
            created_count = sum(int(x) for x in created_matches)
        
        return JsonResponse({
            'success': True,
            'message': f'Sample data populated successfully! Created: {created_count} items',
            'created_count': created_count,
            'output': result
        })
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return JsonResponse({
            'success': False,
            'error': f'Error populating sample data: {str(e)}',
            'details': error_details
        }, status=500)


@login_required
@user_passes_test(is_staff_or_superuser)
@require_http_methods(["POST"])
def reset_rbac(request):
    """Reset RBAC (Role-Based Access Control) system."""
    try:
        from django.core.management import call_command
        from io import StringIO
        
        # Capture command output
        output = StringIO()
        
        # Call the reset RBAC command
        call_command('reset_rbac', stdout=output, verbosity=2)
        
        result = output.getvalue()
        output.close()
        
        return JsonResponse({
            'success': True,
            'message': 'RBAC system reset successfully',
            'output': result
        })
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return JsonResponse({
            'success': False,
            'error': f'Error resetting RBAC: {str(e)}',
            'details': error_details
        }, status=500)




@login_required
@user_passes_test(is_staff_or_superuser)
def webhook_settings(request):
    """Webhook management settings page."""
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'save_config':
            # Save configuration to environment file
            try:
                # Get current values to preserve if not changed
                current_user = getattr(settings, 'PORTAINER_USER', '')
                current_password = getattr(settings, 'PORTAINER_PASSWORD', '')
                current_secret = getattr(settings, 'PORTAINER_WEBHOOK_SECRET', '')
                
                # Handle sensitive fields - only update if user provides new values
                portainer_user = request.POST.get('portainer_user', '')
                portainer_password = request.POST.get('portainer_password', '')
                webhook_secret = request.POST.get('webhook_secret', '')
                
                # If user enters masked values (like "***"), keep current values
                if portainer_user and not portainer_user.startswith('***'):
                    current_user = portainer_user
                elif not portainer_user:
                    current_user = ''  # Allow clearing
                    
                if portainer_password and not portainer_password.startswith('*'):
                    current_password = portainer_password
                elif not portainer_password:
                    current_password = ''  # Allow clearing
                    
                if webhook_secret and not webhook_secret.startswith('****'):
                    current_secret = webhook_secret
                elif not webhook_secret:
                    current_secret = ''  # Allow clearing
                
                config_data = {
                    'PORTAINER_URL': request.POST.get('portainer_url', ''),
                    'PORTAINER_USER': current_user,
                    'PORTAINER_PASSWORD': current_password,
                    'PORTAINER_STACK_NAME': request.POST.get('stack_name', ''),
                    'PORTAINER_WEBHOOK_SECRET': current_secret,
                }
                
                # Validate required fields
                if not config_data['PORTAINER_URL']:
                    messages.error(request, 'Portainer URL is required. Please enter a valid URL.')
                    return redirect('core:webhook_settings')
                
                if not config_data['PORTAINER_STACK_NAME']:
                    messages.error(request, 'Stack Name is required. Please enter your stack name.')
                    return redirect('core:webhook_settings')
                
                # Save to environment file
                env_file_path = os.path.join(settings.BASE_DIR, 'deployment', 'env.development')
                save_result = save_webhook_config(env_file_path, config_data)
                
                if save_result:
                    # Show what was saved
                    saved_items = []
                    if config_data['PORTAINER_URL']:
                        saved_items.append(f"Portainer URL: {config_data['PORTAINER_URL']}")
                    if config_data['PORTAINER_STACK_NAME']:
                        saved_items.append(f"Stack Name: {config_data['PORTAINER_STACK_NAME']}")
                    if config_data['PORTAINER_USER']:
                        saved_items.append(f"Username: {config_data['PORTAINER_USER'][:3]}***")
                    if config_data['PORTAINER_PASSWORD']:
                        saved_items.append("Password: ********")
                    if config_data['PORTAINER_WEBHOOK_SECRET']:
                        saved_items.append(f"Secret: {config_data['PORTAINER_WEBHOOK_SECRET'][:4]}****")
                    
                    messages.success(request, f'Configuration saved successfully! Saved: {", ".join(saved_items)}')
                    
                    # Add a small delay to ensure file is written before redirect
                    time.sleep(0.5)
                else:
                    messages.error(request, 'Failed to save configuration. Please check file permissions.')
                    
            except FileNotFoundError:
                messages.error(request, 'Environment file not found. Please ensure the deployment/env.development file exists.')
            except PermissionError:
                messages.error(request, 'Permission denied. Cannot write to environment file. Please check file permissions.')
            except Exception as e:
                logger.error(f"Error saving webhook config: {str(e)}")
                messages.error(request, f'Error saving configuration: {str(e)}')
                
        elif action == 'test_webhook':
            # Test the webhook configuration
            try:
                portainer_url = getattr(settings, 'PORTAINER_URL', '')
                if not portainer_url:
                    messages.error(request, 'Cannot test connection: Portainer URL not configured. Please save your configuration first.')
                    return redirect('core:webhook_settings')
                
                result = test_portainer_connection()
                if 'successful' in result.lower():
                    messages.success(request, f'✅ Connection test successful: {result}')
                elif 'failed' in result.lower() or 'error' in result.lower():
                    messages.error(request, f'❌ Connection test failed: {result}')
                else:
                    messages.warning(request, f'⚠️ Connection test result: {result}')
            except Exception as e:
                logger.error(f"Error testing connection: {str(e)}")
                messages.error(request, f'❌ Connection test error: {str(e)}')
                
        elif action == 'update_stack':
            # Manually trigger stack update
            try:
                portainer_url = getattr(settings, 'PORTAINER_URL', '')
                stack_name = getattr(settings, 'PORTAINER_STACK_NAME', '')
                
                if not portainer_url or not stack_name:
                    messages.error(request, 'Cannot update stack: Portainer URL or Stack Name not configured. Please save your configuration first.')
                    return redirect('core:webhook_settings')
                
                result = trigger_portainer_stack_update()
                if 'successfully' in result.lower():
                    messages.success(request, f'✅ Stack update successful: {result}')
                elif 'failed' in result.lower() or 'error' in result.lower():
                    messages.error(request, f'❌ Stack update failed: {result}')
                else:
                    messages.warning(request, f'⚠️ Stack update result: {result}')
            except Exception as e:
                logger.error(f"Error updating stack: {str(e)}")
                messages.error(request, f'❌ Stack update error: {str(e)}')
        
        return redirect('core:webhook_settings')
    
    # Get non-sensitive data (show full values)
    portainer_url = getattr(settings, 'PORTAINER_URL', '')
    stack_name = getattr(settings, 'PORTAINER_STACK_NAME', '')
    
    # Mask sensitive data for display
    portainer_user = getattr(settings, 'PORTAINER_USER', '')
    portainer_password = getattr(settings, 'PORTAINER_PASSWORD', '')
    webhook_secret = getattr(settings, 'PORTAINER_WEBHOOK_SECRET', '')
    
    # Show masked values if they exist
    if portainer_user:
        portainer_user = portainer_user[:3] + '*' * (len(portainer_user) - 3) if len(portainer_user) > 3 else '***'
    if portainer_password:
        portainer_password = '*' * 8  # Show 8 asterisks for password
    if webhook_secret:
        webhook_secret = webhook_secret[:4] + '*' * (len(webhook_secret) - 4) if len(webhook_secret) > 4 else '****'
    
    # Debug logging
    logger.info(f"Portainer config loaded - URL: {portainer_url}, Stack: {stack_name}, User: {portainer_user[:3] if portainer_user else 'None'}***")
    
    context = {
        'portainer_url': portainer_url,
        'portainer_user': portainer_user,
        'portainer_password': portainer_password,
        'stack_name': stack_name,
        'webhook_secret': webhook_secret,
        'debug_info': {
            'url_exists': bool(portainer_url),
            'stack_exists': bool(stack_name),
            'user_exists': bool(portainer_user),
            'password_exists': bool(portainer_password),
            'secret_exists': bool(webhook_secret),
        }
    }
    
    return render(request, 'core/webhook_settings.html', context)


def trigger_portainer_stack_update():
    """Trigger a stack update via Portainer API."""
    try:
        portainer_url = getattr(settings, 'PORTAINER_URL', '')
        portainer_user = getattr(settings, 'PORTAINER_USER', '')
        portainer_pass = getattr(settings, 'PORTAINER_PASSWORD', '')
        stack_name = getattr(settings, 'PORTAINER_STACK_NAME', '')
        
        if not all([portainer_url, portainer_user, portainer_pass, stack_name]):
            return 'Configuration incomplete'
        
        # Get authentication token
        auth_response = requests.post(
            f"{portainer_url}/api/auth",
            json={'Username': portainer_user, 'Password': portainer_pass},
            timeout=10
        )
        
        if auth_response.status_code != 200:
            return f'Authentication failed: {auth_response.status_code}'
        
        token = auth_response.json().get('jwt')
        if not token:
            return 'No authentication token received'
        
        # Get stack ID
        headers = {'Authorization': f'Bearer {token}'}
        stacks_response = requests.get(
            f"{portainer_url}/api/stacks",
            headers=headers,
            timeout=10
        )
        
        if stacks_response.status_code != 200:
            return f'Failed to get stacks: {stacks_response.status_code}'
        
        stacks = stacks_response.json()
        stack_id = None
        
        for stack in stacks:
            if stack.get('Name') == stack_name:
                stack_id = stack.get('Id')
                break
        
        if not stack_id:
            return f'Stack "{stack_name}" not found'
        
        # Update the stack
        update_response = requests.put(
            f"{portainer_url}/api/stacks/{stack_id}",
            headers=headers,
            json={'prune': True, 'pullImage': True},
            timeout=30
        )
        
        if update_response.status_code == 200:
            return 'Stack updated successfully'
        else:
            return f'Update failed: {update_response.status_code}'
            
    except requests.exceptions.RequestException as e:
        return f'Network error: {str(e)}'
    except Exception as e:
        return f'Error: {str(e)}'


def save_webhook_config(env_file_path, config_data):
    """Save webhook configuration to environment file."""
    try:
        # Check if directory exists
        env_dir = os.path.dirname(env_file_path)
        if not os.path.exists(env_dir):
            logger.error(f"Directory does not exist: {env_dir}")
            return False
        
        # Read existing file
        existing_lines = []
        if os.path.exists(env_file_path):
            try:
                with open(env_file_path, 'r') as f:
                    existing_lines = f.readlines()
            except PermissionError:
                logger.error(f"Permission denied reading file: {env_file_path}")
                return False
            except Exception as e:
                logger.error(f"Error reading file {env_file_path}: {str(e)}")
                return False
        
        # Update or add configuration lines
        config_keys = list(config_data.keys())
        updated_lines = []
        keys_to_add = config_keys.copy()
        
        for line in existing_lines:
            line = line.strip()
            if not line or line.startswith('#'):
                updated_lines.append(line)
                continue
                
            if '=' in line:
                key = line.split('=')[0].strip()
                if key in config_keys:
                    # Update existing line
                    updated_lines.append(f"{key}={config_data[key]}")
                    keys_to_add.remove(key)
                else:
                    # Keep existing line
                    updated_lines.append(line)
            else:
                updated_lines.append(line)
        
        # Add new configuration lines
        for key in keys_to_add:
            if config_data[key]:  # Only add non-empty values
                updated_lines.append(f"{key}={config_data[key]}")
        
        # Write back to file
        try:
            with open(env_file_path, 'w') as f:
                f.write('\n'.join(updated_lines) + '\n')
            logger.info(f"Successfully saved webhook config to {env_file_path}")
            return True
        except PermissionError:
            logger.error(f"Permission denied writing to file: {env_file_path}")
            return False
        except Exception as e:
            logger.error(f"Error writing to file {env_file_path}: {str(e)}")
            return False
            
    except Exception as e:
        logger.error(f"Error saving webhook config: {str(e)}")
        return False


def test_portainer_connection():
    """Test connection to Portainer API."""
    try:
        portainer_url = getattr(settings, 'PORTAINER_URL', '')
        portainer_user = getattr(settings, 'PORTAINER_USER', '')
        portainer_pass = getattr(settings, 'PORTAINER_PASSWORD', '')
        
        if not all([portainer_url, portainer_user, portainer_pass]):
            return 'Configuration incomplete'
        
        # Test authentication
        auth_response = requests.post(
            f"{portainer_url}/api/auth",
            json={'Username': portainer_user, 'Password': portainer_pass},
            timeout=10
        )
        
        if auth_response.status_code == 200:
            return 'Connection successful'
        else:
            return f'Authentication failed: {auth_response.status_code}'
            
    except requests.exceptions.RequestException as e:
        return f'Network error: {str(e)}'
    except Exception as e:
        return f'Error: {str(e)}'