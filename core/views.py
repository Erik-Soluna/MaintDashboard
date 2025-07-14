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
from django.views.decorators.http import require_http_methods, require_POST
from django.core.management import call_command
from django.core.cache import cache
from django.db import connection
from django.conf import settings
from io import StringIO
import json
import csv
import io
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
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .models import PlaywrightDebugLog
from core.tasks import run_playwright_debug

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
    locations = Location.objects.all().order_by('name')
    sites = Location.objects.filter(is_site=True, is_active=True).prefetch_related('child_locations__child_locations').order_by('name')
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
        locations = Location.objects.all().values(
            'id', 'name', 'address', 'is_site', 'is_active', 'parent_location__name'
        )
        return JsonResponse(list(locations), safe=False)
    
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
        r = redis.Redis.from_url('redis://redis:6379/0')
        r.ping()
        checks.append({'name': 'Redis', 'status': 'ok', 'message': 'Connected'})
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
        
        # Basic Redis check
        r = redis.Redis.from_url('redis://redis:6379/0')
        r.ping()
        
        return JsonResponse({'status': 'ok'}, status=200)
    except Exception as e:
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


def api_explorer(request):
    """API Explorer: Tree view of all models and API documentation."""
    return render(request, 'core/api_explorer.html')


@login_required
def system_health(request):
    """System health/diagnostics page for superusers/admins."""
    if not request.user.is_superuser:
        return redirect('core:dashboard')
    return render(request, 'core/system_health.html')


@login_required
@user_passes_test(is_staff_or_superuser)
@require_http_methods(["POST"])
def generate_pods(request):
    """Generate PODs for existing sites."""
    try:
        from django.core.management import call_command
        from io import StringIO
        
        # Get parameters from request
        site_id = request.POST.get('site_id')
        site_name = request.POST.get('site_name')
        pod_count = int(request.POST.get('pod_count', 11))
        mdcs_per_pod = int(request.POST.get('mdcs_per_pod', 2))
        force = request.POST.get('force', 'false').lower() == 'true'
        
        # Capture command output
        output = StringIO()
        
        # Build command arguments
        args = ['generate_pods']
        if site_id:
            args.extend(['--site-id', site_id])
        elif site_name:
            args.extend(['--site-name', site_name])
        
        args.extend(['--pod-count', str(pod_count)])
        args.extend(['--mdcs-per-pod', str(mdcs_per_pod)])
        
        if force:
            args.append('--force')
        
        # Call the management command
        call_command(*args, stdout=output)
        
        # Get the output
        command_output = output.getvalue()
        output.close()
        
        return JsonResponse({
            'success': True,
            'message': 'PODs generated successfully',
            'output': command_output
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error generating PODs: {str(e)}'
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
    """Populate the database with comprehensive demo data for all major datapoints."""
    try:
        from django.core.management import call_command
        from io import StringIO
        output = StringIO()
        
        # Get parameters from request
        reset_data = request.POST.get('reset_data', 'false').lower() == 'true'
        users_count = int(request.POST.get('users_count', 10))
        equipment_count = int(request.POST.get('equipment_count', 50))
        activities_count = int(request.POST.get('activities_count', 100))
        events_count = int(request.POST.get('events_count', 75))
        
        # Build command arguments
        args = ['populate_comprehensive_demo_data']
        
        if reset_data:
            args.append('--reset')
        
        args.extend([
            '--users', str(users_count),
            '--equipment', str(equipment_count),
            '--activities', str(activities_count),
            '--events', str(events_count)
        ])
        
        # Call the comprehensive demo data command
        call_command(*args, stdout=output)
        
        result = output.getvalue()
        output.close()
        
        return JsonResponse({
            'success': True,
            'message': f'Comprehensive demo data populated successfully! Created {users_count} users, {equipment_count} equipment items, {activities_count} maintenance activities, and {events_count} calendar events.',
            'output': result
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error populating demo data: {str(e)}',
            'output': str(e)
        })


@login_required
@user_passes_test(is_staff_or_superuser)
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
        args = ['clear_database']
        
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
        return JsonResponse({
            'success': False,
            'error': f'Error clearing database: {str(e)}'
        }, status=500)