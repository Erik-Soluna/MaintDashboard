"""dashboard views (split from the original monolithic views.py)."""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth.models import User
from equipment.models import Equipment
from maintenance.models import MaintenanceActivity
from events.models import CalendarEvent
from core.models import Location, EquipmentCategory, Role, Permission, UserProfile, Customer, BrandingSettings, DashboardSettings, CSSCustomization
from core.forms import LocationForm, EquipmentCategoryForm, CustomerForm, UserForm, BrandingSettingsForm, BrandingBasicForm, BrandingNavigationForm, BrandingAppearanceForm, CSSCustomizationForm, CSSPreviewForm, DashboardSettingsForm
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
import shutil
import redis
from django_celery_beat.models import PeriodicTask
import requests
from django.test import RequestFactory
from django.contrib.admin.views.decorators import staff_member_required
import hmac
import hashlib
import os
import shutil
import redis
from django_celery_beat.models import PeriodicTask
from django.utils import timezone
from .helpers import *  # noqa: F401,F403 (shared helpers + globals)


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
    is_all_sites = False
    
    if selected_site_id is not None:
        # If site_id is explicitly provided (even if empty), use it
        if selected_site_id == '' or selected_site_id == 'all':
            # Clear site selection (All Sites) - use special marker
            request.session['selected_site_id'] = 'all'
            selected_site_id = None
            is_all_sites = True
        else:
            # Set specific site selection
            request.session['selected_site_id'] = selected_site_id
            is_all_sites = False
    else:
        # No site_id in request, check session or default
        selected_site_id = request.session.get('selected_site_id')
        
        # If session has 'all', keep it as None (All Sites)
        if selected_site_id == 'all':
            selected_site_id = None
            is_all_sites = True
        elif not selected_site_id and user_profile.default_site:
            selected_site_id = str(user_profile.default_site.id)
            request.session['selected_site_id'] = selected_site_id
            is_all_sites = False
        else:
            is_all_sites = True
    
    # Create cache key for this dashboard view
    cache_key = f"dashboard_data_{selected_site_id or 'all'}_{request.user.id}"
    cache_timeout = 300  # 5 minutes
    
    # Note: Full context caching disabled due to QuerySet serialization issues
    # Cache individual expensive queries instead if needed
    # cached_data = cache.get(cache_key)
    # if cached_data:
    #     return render(request, 'core/dashboard.html', cached_data)
    
    # Get all sites for the site selector
    sites = Location.objects.filter(is_site=True, is_active=True).order_by('name')
    selected_site = None
    if selected_site_id and not is_all_sites:
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
        # Note: Don't slice here - we need to filter these querysets later
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
        # CRITICAL: Must get IDs first, then prefetch only those to avoid loading excessive data
        # This prevents loading 1000+ locations when we only need 100
        # Step 1: Get just the IDs of locations (no prefetch, very fast)
        location_ids_queryset = Location.objects.filter(
            parent_location=selected_site,
            is_active=True
        ).values_list('id', flat=True)
        
        # Get all IDs and sort them (we'll sort by name after loading)
        all_location_ids = list(location_ids_queryset)
        
        # Limit to 100 IDs before doing expensive prefetch operations
        limited_location_ids = all_location_ids[:100]
        
        # Step 2: Now load only those 100 locations with full prefetch
        # This way we only prefetch data for the locations we'll actually use
        if limited_location_ids:
            from django.db.models import Prefetch
            
            # Use Prefetch objects to ensure no slices are applied to prefetch querysets
            # Must use explicit queryset to avoid any default manager slices
            # Create explicit queryset for maintenance activities with no slices
            # Note: MaintenanceActivity is imported at the top of the file
            maintenance_activities_qs = MaintenanceActivity.objects.select_related('assigned_to').all()
            
            locations_queryset = Location.objects.filter(
                id__in=limited_location_ids
            ).select_related('parent_location', 'customer').prefetch_related(
                'equipment',  # Simple prefetch without slice
                'equipment__category',  # Prefetch category for equipment
                Prefetch(
                    'equipment__maintenance_activities',
                    queryset=maintenance_activities_qs
                )
            )
            locations = list(locations_queryset)
            locations.sort(key=lambda loc: natural_sort_key(loc.name))
        else:
            locations = []
        
    else:
        # Global queries
        # Note: Don't slice here - we need to filter these querysets later
        equipment_query = Equipment.objects.select_related('location', 'category')
        maintenance_query = MaintenanceActivity.objects.select_related(
            'equipment', 'equipment__location', 'equipment__category', 'assigned_to'
        )
        calendar_query = CalendarEvent.objects.select_related(
            'equipment', 'equipment__location', 'assigned_to'
        )
        
        # Show top-level locations if no site selected
        # Evaluate queryset first to avoid prefetch issues
        locations_queryset = Location.objects.filter(
            is_site=False,
            is_active=True
        ).select_related('parent_location', 'customer')
        locations = list(locations_queryset[:8])  # Limit after evaluation
        locations.sort(key=lambda loc: natural_sort_key(loc.name))
    
    # ===== BULK STATISTICS CALCULATION =====
    
    # Get dashboard settings (handle case where table doesn't exist yet)
    dashboard_settings = None
    try:
        from core.models import DashboardSettings
        dashboard_settings = DashboardSettings.get_active()
    except Exception:
        # Table doesn't exist yet or other error - use defaults
        pass
    
    # Use settings for cutoff days if available
    urgent_days = dashboard_settings.urgent_days_ahead if dashboard_settings else 7
    upcoming_days = dashboard_settings.upcoming_days_ahead if dashboard_settings else 30
    urgent_cutoff = today + timedelta(days=urgent_days)
    upcoming_cutoff = today + timedelta(days=upcoming_days)
    
    # Calculate urgent items with single queries - only show maintenance activities to avoid duplication
    # Use status filters from dashboard settings
    max_items = 200  # Reasonable limit to prevent excessive memory usage
    now = timezone.now()

    # Aware datetime bounds for filtering DateTimeFields (scheduled_*/actual_end).
    # Comparing a bare date against a DateTimeField emits a naive-datetime warning
    # and is coerced to UTC midnight; build explicit aware bounds instead.
    from datetime import datetime as _dt, time as _time
    today_dt = timezone.make_aware(_dt.combine(today, _time.min))
    urgent_cutoff_dt = timezone.make_aware(_dt.combine(urgent_cutoff, _time.max))
    upcoming_cutoff_dt = timezone.make_aware(_dt.combine(upcoming_cutoff, _time.max))
    
    # Get status filters from dashboard settings
    urgent_statuses = dashboard_settings.urgent_statuses if dashboard_settings and dashboard_settings.urgent_statuses else ['scheduled', 'overdue']
    
    urgent_maintenance_all = list(maintenance_query.filter(
        Q(status__in=urgent_statuses) & (
            Q(status='overdue') |  # Items explicitly marked as overdue
            (Q(scheduled_start__lt=now) & ~Q(status__in=['completed', 'cancelled'])) |  # Items past scheduled start date (overdue)
            # Items within urgent window (0-7 days)
            (Q(scheduled_end__lte=urgent_cutoff_dt) & Q(scheduled_end__gte=today_dt)) |
            # Items with only scheduled_start in urgent window
            Q(scheduled_end__isnull=True, scheduled_start__lte=urgent_cutoff_dt, scheduled_start__gte=today_dt)
        )
    ).order_by('scheduled_end', 'scheduled_start')[:max_items])
    
    # Filter out calendar events that are synced with maintenance activities to avoid duplication
    urgent_calendar_all = list(calendar_query.filter(
        event_date__lte=urgent_cutoff,
        event_date__gte=today,
        is_completed=False,
        maintenance_activity__isnull=True  # Only show calendar events NOT synced with maintenance
    ).order_by('event_date')[:max_items])
    
    # Calculate upcoming items with single queries - only show maintenance activities to avoid duplication
    # Upcoming items are those scheduled AFTER the urgent window (7-30 days from dashboard settings)
    # Use status filters from dashboard settings
    upcoming_statuses = dashboard_settings.upcoming_statuses if dashboard_settings and dashboard_settings.upcoming_statuses else ['pending', 'scheduled', 'in_progress']
    
    upcoming_maintenance_all = list(maintenance_query.filter(
        Q(
            # Items with scheduled_end AFTER urgent window but within upcoming window (7-30 days)
            Q(scheduled_end__gt=urgent_cutoff_dt, scheduled_end__lte=upcoming_cutoff_dt) |
            # Items with only scheduled_start AFTER urgent window but within upcoming window
            Q(scheduled_end__isnull=True, scheduled_start__gt=urgent_cutoff_dt, scheduled_start__lte=upcoming_cutoff_dt)
        ),
        status__in=upcoming_statuses
    ).exclude(
        # Exclude overdue items (they go to urgent)
        Q(status='overdue') |
        # Exclude items that are past their scheduled_end (they're overdue and go to urgent)
        Q(scheduled_end__lt=now, status__in=['pending', 'scheduled']) |
        # Exclude items that are past their scheduled_start if no scheduled_end (they're overdue)
        Q(scheduled_end__isnull=True, scheduled_start__lt=now, status__in=['pending', 'scheduled'])
    ).order_by('scheduled_end', 'scheduled_start')[:max_items])
    
    # Filter out calendar events that are synced with maintenance activities to avoid duplication
    # Upcoming calendar events are those from today to 30 days (respecting dashboard settings)
    upcoming_calendar_all = list(calendar_query.filter(
        event_date__gte=today,  # From today onwards
        event_date__lte=upcoming_cutoff,  # Within upcoming window (up to 30 days from dashboard settings)
        is_completed=False,
        maintenance_activity__isnull=True  # Only show calendar events NOT synced with maintenance
    ).order_by('event_date')[:max_items])
    
    # Calculate active items - use status filters from dashboard settings
    active_statuses = dashboard_settings.active_statuses if dashboard_settings and dashboard_settings.active_statuses else ['pending', 'in_progress']
    
    active_maintenance_all = list(maintenance_query.filter(
        status__in=active_statuses
    ).order_by('-scheduled_start', '-created_at')[:max_items])
    
    # Filter out calendar events that are synced with maintenance activities to avoid duplication
    # Note: Calendar events don't have in_progress/pending status, so we'll only show maintenance activities for active items
    active_calendar_all = []  # Calendar events don't have in_progress/pending status
    
    # Group items by site if enabled
    group_by_site = dashboard_settings.group_urgent_by_site if dashboard_settings else True
    group_upcoming = dashboard_settings.group_upcoming_by_site if dashboard_settings else True
    group_active = dashboard_settings.group_active_by_site if dashboard_settings else True
    urgent_maintenance_by_site = {}
    urgent_maintenance_by_site_grouped = {}
    urgent_calendar_by_site = {}
    upcoming_maintenance_by_site = {}
    upcoming_maintenance_by_site_grouped = {}
    upcoming_calendar_by_site = {}
    active_maintenance_by_site = {}
    active_maintenance_by_site_grouped = {}
    active_calendar_by_site = {}
    
    if group_by_site and is_all_sites:
        # Build site mapping dictionary to avoid N+1 queries
        # Prefetch all locations with their parent relationships
        location_ids = set()
        for item in urgent_maintenance_all:
            if item.equipment and item.equipment.location:
                location_ids.add(item.equipment.location.id)
        for event in urgent_calendar_all:
            if event.equipment and event.equipment.location:
                location_ids.add(event.equipment.location.id)
        for item in upcoming_maintenance_all:
            if item.equipment and item.equipment.location:
                location_ids.add(item.equipment.location.id)
        for event in upcoming_calendar_all:
            if event.equipment and event.equipment.location:
                location_ids.add(event.equipment.location.id)
        for item in active_maintenance_all:
            if item.equipment and item.equipment.location:
                location_ids.add(item.equipment.location.id)
        
        # Fetch all locations with prefetched parent relationships
        locations_with_parents = Location.objects.filter(id__in=location_ids).select_related('parent_location')
        location_to_site = {}
        for loc in locations_with_parents:
            site = loc.get_site_location()
            location_to_site[loc.id] = site.name if site else "Unknown Site"
        
        # Group urgent maintenance by site, then by activity type
        urgent_maintenance_by_site_and_type = {}
        for item in urgent_maintenance_all:
            if item.equipment and item.equipment.location:
                site_name = location_to_site.get(item.equipment.location.id, "Unknown Site")
            else:
                site_name = "Unknown Site"
            
            activity_type_name = item.activity_type.name if item.activity_type else "Unknown"
            
            if site_name not in urgent_maintenance_by_site_and_type:
                urgent_maintenance_by_site_and_type[site_name] = {}
            if activity_type_name not in urgent_maintenance_by_site_and_type[site_name]:
                urgent_maintenance_by_site_and_type[site_name][activity_type_name] = []
            
            max_per_type = (dashboard_settings.max_urgent_items_per_site if dashboard_settings else 15) * 2
            if len(urgent_maintenance_by_site_and_type[site_name][activity_type_name]) < max_per_type:
                urgent_maintenance_by_site_and_type[site_name][activity_type_name].append(item)
        
        # Convert to flat structure for backwards compatibility
        for site_name, activity_types in urgent_maintenance_by_site_and_type.items():
            urgent_maintenance_by_site[site_name] = []
            for activity_type_name, items in activity_types.items():
                urgent_maintenance_by_site[site_name].extend(items)
        
        # Store the grouped structure for the template
        urgent_maintenance_by_site_grouped = {}
        for site_name, activity_types in urgent_maintenance_by_site_and_type.items():
            total_count = sum(len(items) for items in activity_types.values())
            urgent_maintenance_by_site_grouped[site_name] = {
                'activity_types': activity_types,
                'total_count': total_count
            }
        
        # Group urgent calendar by site
        for event in urgent_calendar_all:
            if event.equipment and event.equipment.location:
                site_name = location_to_site.get(event.equipment.location.id, "Unknown Site")
            else:
                site_name = "Unknown Site"
            if site_name not in urgent_calendar_by_site:
                urgent_calendar_by_site[site_name] = []
            if len(urgent_calendar_by_site[site_name]) < (dashboard_settings.max_urgent_items_per_site if dashboard_settings else 15):
                urgent_calendar_by_site[site_name].append(event)
        
        # Group upcoming maintenance by site, then by activity type
        if group_upcoming:
            # Structure: {site_name: {activity_type_name: [items]}}
            upcoming_maintenance_by_site_and_type = {}
            for item in upcoming_maintenance_all:
                if item.equipment and item.equipment.location:
                    site_name = location_to_site.get(item.equipment.location.id, "Unknown Site")
                else:
                    site_name = "Unknown Site"
                
                activity_type_name = item.activity_type.name if item.activity_type else "Unknown"
                
                if site_name not in upcoming_maintenance_by_site_and_type:
                    upcoming_maintenance_by_site_and_type[site_name] = {}
                if activity_type_name not in upcoming_maintenance_by_site_and_type[site_name]:
                    upcoming_maintenance_by_site_and_type[site_name][activity_type_name] = []
                
                max_per_type = (dashboard_settings.max_upcoming_items_per_site if dashboard_settings else 15) * 2  # Allow more per type
                if len(upcoming_maintenance_by_site_and_type[site_name][activity_type_name]) < max_per_type:
                    upcoming_maintenance_by_site_and_type[site_name][activity_type_name].append(item)
            
            # Convert to flat structure for backwards compatibility
            for site_name, activity_types in upcoming_maintenance_by_site_and_type.items():
                upcoming_maintenance_by_site[site_name] = []
                for activity_type_name, items in activity_types.items():
                    upcoming_maintenance_by_site[site_name].extend(items)
            
            # Store the grouped structure for the template
            # Also calculate total counts per site for display
            upcoming_maintenance_by_site_grouped = {}
            for site_name, activity_types in upcoming_maintenance_by_site_and_type.items():
                total_count = sum(len(items) for items in activity_types.values())
                upcoming_maintenance_by_site_grouped[site_name] = {
                    'activity_types': activity_types,
                    'total_count': total_count
                }
            
            # Group upcoming calendar by site
            for event in upcoming_calendar_all:
                if event.equipment and event.equipment.location:
                    site_name = location_to_site.get(event.equipment.location.id, "Unknown Site")
                else:
                    site_name = "Unknown Site"
                if site_name not in upcoming_calendar_by_site:
                    upcoming_calendar_by_site[site_name] = []
                if len(upcoming_calendar_by_site[site_name]) < (dashboard_settings.max_upcoming_items_per_site if dashboard_settings else 15):
                    upcoming_calendar_by_site[site_name].append(event)
        
        # Group active maintenance by site, then by activity type
        if group_active:
            active_maintenance_by_site_and_type = {}
            for item in active_maintenance_all:
                if item.equipment and item.equipment.location:
                    site_name = location_to_site.get(item.equipment.location.id, "Unknown Site")
                else:
                    site_name = "Unknown Site"
                
                activity_type_name = item.activity_type.name if item.activity_type else "Unknown"
                
                if site_name not in active_maintenance_by_site_and_type:
                    active_maintenance_by_site_and_type[site_name] = {}
                if activity_type_name not in active_maintenance_by_site_and_type[site_name]:
                    active_maintenance_by_site_and_type[site_name][activity_type_name] = []
                
                max_per_type = (dashboard_settings.max_active_items_per_site if dashboard_settings else 15) * 2
                if len(active_maintenance_by_site_and_type[site_name][activity_type_name]) < max_per_type:
                    active_maintenance_by_site_and_type[site_name][activity_type_name].append(item)
            
            # Convert to flat structure for backwards compatibility
            for site_name, activity_types in active_maintenance_by_site_and_type.items():
                active_maintenance_by_site[site_name] = []
                for activity_type_name, items in activity_types.items():
                    active_maintenance_by_site[site_name].extend(items)
            
            # Store the grouped structure for the template
            active_maintenance_by_site_grouped = {}
            for site_name, activity_types in active_maintenance_by_site_and_type.items():
                total_count = sum(len(items) for items in activity_types.values())
                active_maintenance_by_site_grouped[site_name] = {
                    'activity_types': activity_types,
                    'total_count': total_count
                }
        else:
            active_maintenance_by_site_grouped = {}
    
    # For backwards compatibility, keep flat lists
    urgent_maintenance = urgent_maintenance_all[:dashboard_settings.max_urgent_items_total if dashboard_settings else 50]
    urgent_calendar = urgent_calendar_all[:10]
    upcoming_maintenance = upcoming_maintenance_all[:dashboard_settings.max_upcoming_items_total if dashboard_settings else 50]
    upcoming_calendar = upcoming_calendar_all[:10]
    active_maintenance = active_maintenance_all[:dashboard_settings.max_active_items_total if dashboard_settings else 50]
    active_calendar = active_calendar_all[:10]
    
    # Calculate total counts for grouped items
    urgent_total_count = 0
    upcoming_total_count = 0
    active_total_count = 0
    
    if group_by_site and is_all_sites:
        # Count from grouped data
        for site_items in urgent_maintenance_by_site.values():
            urgent_total_count += len(site_items)
        for site_events in urgent_calendar_by_site.values():
            urgent_total_count += len(site_events)
        
        if group_upcoming:
            for site_items in upcoming_maintenance_by_site.values():
                upcoming_total_count += len(site_items)
            for site_events in upcoming_calendar_by_site.values():
                upcoming_total_count += len(site_events)
        
        # Count active items from grouped data
        group_active = dashboard_settings.group_active_by_site if dashboard_settings else True
        if group_active:
            for site_items in active_maintenance_by_site.values():
                active_total_count += len(site_items)
    else:
        # Count from flat lists
        urgent_total_count = len(urgent_maintenance) + len(urgent_calendar)
        upcoming_total_count = len(upcoming_maintenance) + len(upcoming_calendar)
        active_total_count = len(active_maintenance) + len(active_calendar)
    
    # ===== OPTIMIZED OVERVIEW DATA CALCULATION =====
    
    if selected_site:
        # POD STATUS - Use prefetched data to avoid N+1 queries
        overview_data = []
        
        # Get all equipment and maintenance data in bulk
        # NOTE: Calendar events are deprecated - only use maintenance activities
        pod_equipment = {loc.id: [] for loc in locations}
        pod_maintenance = {loc.id: [] for loc in locations}
        
        # Organize equipment by location - Limit to prevent excessive memory usage
        for equipment in equipment_query[:1000]:  # Limit to 1000 items
            if equipment.location and equipment.location.id in pod_equipment:
                pod_equipment[equipment.location.id].append(equipment)
        
        # Organize maintenance by location - Limit to prevent excessive memory usage
        for maintenance in maintenance_query[:1000]:  # Limit to 1000 items
            if maintenance.equipment and maintenance.equipment.location and maintenance.equipment.location.id in pod_maintenance:
                pod_maintenance[maintenance.equipment.location.id].append(maintenance)
        
        # Process each location with bulk data
        for location in locations:
            location_equipment = pod_equipment.get(location.id, [])
            location_maintenance = pod_maintenance.get(location.id, [])
            
            # Calculate counts from in-memory data
            equipment_in_maintenance = sum(1 for eq in location_equipment if eq.status == 'maintenance')
            active_equipment = sum(1 for eq in location_equipment if eq.status == 'active')
            total_equipment = len(location_equipment)
            
            # Calculate IN MAINT count: equipment in maintenance OR maintenance activities in progress
            in_maint_count = equipment_in_maintenance
            in_maint_count += sum(
                1 for ma in location_maintenance
                if ma.status == 'in_progress' and ma.equipment and ma.equipment.status != 'maintenance'
            )
            
            # Calculate UPCOMING count: maintenance activities scheduled AFTER urgent window but within upcoming window
            # upcoming_cutoff is configured in Dashboard Settings (default: 30 days)
            # urgent_cutoff is configured in Dashboard Settings (default: 7 days)
            # This matches the same logic used for the "Upcoming Items" section on the overview page
            # Items in urgent window (0-7 days) go to urgent, items after urgent window (7-30 days) go to upcoming
            upcoming_maintenance_count = 0
            for ma in location_maintenance:
                if ma.status not in ['scheduled', 'pending', 'in_progress'] or ma.status == 'overdue':
                    continue
                
                # Check if item is in upcoming window (after urgent cutoff, within upcoming cutoff)
                is_upcoming = False
                if ma.scheduled_end:
                    scheduled_date = ma.scheduled_end.date()
                    if scheduled_date > urgent_cutoff and scheduled_date <= upcoming_cutoff:
                        is_upcoming = True
                elif ma.scheduled_start:
                    scheduled_date = ma.scheduled_start.date()
                    if scheduled_date > urgent_cutoff and scheduled_date <= upcoming_cutoff:
                        is_upcoming = True
                
                # Exclude items that are past their scheduled date (they're overdue)
                if is_upcoming:
                    if ma.scheduled_end and ma.scheduled_end.date() < today:
                        is_upcoming = False
                    elif not ma.scheduled_end and ma.scheduled_start and ma.scheduled_start.date() < today:
                        is_upcoming = False
                
                if is_upcoming:
                    upcoming_maintenance_count += 1
            
            # Get recent activities (filter out any that might have been deleted)
            recent_activities = []
            for ma in location_maintenance:
                try:
                    # Verify the maintenance activity still exists in the database
                    if (ma.actual_end and 
                        ma.actual_end.date() >= today - timedelta(days=30) and
                        ma.status == 'completed'):
                        recent_activities.append(ma)
                except Exception:
                    # Maintenance activity was deleted, skip it
                    continue
            
            recent_activities.sort(key=lambda x: x.actual_end, reverse=True)
            recent_activities = recent_activities[:3]
            
            # Get next upcoming maintenance activities (replacing deprecated calendar events)
            # Show upcoming maintenance activities scheduled in the future
            next_events = []
            for ma in location_maintenance:
                try:
                    # Verify the maintenance activity still exists in the database
                    # Show scheduled/pending activities that are upcoming (within upcoming window)
                    if (ma.status in ['scheduled', 'pending', 'in_progress'] and
                        not ma.status == 'overdue'):
                        # Check if it's in the upcoming window (after urgent cutoff, within upcoming cutoff)
                        scheduled_date = None
                        if ma.scheduled_end:
                            scheduled_date = ma.scheduled_end.date()
                        elif ma.scheduled_start:
                            scheduled_date = ma.scheduled_start.date()
                        
                        if scheduled_date and scheduled_date >= today:
                            # Include if it's in the upcoming window (7-30 days) or urgent window (0-7 days)
                            if scheduled_date <= upcoming_cutoff:
                                next_events.append(ma)
                except Exception:
                    # Maintenance activity was deleted, skip it
                    continue
            
            # Sort by scheduled date (use scheduled_end if available, otherwise scheduled_start)
            next_events.sort(key=lambda x: (x.scheduled_end.date() if x.scheduled_end else x.scheduled_start.date()) if (x.scheduled_end or x.scheduled_start) else today)
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
                'in_maint_count': in_maint_count,  # Total count including in_progress activities
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
        
        # Optimize: Get all site data in bulk queries instead of per-site queries
        site_ids = [site.id for site in all_sites]
        
        # Bulk equipment counts per site
        from django.db.models import Case, When, IntegerField
        equipment_by_site = Equipment.objects.filter(
            Q(location__parent_location_id__in=site_ids) | Q(location_id__in=site_ids)
        ).values('location__parent_location_id', 'location_id', 'status').annotate(count=Count('id'))
        
        # Bulk maintenance counts per site
        maintenance_by_site = MaintenanceActivity.objects.filter(
            Q(equipment__location__parent_location_id__in=site_ids) | Q(equipment__location_id__in=site_ids)
        ).values('equipment__location__parent_location_id', 'equipment__location_id', 'status').annotate(count=Count('id'))
        
        # Bulk overdue maintenance counts
        overdue_by_site = MaintenanceActivity.objects.filter(
            Q(equipment__location__parent_location_id__in=site_ids) | Q(equipment__location_id__in=site_ids),
            scheduled_end__lt=timezone.now(),
            status__in=['pending', 'scheduled']
        ).values('equipment__location__parent_location_id', 'equipment__location_id').annotate(count=Count('id'))
        
        # Bulk upcoming maintenance counts - items AFTER urgent window but within upcoming window
        # Use scheduled_end if available, otherwise scheduled_start
        upcoming_by_site = MaintenanceActivity.objects.filter(
            Q(equipment__location__parent_location_id__in=site_ids) | Q(equipment__location_id__in=site_ids),
            Q(
                # Items with scheduled_end AFTER urgent window but within upcoming window
                Q(scheduled_end__gt=urgent_cutoff_dt, scheduled_end__lte=upcoming_cutoff_dt) |
                # Items with only scheduled_start AFTER urgent window but within upcoming window
                Q(scheduled_end__isnull=True, scheduled_start__gt=urgent_cutoff_dt, scheduled_start__lte=upcoming_cutoff_dt)
            ),
            status__in=['scheduled', 'pending', 'in_progress']
        ).exclude(
            Q(status='overdue') |
            Q(scheduled_end__lt=now, status__in=['pending', 'scheduled']) |
            Q(scheduled_end__isnull=True, scheduled_start__lt=now, status__in=['pending', 'scheduled'])
        ).values('equipment__location__parent_location_id', 'equipment__location_id').annotate(count=Count('id'))
        
        # Build lookup dictionaries
        site_equipment_lookup = {}
        site_maintenance_lookup = {}
        site_overdue_lookup = {}
        site_upcoming_lookup = {}
        
        for item in equipment_by_site:
            site_id = item.get('location__parent_location_id') or item.get('location_id')
            if site_id:
                if site_id not in site_equipment_lookup:
                    site_equipment_lookup[site_id] = {}
                # Sum counts for the same status from different locations within the same site
                status = item['status']
                site_equipment_lookup[site_id][status] = site_equipment_lookup[site_id].get(status, 0) + item['count']
        
        for item in maintenance_by_site:
            site_id = item.get('equipment__location__parent_location_id') or item.get('equipment__location_id')
            if site_id:
                if site_id not in site_maintenance_lookup:
                    site_maintenance_lookup[site_id] = {}
                # Sum counts for the same status from different locations within the same site
                status = item['status']
                site_maintenance_lookup[site_id][status] = site_maintenance_lookup[site_id].get(status, 0) + item['count']
        
        for item in overdue_by_site:
            site_id = item.get('equipment__location__parent_location_id') or item.get('equipment__location_id')
            if site_id:
                # Sum counts from different locations within the same site
                site_overdue_lookup[site_id] = site_overdue_lookup.get(site_id, 0) + item['count']
        
        for item in upcoming_by_site:
            site_id = item.get('equipment__location__parent_location_id') or item.get('equipment__location_id')
            if site_id:
                # Sum counts from different locations within the same site
                site_upcoming_lookup[site_id] = site_upcoming_lookup.get(site_id, 0) + item['count']
        
        # Bulk fetch recent activities and events for ALL sites at once (avoid N+1 queries)
        all_site_ids = [site.id for site in all_sites]
        all_site_filters = Q(equipment__location__parent_location_id__in=all_site_ids) | Q(equipment__location_id__in=all_site_ids)
        
        # Get all recent activities for all sites, then group by site
        all_recent_activities = MaintenanceActivity.objects.filter(
            all_site_filters,
            actual_end__gte=today_dt - timedelta(days=30),
            status='completed'
        ).select_related('equipment', 'equipment__location', 'assigned_to').order_by('-actual_end')[:100]  # Limit total
        
        # Get all next events for all sites, then group by site
        all_next_events = CalendarEvent.objects.filter(
            all_site_filters,
            event_date__gte=today,
            is_completed=False
        ).select_related('equipment', 'equipment__location', 'assigned_to').order_by('event_date')[:100]  # Limit total
        
        # Group activities and events by site
        recent_activities_by_site = {site.id: [] for site in all_sites}
        next_events_by_site = {site.id: [] for site in all_sites}
        
        for activity in all_recent_activities:
            if activity.equipment and activity.equipment.location:
                site_id = activity.equipment.location.parent_location_id if activity.equipment.location.parent_location else activity.equipment.location_id
                if site_id in recent_activities_by_site and len(recent_activities_by_site[site_id]) < 3:
                    recent_activities_by_site[site_id].append(activity)
        
        for event in all_next_events:
            if event.equipment and event.equipment.location:
                site_id = event.equipment.location.parent_location_id if event.equipment.location.parent_location else event.equipment.location_id
                if site_id in next_events_by_site and len(next_events_by_site[site_id]) < 3:
                    next_events_by_site[site_id].append(event)
        
        # Bulk fetch calendar counts for all sites - use separate efficient queries
        calendar_counts_by_site = {site.id: {'total': 0, 'pending': 0, 'completed': 0} for site in all_sites}
        
        # Get total counts per site (single query)
        calendar_totals = CalendarEvent.objects.filter(
            all_site_filters
        ).values('equipment__location__parent_location_id', 'equipment__location_id').annotate(count=Count('id'))
        
        for item in calendar_totals:
            site_id = item.get('equipment__location__parent_location_id') or item.get('equipment__location_id')
            if site_id in calendar_counts_by_site:
                # Sum counts from different locations within the same site
                calendar_counts_by_site[site_id]['total'] = calendar_counts_by_site[site_id].get('total', 0) + item['count']
        
        # Get completed counts per site (single query)
        calendar_completed = CalendarEvent.objects.filter(
            all_site_filters,
            is_completed=True
        ).values('equipment__location__parent_location_id', 'equipment__location_id').annotate(count=Count('id'))
        
        for item in calendar_completed:
            site_id = item.get('equipment__location__parent_location_id') or item.get('equipment__location_id')
            if site_id in calendar_counts_by_site:
                # Sum counts from different locations within the same site
                calendar_counts_by_site[site_id]['completed'] = calendar_counts_by_site[site_id].get('completed', 0) + item['count']
        
        # Get pending counts per site (single query)
        calendar_pending = CalendarEvent.objects.filter(
            all_site_filters,
            is_completed=False,
            event_date__gte=today
        ).values('equipment__location__parent_location_id', 'equipment__location_id').annotate(count=Count('id'))
        
        for item in calendar_pending:
            site_id = item.get('equipment__location__parent_location_id') or item.get('equipment__location_id')
            if site_id in calendar_counts_by_site:
                # Sum counts from different locations within the same site
                calendar_counts_by_site[site_id]['pending'] = calendar_counts_by_site[site_id].get('pending', 0) + item['count']
        
        # Bulk fetch pod counts for all sites
        pod_counts = Location.objects.filter(
            parent_location_id__in=all_site_ids,
            is_active=True
        ).values('parent_location_id').annotate(count=Count('id'))
        pod_counts_dict = {item['parent_location_id']: item['count'] for item in pod_counts}
        
        for site in all_sites:
            # Get pre-computed data from lookups
            equipment_counts = site_equipment_lookup.get(site.id, {})
            maintenance_counts_dict = site_maintenance_lookup.get(site.id, {})
            
            # Get pre-computed calendar counts
            calendar_counts = calendar_counts_by_site.get(site.id, {'total': 0, 'pending': 0, 'completed': 0})
            
            # Calculate derived values
            total_equipment = sum(equipment_counts.values())
            active_equipment = equipment_counts.get('active', 0)
            equipment_in_maintenance = equipment_counts.get('maintenance', 0)
            inactive_equipment = equipment_counts.get('inactive', 0)
            
            pending_maintenance = maintenance_counts_dict.get('pending', 0)
            in_progress_maintenance = maintenance_counts_dict.get('in_progress', 0)
            
            # Get pre-computed counts
            overdue_maintenance = site_overdue_lookup.get(site.id, 0)
            upcoming_maintenance_count = site_upcoming_lookup.get(site.id, 0)
            
            # Get pre-fetched activities and events
            recent_activities = recent_activities_by_site.get(site.id, [])
            next_events = next_events_by_site.get(site.id, [])
            
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
            
            # Get pre-computed pod count
            pod_count = pod_counts_dict.get(site.id, 0)
            
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
    
    # Use aggregate queries for statistics - these are already filtered by site if applicable
    # Limit the querysets before aggregation to prevent expensive operations on huge datasets
    equipment_stats = equipment_query.values('status').annotate(count=Count('id'))
    equipment_counts = {item['status']: item['count'] for item in equipment_stats}
    
    maintenance_stats = maintenance_query.values('status').annotate(count=Count('id'))
    maintenance_counts = {item['status']: item['count'] for item in maintenance_stats}
    
    # For calendar stats, use a more efficient approach
    calendar_total = calendar_query.count()
    calendar_events_this_week = calendar_query.filter(
        event_date__gte=today,
        event_date__lt=today + timedelta(days=7)
    ).count()
    calendar_completed = calendar_query.filter(is_completed=True).count()
    calendar_pending = calendar_query.filter(is_completed=False, event_date__gte=today).count()
    
    calendar_stats = {
        'total': calendar_total,
        'events_this_week': calendar_events_this_week,
        'completed': calendar_completed,
        'pending': calendar_pending
    }
    
    # Calculate overdue maintenance - use exists() check first to avoid full count if possible
    overdue_count = maintenance_query.filter(
        scheduled_end__lt=timezone.now(),
        status__in=['pending', 'scheduled']
    ).count()
    
    # Calculate completed this month
    completed_this_month = maintenance_query.filter(
        status='completed',
        actual_end__gte=timezone.make_aware(_dt.combine(today.replace(day=1), _time.min))
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
    
    # Get status colors from BrandingSettings (moved from DashboardSettings for consistency)
    status_colors = {}
    try:
        from core.models import BrandingSettings
        branding = BrandingSettings.get_active()
        if branding:
            status_colors = {
                'scheduled': branding.status_color_scheduled,
                'pending': branding.status_color_pending,
                'in_progress': branding.status_color_in_progress,
                'cancelled': branding.status_color_cancelled,
                'completed': branding.status_color_completed,
                'overdue': branding.status_color_overdue,
            }
    except Exception:
        pass
    
    # Use defaults if no settings found
    if not status_colors:
        status_colors = {
            'scheduled': '#808080',  # Grey
            'pending': '#4299e1',    # Blue
            'in_progress': '#ed8936',  # Yellow
            'cancelled': '#000000',  # Black
            'completed': '#48bb78',  # Green
            'overdue': '#f56565',    # Red
        }
    
    # Build final context
    context = {
        'sites': sites,
        'selected_site': selected_site,
        'selected_site_id': selected_site_id,
        'is_all_sites': is_all_sites,
        'site_health': site_health,
        'site_stats': site_stats,
        'active_maintenance': active_maintenance,
        'active_calendar': active_calendar,
        'active_maintenance_by_site': active_maintenance_by_site,
        'active_maintenance_by_site_grouped': active_maintenance_by_site_grouped if group_active and is_all_sites else {},
        'active_calendar_by_site': active_calendar_by_site,
        'active_total_count': active_total_count,
        
        # Urgent and upcoming items
        'urgent_maintenance': urgent_maintenance,
        'urgent_calendar': urgent_calendar,
        'upcoming_maintenance': upcoming_maintenance,
        'upcoming_calendar': upcoming_calendar,
        
        # Grouped by site (if enabled)
        'urgent_maintenance_by_site': urgent_maintenance_by_site,
        'urgent_maintenance_by_site_grouped': urgent_maintenance_by_site_grouped if group_by_site and is_all_sites else {},
        'urgent_calendar_by_site': urgent_calendar_by_site,
        'upcoming_maintenance_by_site': upcoming_maintenance_by_site,
        'upcoming_maintenance_by_site_grouped': upcoming_maintenance_by_site_grouped if group_upcoming and is_all_sites else {},
        'upcoming_calendar_by_site': upcoming_calendar_by_site,
        
        # Total counts (for display)
        'urgent_total_count': urgent_total_count,
        'upcoming_total_count': upcoming_total_count,
        
        # Dashboard settings
        'dashboard_settings': dashboard_settings,
        
        # Status colors for overview page
        'status_colors': status_colors,
        
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
    
    # Convert QuerySets to lists for caching (QuerySets cannot be pickled)
    # Note: We can't cache the full context because it contains QuerySet objects
    # Instead, we'll cache only the expensive computed data
    # For now, disable caching of the full context to avoid serialization issues
    # The cache.get() above will still work for simple cases, but complex contexts won't cache
    
    # Cache key exists but we can't cache QuerySets, so we'll skip full context caching
    # Individual expensive queries could be cached separately if needed
    
    return render(request, 'core/dashboard.html', context)


@login_required
@user_passes_test(is_staff_or_superuser)
def dashboard_settings(request):
    """Dashboard/Overview page settings management view."""
    dashboard_settings_obj = DashboardSettings.get_active()
    
    if request.method == 'POST':
        form = DashboardSettingsForm(request.POST, instance=dashboard_settings_obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'Dashboard settings updated successfully!')
            # Invalidate dashboard cache to ensure changes take effect immediately
            from django.core.cache import cache
            cache.clear()  # Clear all cache to ensure dashboard updates
            return redirect('core:dashboard_settings')
    else:
        form = DashboardSettingsForm(instance=dashboard_settings_obj)
    
    context = {
        'form': form,
        'dashboard_settings': dashboard_settings_obj,
    }
    
    return render(request, 'core/dashboard_settings.html', context)


__all__ = ["dashboard", "dashboard_settings"]
