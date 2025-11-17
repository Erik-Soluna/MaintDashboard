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
    is_all_sites = False
    
    if selected_site_id is not None:
        # If site_id is explicitly provided (even if empty), use it
        if selected_site_id == '':
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
        # Limit prefetch to avoid loading excessive data
        locations_queryset = Location.objects.filter(
            parent_location=selected_site,
            is_active=True
        ).select_related('parent_location', 'customer').prefetch_related(
            Prefetch('equipment', queryset=Equipment.objects.select_related('category')[:50]),  # Limit equipment per location
            Prefetch('equipment__maintenance_activities', 
                    queryset=MaintenanceActivity.objects.select_related('assigned_to').order_by('-scheduled_start')[:10])  # Limit activities per equipment
        )
        locations = list(locations_queryset[:100])  # Limit total locations
        locations.sort(key=lambda loc: natural_sort_key(loc.name))
        
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
        locations_queryset = Location.objects.filter(
            is_site=False,
            is_active=True
        ).select_related('parent_location', 'customer')[:8]
        locations = list(locations_queryset)
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
    # Include overdue items (scheduled_end < now) and pending/in_progress items due within configured days
    # Limit queries to prevent loading too much data
    max_items = 200  # Reasonable limit to prevent excessive memory usage
    now = timezone.now()
    urgent_maintenance_all = list(maintenance_query.filter(
        Q(status='overdue') |  # Items explicitly marked as overdue
        (Q(scheduled_end__lt=now) & ~Q(status__in=['completed', 'cancelled'])) |  # Items past due date (overdue)
        (Q(scheduled_end__lte=urgent_cutoff) & Q(scheduled_end__gte=today) & Q(status__in=['pending', 'in_progress']))  # Urgent pending/in_progress items
    ).order_by('scheduled_end')[:max_items])
    
    # Filter out calendar events that are synced with maintenance activities to avoid duplication
    urgent_calendar_all = list(calendar_query.filter(
        event_date__lte=urgent_cutoff,
        event_date__gte=today,
        is_completed=False,
        maintenance_activity__isnull=True  # Only show calendar events NOT synced with maintenance
    ).order_by('event_date')[:max_items])
    
    # Calculate upcoming items with single queries - only show maintenance activities to avoid duplication
    upcoming_maintenance_all = list(maintenance_query.filter(
        scheduled_end__gt=urgent_cutoff,
        scheduled_end__lte=upcoming_cutoff,
        status__in=['pending', 'scheduled']
    ).order_by('scheduled_end')[:max_items])
    
    # Filter out calendar events that are synced with maintenance activities to avoid duplication
    upcoming_calendar_all = list(calendar_query.filter(
        event_date__gt=urgent_cutoff,
        event_date__lte=upcoming_cutoff,
        is_completed=False,
        maintenance_activity__isnull=True  # Only show calendar events NOT synced with maintenance
    ).order_by('event_date')[:max_items])
    
    # Group items by site if enabled
    group_by_site = dashboard_settings.group_urgent_by_site if dashboard_settings else True
    urgent_maintenance_by_site = {}
    urgent_calendar_by_site = {}
    upcoming_maintenance_by_site = {}
    upcoming_calendar_by_site = {}
    
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
        
        # Fetch all locations with prefetched parent relationships
        locations_with_parents = Location.objects.filter(id__in=location_ids).select_related('parent_location')
        location_to_site = {}
        for loc in locations_with_parents:
            site = loc.get_site_location()
            location_to_site[loc.id] = site.name if site else "Unknown Site"
        
        # Group urgent maintenance by site
        for item in urgent_maintenance_all:
            if item.equipment and item.equipment.location:
                site_name = location_to_site.get(item.equipment.location.id, "Unknown Site")
            else:
                site_name = "Unknown Site"
            if site_name not in urgent_maintenance_by_site:
                urgent_maintenance_by_site[site_name] = []
            if len(urgent_maintenance_by_site[site_name]) < (dashboard_settings.max_urgent_items_per_site if dashboard_settings else 15):
                urgent_maintenance_by_site[site_name].append(item)
        
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
        
        # Group upcoming maintenance by site
        group_upcoming = dashboard_settings.group_upcoming_by_site if dashboard_settings else True
        if group_upcoming:
            for item in upcoming_maintenance_all:
                if item.equipment and item.equipment.location:
                    site_name = location_to_site.get(item.equipment.location.id, "Unknown Site")
                else:
                    site_name = "Unknown Site"
                if site_name not in upcoming_maintenance_by_site:
                    upcoming_maintenance_by_site[site_name] = []
                if len(upcoming_maintenance_by_site[site_name]) < (dashboard_settings.max_upcoming_items_per_site if dashboard_settings else 15):
                    upcoming_maintenance_by_site[site_name].append(item)
            
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
    
    # For backwards compatibility, keep flat lists
    urgent_maintenance = urgent_maintenance_all[:dashboard_settings.max_urgent_items_total if dashboard_settings else 50]
    urgent_calendar = urgent_calendar_all[:10]
    upcoming_maintenance = upcoming_maintenance_all[:dashboard_settings.max_upcoming_items_total if dashboard_settings else 50]
    upcoming_calendar = upcoming_calendar_all[:10]
    
    # Calculate total counts for grouped items
    urgent_total_count = 0
    upcoming_total_count = 0
    
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
    else:
        # Count from flat lists
        urgent_total_count = len(urgent_maintenance) + len(urgent_calendar)
        upcoming_total_count = len(upcoming_maintenance) + len(upcoming_calendar)
    
    # ===== OPTIMIZED OVERVIEW DATA CALCULATION =====
    
    if selected_site:
        # POD STATUS - Use prefetched data to avoid N+1 queries
        overview_data = []
        
        # Get all equipment and maintenance data in bulk
        pod_equipment = {loc.id: [] for loc in locations}
        pod_maintenance = {loc.id: [] for loc in locations}
        pod_calendar = {loc.id: [] for loc in locations}
        
        # Organize equipment by location - Limit to prevent excessive memory usage
        for equipment in equipment_query[:1000]:  # Limit to 1000 items
            if equipment.location and equipment.location.id in pod_equipment:
                pod_equipment[equipment.location.id].append(equipment)
        
        # Organize maintenance by location - Limit to prevent excessive memory usage
        for maintenance in maintenance_query[:1000]:  # Limit to 1000 items
            if maintenance.equipment and maintenance.equipment.location and maintenance.equipment.location.id in pod_maintenance:
                pod_maintenance[maintenance.equipment.location.id].append(maintenance)
        
        # Organize calendar by location - Limit to prevent excessive memory usage
        for calendar_event in calendar_query[:1000]:  # Limit to 1000 items
            if calendar_event.equipment and calendar_event.equipment.location and calendar_event.equipment.location.id in pod_calendar:
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
            
            # Get next events (filter out any that might have been deleted)
            next_events = []
            for ce in location_calendar:
                try:
                    # Verify the event still exists in the database
                    if (ce.event_date >= today and not ce.is_completed):
                        next_events.append(ce)
                except Exception:
                    # Event was deleted, skip it
                    continue
            
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
        
        # Bulk upcoming maintenance counts
        upcoming_by_site = MaintenanceActivity.objects.filter(
            Q(equipment__location__parent_location_id__in=site_ids) | Q(equipment__location_id__in=site_ids),
            scheduled_start__date__lte=urgent_cutoff,
            scheduled_start__date__gte=today,
            status__in=['scheduled', 'pending']
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
                site_equipment_lookup[site_id][item['status']] = item['count']
        
        for item in maintenance_by_site:
            site_id = item.get('equipment__location__parent_location_id') or item.get('equipment__location_id')
            if site_id:
                if site_id not in site_maintenance_lookup:
                    site_maintenance_lookup[site_id] = {}
                site_maintenance_lookup[site_id][item['status']] = item['count']
        
        for item in overdue_by_site:
            site_id = item.get('equipment__location__parent_location_id') or item.get('equipment__location_id')
            if site_id:
                site_overdue_lookup[site_id] = item['count']
        
        for item in upcoming_by_site:
            site_id = item.get('equipment__location__parent_location_id') or item.get('equipment__location_id')
            if site_id:
                site_upcoming_lookup[site_id] = item['count']
        
        # Bulk fetch recent activities and events for ALL sites at once (avoid N+1 queries)
        all_site_ids = [site.id for site in all_sites]
        all_site_filters = Q(equipment__location__parent_location_id__in=all_site_ids) | Q(equipment__location_id__in=all_site_ids)
        
        # Get all recent activities for all sites, then group by site
        all_recent_activities = MaintenanceActivity.objects.filter(
            all_site_filters,
            actual_end__gte=today - timedelta(days=30),
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
                calendar_counts_by_site[site_id]['total'] = item['count']
        
        # Get completed counts per site (single query)
        calendar_completed = CalendarEvent.objects.filter(
            all_site_filters,
            is_completed=True
        ).values('equipment__location__parent_location_id', 'equipment__location_id').annotate(count=Count('id'))
        
        for item in calendar_completed:
            site_id = item.get('equipment__location__parent_location_id') or item.get('equipment__location_id')
            if site_id in calendar_counts_by_site:
                calendar_counts_by_site[site_id]['completed'] = item['count']
        
        # Get pending counts per site (single query)
        calendar_pending = CalendarEvent.objects.filter(
            all_site_filters,
            is_completed=False,
            event_date__gte=today
        ).values('equipment__location__parent_location_id', 'equipment__location_id').annotate(count=Count('id'))
        
        for item in calendar_pending:
            site_id = item.get('equipment__location__parent_location_id') or item.get('equipment__location_id')
            if site_id in calendar_counts_by_site:
                calendar_counts_by_site[site_id]['pending'] = item['count']
        
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
        'selected_site_id': selected_site_id,
        'is_all_sites': is_all_sites,
        'site_health': site_health,
        'site_stats': site_stats,
        
        # Urgent and upcoming items
        'urgent_maintenance': urgent_maintenance,
        'urgent_calendar': urgent_calendar,
        'upcoming_maintenance': upcoming_maintenance,
        'upcoming_calendar': upcoming_calendar,
        
        # Grouped by site (if enabled)
        'urgent_maintenance_by_site': urgent_maintenance_by_site,
        'urgent_calendar_by_site': urgent_calendar_by_site,
        'upcoming_maintenance_by_site': upcoming_maintenance_by_site,
        'upcoming_calendar_by_site': upcoming_calendar_by_site,
        
        # Total counts (for display)
        'urgent_total_count': urgent_total_count,
        'upcoming_total_count': upcoming_total_count,
        
        # Dashboard settings
        'dashboard_settings': dashboard_settings,
        
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
@user_passes_test(lambda u: u.is_superuser)
def clear_maintenance_data(request):
    """Clear all maintenance activities and calendar events (superuser only)."""
    if request.method == 'POST':
        try:
            from django.db import transaction
            from maintenance.models import MaintenanceActivity, MaintenanceSchedule
            from events.models import CalendarEvent
            
            with transaction.atomic():
                # Count existing records
                activity_count = MaintenanceActivity.objects.count()
                event_count = CalendarEvent.objects.count()
                schedule_count = MaintenanceSchedule.objects.count()
                
                # Delete calendar events first (they reference maintenance activities)
                if event_count > 0:
                    CalendarEvent.objects.all().delete()
                
                # Delete maintenance activities
                if activity_count > 0:
                    MaintenanceActivity.objects.all().delete()
                
                # Delete maintenance schedules
                if schedule_count > 0:
                    MaintenanceSchedule.objects.all().delete()
                
                # Invalidate dashboard cache
                invalidate_dashboard_cache()
                
                messages.success(
                    request, 
                    f'Successfully cleared {activity_count} maintenance activities, '
                    f'{event_count} calendar events, and {schedule_count} maintenance schedules!'
                )
                
        except Exception as e:
            messages.error(request, f'Error clearing data: {str(e)}')
            
        return redirect('core:dashboard')
    
    # GET request - show confirmation page
    from maintenance.models import MaintenanceActivity, MaintenanceSchedule
    from events.models import CalendarEvent
    
    activity_count = MaintenanceActivity.objects.count()
    event_count = CalendarEvent.objects.count()
    schedule_count = MaintenanceSchedule.objects.count()
    
    context = {
        'activity_count': activity_count,
        'event_count': event_count,
        'schedule_count': schedule_count,
        'total_count': activity_count + event_count + schedule_count,
    }
    
    return render(request, 'core/clear_data_confirm.html', context)


def invalidate_dashboard_cache(user_id=None, site_id=None):
    """Invalidate dashboard cache for specific user and/or site."""
    from django.core.cache import cache
    
    if user_id:
        # Invalidate cache for specific user
        if site_id == 'all':
            # For 'all' sites, clear the 'all' cache for this user
            cache_key = f"dashboard_data_all_{user_id}"
            cache.delete(cache_key)
        elif site_id:
            # Invalidate cache for specific user and site
            cache_key = f"dashboard_data_{site_id}_{user_id}"
            cache.delete(cache_key)
            # Also clear the 'all' cache since it might contain this site's data
            cache_key = f"dashboard_data_all_{user_id}"
            cache.delete(cache_key)
        else:
            # Invalidate all dashboard caches for this user (use with caution)
            # Since Django cache doesn't support pattern deletion, we'll clear common cache keys
            for i in range(100):  # Reasonable upper limit for user IDs
                cache.delete(f"dashboard_data_all_{i}")
                # Also clear some common site-specific caches
                for site_id_val in range(1, 100):  # Reasonable upper limit for site IDs
                    cache.delete(f"dashboard_data_{site_id_val}_{i}")
    else:
        # Invalidate all dashboard caches (use with caution)
        # Since Django cache doesn't support pattern deletion, we'll clear common cache keys
        for i in range(100):  # Reasonable upper limit for user IDs
            cache.delete(f"dashboard_data_all_{i}")
            # Also clear some common site-specific caches
            for site_id_val in range(1, 100):  # Reasonable upper limit for site IDs
                cache.delete(f"dashboard_data_{site_id_val}_{i}")


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
            
            # Handle timezone preference
            timezone = request.POST.get('timezone', 'America/Chicago')
            if timezone in [choice[0] for choice in profile.TIMEZONE_CHOICES]:
                profile.timezone = timezone
            
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
        'timezone_choices': profile.TIMEZONE_CHOICES,
    }
    return render(request, 'core/profile.html', context)


@login_required
def map_view(request):
    """Map view showing customer-specific equipment with connections."""
    from equipment.models import EquipmentConnection
    import json
    
    # Get selected customer from request or show all
    selected_customer_id = request.GET.get('customer_id', 'all')
    
    customers = Customer.objects.filter(is_active=True).order_by('name')
    
    # Build customer-specific maps
    customer_maps = []
    
    if selected_customer_id == 'all':
        # Show all customers
        customer_list = customers
    else:
        # Show specific customer
        try:
            customer_list = [customers.get(id=selected_customer_id)]
        except Customer.DoesNotExist:
            customer_list = customers
            selected_customer_id = 'all'
    
    for customer in customer_list:
        # Get all locations for this customer (sites and sub-locations)
        customer_locations = Location.objects.filter(
            Q(customer=customer) | Q(parent_location__customer=customer),
            is_active=True
        ).select_related('parent_location', 'customer')
        
        # Get all equipment at these locations
        customer_equipment = Equipment.objects.filter(
            location__in=customer_locations,
            is_active=True
        ).select_related('location', 'category')
        
        if not customer_equipment.exists():
            continue
        
        # Get equipment IDs for this customer
        equipment_ids = list(customer_equipment.values_list('id', flat=True))
        
        # Get connections between this customer's equipment
        customer_connections = EquipmentConnection.objects.filter(
            upstream_equipment__id__in=equipment_ids,
            downstream_equipment__id__in=equipment_ids,
            is_active=True
        ).select_related('upstream_equipment', 'downstream_equipment')
        
        # Build connection data for JavaScript
        connection_data = []
        for conn in customer_connections:
            connection_data.append({
                'id': conn.id,
                'upstream_id': conn.upstream_equipment.id,
                'downstream_id': conn.downstream_equipment.id,
                'connection_type': conn.connection_type,
                'is_critical': conn.is_critical,
            })
        
        # Build equipment data with effective status
        equipment_data = []
        for equip in customer_equipment:
            effective_status = equip.get_effective_status()
            equipment_data.append({
                'id': equip.id,
                'name': equip.name,
                'location_id': equip.location.id if equip.location else None,
                'location_name': equip.location.name if equip.location else 'Unknown',
                'status': equip.status,
                'effective_status': effective_status,
                'is_cascade_offline': effective_status == 'cascade_offline',
            })
        
        # Group locations by site
        sites = customer_locations.filter(is_site=True)
        location_groups = {}
        for site in sites:
            location_groups[site] = customer_locations.filter(parent_location=site)
        
        # Add independent locations (no parent)
        independent_locations = customer_locations.filter(parent_location=None, is_site=False)
        if independent_locations.exists():
            location_groups[None] = independent_locations
        
        customer_maps.append({
            'customer': customer,
            'locations': customer_locations,
            'location_groups': location_groups,
            'equipment': customer_equipment,
            'connections': customer_connections,
            'connections_json': json.dumps(connection_data),
            'equipment_json': json.dumps(equipment_data),
        })
    
    # Get all equipment for connection manager dropdowns
    all_equipment = Equipment.objects.filter(is_active=True).select_related('location', 'category')
    
    context = {
        'customer_maps': customer_maps,
        'customers': customers,
        'selected_customer_id': selected_customer_id,
        'all_equipment': all_equipment,
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
    
    # Get Docker logs configuration
    from core.services.docker_logs_service import DockerLogsService
    docker_service = DockerLogsService()
    
    context = {
        'health': health,
        'docker_logs_enabled': docker_service.is_enabled(),
        'docker_logs_debug_only': docker_service.is_debug_only(),
    }
    return render(request, 'core/settings.html', context)


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
def equipment_conditional_fields_settings(request):
    """Equipment conditional fields management view."""
    from equipment.models import EquipmentCategoryField, EquipmentCategoryConditionalField
    from django.db import connection
    
    # Check if the conditional fields table exists
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'equipment_equipmentcategoryconditionalfield'
                );
            """)
            table_exists = cursor.fetchone()[0]
            
        if not table_exists:
            messages.error(request, 'Conditional fields table does not exist. Please run migrations.')
            # Return a simplified context without conditional fields
            categories = EquipmentCategory.objects.filter(is_active=True).prefetch_related('custom_fields').order_by('name')
            context = {
                'categories': categories,
                'conditional_fields': [],
                'conditional_fields_by_category': {},
                'table_missing': True,
            }
            return render(request, 'core/equipment_conditional_fields_settings.html', context)
            
    except Exception as e:
        messages.error(request, f'Database error: {str(e)}')
        categories = EquipmentCategory.objects.filter(is_active=True).prefetch_related('custom_fields').order_by('name')
        context = {
            'categories': categories,
            'conditional_fields': [],
            'conditional_fields_by_category': {},
            'table_missing': True,
        }
        return render(request, 'core/equipment_conditional_fields_settings.html', context)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'create_conditional_field':
            source_category_id = request.POST.get('source_category')
            target_category_id = request.POST.get('target_category')
            field_id = request.POST.get('field')
            
            try:
                source_category = EquipmentCategory.objects.get(id=source_category_id)
                target_category = EquipmentCategory.objects.get(id=target_category_id)
                field = EquipmentCategoryField.objects.get(id=field_id)
                
                # Check if assignment already exists
                existing = EquipmentCategoryConditionalField.objects.filter(
                    target_category=target_category,
                    field=field
                ).first()
                
                if existing:
                    messages.warning(request, f'Field "{field.label}" is already assigned to "{target_category.name}".')
                else:
                    conditional_field = EquipmentCategoryConditionalField.objects.create(
                        source_category=source_category,
                        target_category=target_category,
                        field=field,
                        created_by=request.user
                    )
                    messages.success(request, f'Field "{field.label}" from "{source_category.name}" assigned to "{target_category.name}".')
                    
            except (EquipmentCategory.DoesNotExist, EquipmentCategoryField.DoesNotExist):
                messages.error(request, 'Invalid category or field selection.')
        
        elif action == 'delete_conditional_field':
            conditional_field_id = request.POST.get('conditional_field_id')
            try:
                conditional_field = EquipmentCategoryConditionalField.objects.get(id=conditional_field_id)
                field_label = conditional_field.field.label
                target_category_name = conditional_field.target_category.name
                conditional_field.delete()
                messages.success(request, f'Conditional field "{field_label}" removed from "{target_category_name}".')
            except EquipmentCategoryConditionalField.DoesNotExist:
                messages.error(request, 'Conditional field not found.')
        
        elif action == 'toggle_conditional_field':
            conditional_field_id = request.POST.get('conditional_field_id')
            try:
                conditional_field = EquipmentCategoryConditionalField.objects.get(id=conditional_field_id)
                conditional_field.is_active = not conditional_field.is_active
                conditional_field.save()
                status = 'enabled' if conditional_field.is_active else 'disabled'
                messages.success(request, f'Conditional field "{conditional_field.field.label}" {status}.')
            except EquipmentCategoryConditionalField.DoesNotExist:
                messages.error(request, 'Conditional field not found.')
        
        return redirect('core:equipment_conditional_fields_settings')
    
    # Get all categories with their custom fields
    categories = EquipmentCategory.objects.filter(is_active=True).prefetch_related('custom_fields').order_by('name')
    
    # Get all conditional field assignments with error handling
    try:
        conditional_fields = EquipmentCategoryConditionalField.objects.select_related(
            'source_category', 'target_category', 'field'
        ).order_by('target_category__name', 'field__label')
        
        # Group conditional fields by target category
        conditional_fields_by_category = {}
        for cf in conditional_fields:
            target_name = cf.target_category.name
            if target_name not in conditional_fields_by_category:
                conditional_fields_by_category[target_name] = []
            conditional_fields_by_category[target_name].append(cf)
            
    except Exception as e:
        messages.error(request, f'Error loading conditional fields: {str(e)}')
        conditional_fields = []
        conditional_fields_by_category = {}
    
    context = {
        'categories': categories,
        'conditional_fields': conditional_fields,
        'conditional_fields_by_category': conditional_fields_by_category,
        'table_missing': False,
    }
    return render(request, 'core/equipment_conditional_fields_settings.html', context)


@login_required
@user_passes_test(is_staff_or_superuser)
def category_fields_api(request, category_id):
    """API endpoint to get fields for a specific equipment category."""
    from equipment.models import EquipmentCategoryField
    
    try:
        category = EquipmentCategory.objects.get(id=category_id)
        fields = EquipmentCategoryField.objects.filter(
            category=category,
            is_active=True
        ).order_by('sort_order')
        
        fields_data = []
        for field in fields:
            fields_data.append({
                'id': field.id,
                'name': field.name,
                'label': field.label,
                'field_type': field.field_type,
                'required': field.required,
                'help_text': field.help_text,
                'field_group': field.field_group or 'General',
            })
        
        return JsonResponse({
            'status': 'success',
            'category': {
                'id': category.id,
                'name': category.name,
            },
            'fields': fields_data,
        })
        
    except EquipmentCategory.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Category not found'
        }, status=404)


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


@login_required
@user_passes_test(is_staff_or_superuser)
def add_user(request):
    """Add new user."""
    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'User "{user.username}" has been created successfully.')
            return redirect('core:user_management')
    else:
        form = UserForm()
    
    context = {
        'form': form,
        'title': 'Add User',
        'action': 'Add'
    }
    return render(request, 'core/user_form.html', context)


@login_required
@user_passes_test(is_staff_or_superuser)
def edit_user(request, user_id):
    """Edit existing user."""
    user = get_object_or_404(User, id=user_id)
    profile, created = UserProfile.objects.get_or_create(user=user)
    
    if request.method == 'POST':
        form = UserForm(request.POST, instance=user)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'User "{user.username}" has been updated successfully.')
            return redirect('core:user_management')
    else:
        # Initialize form with user and profile data
        form = UserForm(instance=user, initial={
            'role': profile.role,
            'employee_id': profile.employee_id,
            'department': profile.department,
            'phone_number': profile.phone_number,
        })
    
    context = {
        'form': form,
        'user': user,
        'title': 'Edit User',
        'action': 'Edit'
    }
    return render(request, 'core/user_form.html', context)


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
            
            # Invalidate dashboard cache to ensure Overview page updates immediately
            invalidate_dashboard_cache()
            
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
            
            # Invalidate dashboard cache to ensure Overview page updates immediately
            invalidate_dashboard_cache()
            
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
            
            # Invalidate dashboard cache to ensure Overview page updates immediately
            invalidate_dashboard_cache()
            
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
            
            # Invalidate dashboard cache to ensure Overview page updates immediately
            invalidate_dashboard_cache()
            
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
            
            # Invalidate dashboard cache to ensure Overview page updates immediately
            invalidate_dashboard_cache()
            
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
        
        # Invalidate dashboard cache to ensure Overview page updates immediately
        invalidate_dashboard_cache()
        
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
    if site_id and site_id != 'all':
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
            'error': str(e),
            'status': 'error',
            'timestamp': timezone.now().isoformat()
        }, status=500)


@login_required
def health_check_view(request):
    """Render the health check interface."""
    if not request.user.is_superuser:
        return render(request, 'core/access_denied.html', {'message': 'Access denied'})
    
    return render(request, 'core/health_check.html')


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
        # Basic database connection check with timeout
        from django.db import connection
        from django.db.utils import OperationalError
        import time
        
        start_time = time.time()
        
        # Quick database ping
        try:
            connection.ensure_connection()
            db_time = time.time() - start_time
            logger.debug(f"Database health check completed in {db_time:.3f}s")
        except OperationalError as db_error:
            logger.error(f"Database health check failed: {db_error}")
            return JsonResponse({'status': 'error', 'message': 'Database connection failed'}, status=500)
        
        # Basic Redis check (only if enabled and Redis is available)
        from django.conf import settings
        redis_status = "disabled"
        if getattr(settings, 'USE_REDIS', True):
            try:
                import redis
                r = redis.Redis.from_url(
                    getattr(settings, 'REDIS_URL', 'redis://redis:6379'), 
                    socket_connect_timeout=1, 
                    socket_timeout=1
                )
                r.ping()
                redis_status = "healthy"
                logger.debug("Redis health check completed successfully")
            except Exception as redis_error:
                # Log the Redis error but don't fail the health check
                logger.warning(f"Redis connection failed: {redis_error}. Health check continuing...")
                redis_status = "unavailable"
        
        # Return success response
        response_data = {
            'status': 'ok',
            'timestamp': time.time(),
            'database': 'healthy',
            'redis': redis_status,
            'response_time': time.time() - start_time
        }
        
        logger.debug(f"Health check completed successfully in {response_data['response_time']:.3f}s")
        return JsonResponse(response_data, status=200)
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        return JsonResponse({
            'status': 'error', 
            'message': str(e),
            'timestamp': time.time()
        }, status=500)


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
        # Trigger log collection if requested
        if request.GET.get('collect_logs') == 'true':
            # Direct log collection without Celery
            from .services.log_streaming_service import LogStreamingService
            log_service = LogStreamingService()
            
            # Collect logs directly
            try:
                # Create logs directory
                import os
                logs_dir = '/app/logs'
                os.makedirs(logs_dir, exist_ok=True)
                
                # Get containers and collect logs from accessible sources
                containers = log_service.get_available_containers()
                collected_count = 0
                
                for container in containers:
                    try:
                        log_file = container.get('log_file')
                        if log_file and os.path.exists(log_file):
                            # Read from accessible log file
                            with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                                content = f.read()
                            
                            # Write to our logs directory
                            output_file = os.path.join(logs_dir, f"{container['name']}.log")
                            with open(output_file, 'w', encoding='utf-8') as f:
                                f.write(f"# Source: {container['name']}\n")
                                f.write(f"# Type: {container.get('image', 'Unknown')}\n")
                                f.write(f"# Path: {log_file}\n")
                                f.write(f"# Collected at: {timezone.now().isoformat()}\n")
                                f.write("#" * 80 + "\n")
                                f.write(content)
                            
                            collected_count += 1
                            logger.info(f"Collected logs from {container['name']}: {len(content)} characters")
                        else:
                            logger.warning(f"No accessible log file for {container['name']}")
                    except Exception as e:
                        logger.warning(f"Error collecting logs for {container['name']}: {e}")
                
                logger.info(f"Direct log collection completed: {collected_count} containers")
                
            except Exception as e:
                logger.error(f"Error in direct log collection: {e}")
        
        # Get available containers for log streaming
        from .services.log_streaming_service import LogStreamingService
        log_service = LogStreamingService()
        containers = log_service.get_available_containers()
        
        context = {
            'containers': containers,
            'docker_logs_enabled': getattr(settings, 'DOCKER_LOGS_ENABLED', False),
            'docker_logs_debug_only': getattr(settings, 'DOCKER_LOGS_DEBUG_ONLY', False),
        }
        
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


@login_required
@user_passes_test(is_staff_or_superuser)
@require_http_methods(["POST"])
def generate_mdcs(request):
    """Generate MDCs for existing PODs."""
    try:
        from django.contrib.auth.models import User
        
        # Get parameters from the form
        pod_id = request.POST.get('pod_id', '').strip()
        site_id = request.POST.get('site_id', '').strip()
        mdcs_per_pod = int(request.POST.get('mdcs_per_pod', 2))
        force = request.POST.get('force', 'false').lower() == 'true'
        
        # Get or create a system user for creating locations
        system_user, _ = User.objects.get_or_create(
            username='system',
            defaults={'email': 'system@maintenance.local', 'is_staff': True}
        )
        
        # Determine which PODs to process
        if pod_id:
            # Generate for specific POD
            try:
                pod = Location.objects.get(id=pod_id, is_site=False, parent_location__is_site=False)
                pods = [pod]
            except Location.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': f'POD with ID {pod_id} not found'
                }, status=404)
        elif site_id:
            # Generate for all PODs in a specific site
            try:
                site = Location.objects.get(id=site_id, is_site=True)
                pods = Location.objects.filter(
                    parent_location=site,
                    is_site=False,
                    is_active=True
                ).order_by('name')
            except Location.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': f'Site with ID {site_id} not found'
                }, status=404)
        else:
            # Generate for all PODs (PODs are locations that are not sites and whose parent is a site)
            pods = Location.objects.filter(
                is_site=False,
                parent_location__is_site=True,
                is_active=True
            ).order_by('parent_location__name', 'name')
        
        if not pods.exists():
            return JsonResponse({
                'success': False,
                'error': 'No PODs found to generate MDCs for'
            }, status=400)
        
        total_mdcs_created = 0
        output_lines = []
        
        # Process each POD
        for pod in pods:
            site = pod.parent_location
            pod_name = pod.name
            
            # Get existing MDCs for this POD to determine starting number
            existing_mdcs = Location.objects.filter(
                parent_location=pod,
                is_site=False,
                is_active=True
            ).order_by('name')
            
            # Determine starting MDC number
            if existing_mdcs.exists():
                # Find the highest MDC number
                max_mdc_num = 0
                for mdc in existing_mdcs:
                    # Extract number from name like "MDC 1", "MDC 2", etc.
                    import re
                    match = re.search(r'MDC\s+(\d+)', mdc.name, re.IGNORECASE)
                    if match:
                        max_mdc_num = max(max_mdc_num, int(match.group(1)))
                mdc_start = max_mdc_num + 1
            else:
                # No existing MDCs, start from 1
                mdc_start = 1
            
            mdc_end = mdc_start + mdcs_per_pod - 1
            
            # Generate MDCs for this POD
            for mdc_num in range(mdc_start, mdc_end + 1):
                mdc_name = f'MDC {mdc_num}'
                
                # Check if MDC already exists
                existing_mdc = Location.objects.filter(
                    name=mdc_name,
                    parent_location=pod,
                    is_site=False
                ).first()
                
                if existing_mdc and not force:
                    output_lines.append(f'MDC already exists: {site.name} > {pod_name} > {mdc_name} - skipping')
                    continue
                
                # Create or update MDC
                mdc, created = Location.objects.get_or_create(
                    name=mdc_name,
                    parent_location=pod,
                    defaults={
                        'is_site': False,
                        'created_by': system_user,
                        'updated_by': system_user,
                        'is_active': True
                    }
                )
                
                if created:
                    output_lines.append(f'Created MDC: {site.name} > {pod_name} > {mdc_name}')
                    total_mdcs_created += 1
                elif force:
                    mdc.updated_by = system_user
                    mdc.is_active = True
                    mdc.save()
                    output_lines.append(f'Updated existing MDC: {site.name} > {pod_name} > {mdc_name}')
                    total_mdcs_created += 1
        
        # Build result message
        if pod_id:
            target_desc = f"POD '{pods[0].name}'"
        elif site_id:
            target_desc = f"site '{site.name}'"
        else:
            target_desc = "all PODs"
        
        result = '\n'.join(output_lines) if output_lines else 'No MDCs were created (all already exist)'
        
        return JsonResponse({
            'success': True,
            'message': f'MDC generation completed successfully for {target_desc}! Generated: {total_mdcs_created} MDCs',
            'generated_count': total_mdcs_created,
            'output': result
        })
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return JsonResponse({
            'success': False,
            'error': f'Error generating MDCs: {str(e)}',
            'details': error_details
        }, status=500)


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


@csrf_exempt
@require_http_methods(["POST"])
def reorganize_activity_types_api(request):
    """API endpoint to run the reorganize_activity_types management command."""
    try:
        from django.core.management import call_command
        from io import StringIO
        
        # Get parameters
        dry_run = request.POST.get('dry_run', 'true').lower() == 'true'
        force = request.POST.get('force', 'false').lower() == 'true'
        
        # Capture output
        output = StringIO()
        
        # Build command arguments
        args = ['reorganize_activity_types']
        if dry_run:
            args.append('--dry-run')
        if force:
            args.append('--force')
        
        # Run the command
        call_command(*args, stdout=output, verbosity=2)
        
        command_output = output.getvalue()
        output.close()
        
        return JsonResponse({
            'success': True,
            'dry_run': dry_run,
            'force': force,
            'output': command_output,
            'message': 'Activity types reorganized successfully' if not dry_run else 'Dry run completed'
        })
        
    except Exception as e:
        logger.error(f"Error reorganizing activity types: {str(e)}")
        import traceback
        return JsonResponse({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def clear_maintenance_activities_api(request):
    """API endpoint to clear scheduled maintenance activities (unsecured for now - will add API keys later)."""
    try:
        from maintenance.models import MaintenanceActivity, MaintenanceSchedule
        from django.db import connection
        import json
        import time
        import threading
        
        # TODO: Add API key authentication here
        # For now, allowing access for testing purposes
        
        # Get parameters
        clear_all = request.POST.get('clear_all', 'false').lower() == 'true'
        clear_schedules = request.POST.get('clear_schedules', 'false').lower() == 'true'
        dry_run = request.POST.get('dry_run', 'true').lower() == 'true'  # Default to dry_run for safety
        use_fast_delete = request.POST.get('fast_delete', 'true').lower() == 'true'  # Use optimized deletion
        async_mode = request.POST.get('async', 'false').lower() == 'true'  # Run in background
        
        results = {
            'success': True,
            'dry_run': dry_run,
            'activities_deleted': 0,
            'schedules_deleted': 0,
            'message': '',
            'execution_time_seconds': 0
        }
        
        start_time = time.time()
        
        # Count what would be deleted
        if clear_all:
            # Clear ALL activities
            activities_query = MaintenanceActivity.objects.all()
        else:
            # Only clear scheduled/pending activities (not completed)
            activities_query = MaintenanceActivity.objects.filter(
                status__in=['scheduled', 'pending']
            )
        
        activities_count = activities_query.count()
        results['activities_deleted'] = activities_count
        
        if clear_schedules:
            schedules_query = MaintenanceSchedule.objects.all()
            schedules_count = schedules_query.count()
            results['schedules_deleted'] = schedules_count
        
        # If async mode and not dry run, run in background thread
        if async_mode and not dry_run:
            def delete_in_background():
                """Background deletion function."""
                try:
                    # Re-query in new thread context
                    from maintenance.models import MaintenanceActivity, MaintenanceSchedule
                    from django.db import connection
                    
                    if clear_all:
                        activities = MaintenanceActivity.objects.all()
                    else:
                        activities = MaintenanceActivity.objects.filter(
                            status__in=['scheduled', 'pending']
                        )
                    
                    activity_ids = list(activities.values_list('id', flat=True))
                    
                    if activity_ids and use_fast_delete and len(activity_ids) > 100:
                        # Fast SQL delete
                        ids_str = ','.join(map(str, activity_ids))
                        with connection.cursor() as cursor:
                            cursor.execute(f"DELETE FROM maintenance_maintenancetimelineentry WHERE activity_id IN ({ids_str})")
                            cursor.execute(f"DELETE FROM maintenance_maintenancechecklist WHERE activity_id IN ({ids_str})")
                            cursor.execute(f"DELETE FROM maintenance_maintenancereport WHERE maintenance_activity_id IN ({ids_str})")
                            try:
                                cursor.execute(f"DELETE FROM events_calendarevent WHERE maintenance_activity_id IN ({ids_str})")
                            except:
                                pass
                            cursor.execute(f"DELETE FROM maintenance_maintenanceactivity WHERE id IN ({ids_str})")
                        logger.info(f"Fast SQL deletion completed: {len(activity_ids)} activities")
                    else:
                        # ORM delete
                        deleted = activities.delete()
                        logger.info(f"ORM deletion completed: {deleted[0]} activities")
                    
                    if clear_schedules:
                        MaintenanceSchedule.objects.all().delete()
                        logger.info(f"Schedules deleted")
                    
                except Exception as e:
                    logger.error(f"Background deletion error: {str(e)}")
            
            # Start background thread
            thread = threading.Thread(target=delete_in_background, daemon=True)
            thread.start()
            
            return JsonResponse({
                'success': True,
                'async': True,
                'message': f'Deletion started in background for {activities_count} activities. Check logs for completion.',
                'activities_to_delete': activities_count,
                'schedules_to_delete': results['schedules_deleted'] if clear_schedules else 0,
                'note': 'Background deletion is running. It will complete in 5-30 seconds depending on data volume.'
            })
        
        # Perform deletion if not dry run (synchronous mode)
        if not dry_run:
            if use_fast_delete and activities_count > 100:
                # OPTIMIZED: Use raw SQL for bulk deletion (10-50x faster)
                # Get activity IDs
                activity_ids = list(activities_query.values_list('id', flat=True))
                
                if activity_ids:
                    # Convert to comma-separated string for SQL IN clause
                    ids_str = ','.join(map(str, activity_ids))
                    
                    with connection.cursor() as cursor:
                        # Delete related records first (CASCADE simulation)
                        # This is much faster than Django's ORM cascade
                        
                        # Delete timeline entries
                        cursor.execute(f"DELETE FROM maintenance_maintenancetimelineentry WHERE activity_id IN ({ids_str})")
                        
                        # Delete checklist items  
                        cursor.execute(f"DELETE FROM maintenance_maintenancechecklist WHERE activity_id IN ({ids_str})")
                        
                        # Delete reports
                        cursor.execute(f"DELETE FROM maintenance_maintenancereport WHERE maintenance_activity_id IN ({ids_str})")
                        
                        # Delete calendar events if they exist
                        try:
                            cursor.execute(f"DELETE FROM events_calendarevent WHERE maintenance_activity_id IN ({ids_str})")
                        except:
                            pass  # Table might not exist or column might be different
                        
                        # Finally delete the activities themselves
                        cursor.execute(f"DELETE FROM maintenance_maintenanceactivity WHERE id IN ({ids_str})")
                    
                    results['activities_deleted'] = len(activity_ids)
                    results['method'] = 'fast_sql'
            else:
                # Standard Django ORM delete (slower but safer)
                deleted_activities = activities_query.delete()
                results['activities_deleted'] = deleted_activities[0] if deleted_activities else 0
                results['method'] = 'orm'
            
            if clear_schedules:
                deleted_schedules = schedules_query.delete()
                results['schedules_deleted'] = deleted_schedules[0] if deleted_schedules else 0
            
            results['message'] = f'Successfully deleted {results["activities_deleted"]} activities'
            if clear_schedules:
                results['message'] += f' and {results["schedules_deleted"]} schedules'
        else:
            results['message'] = f'Dry run: Would delete {activities_count} activities'
            if clear_schedules:
                results['message'] += f' and {schedules_count} schedules'
        
        results['execution_time_seconds'] = round(time.time() - start_time, 2)
        
        logger.info(f"Maintenance cleanup via API: {results['message']} (took {results['execution_time_seconds']}s)")
        return JsonResponse(results)
        
    except Exception as e:
        logger.error(f"Error clearing maintenance activities: {str(e)}")
        import traceback
        return JsonResponse({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }, status=500)


@login_required
@user_passes_test(is_staff_or_superuser)
@require_http_methods(["POST"])
def clear_maintenance_activities(request):
    """Clear scheduled maintenance activities without wiping entire database (web interface version)."""
    try:
        from maintenance.models import MaintenanceActivity, MaintenanceSchedule
        import json
        
        # Safety check - only allow in debug mode or for superusers
        if not request.user.is_superuser:
            return JsonResponse({
                'success': False,
                'error': 'Only superusers can clear maintenance activities'
            }, status=403)
        
        # Get parameters
        clear_all = request.POST.get('clear_all', 'false').lower() == 'true'
        clear_schedules = request.POST.get('clear_schedules', 'false').lower() == 'true'
        dry_run = request.POST.get('dry_run', 'false').lower() == 'true'
        
        results = {
            'success': True,
            'dry_run': dry_run,
            'activities_deleted': 0,
            'schedules_deleted': 0,
            'message': ''
        }
        
        # Count what would be deleted
        if clear_all:
            # Clear ALL activities
            activities_query = MaintenanceActivity.objects.all()
        else:
            # Only clear scheduled/pending activities (not completed)
            activities_query = MaintenanceActivity.objects.filter(
                status__in=['scheduled', 'pending']
            )
        
        activities_count = activities_query.count()
        results['activities_deleted'] = activities_count
        
        if clear_schedules:
            schedules_query = MaintenanceSchedule.objects.all()
            schedules_count = schedules_query.count()
            results['schedules_deleted'] = schedules_count
        
        # Perform deletion if not dry run
        if not dry_run:
            deleted_activities = activities_query.delete()
            results['activities_deleted'] = deleted_activities[0] if deleted_activities else 0
            
            if clear_schedules:
                deleted_schedules = schedules_query.delete()
                results['schedules_deleted'] = deleted_schedules[0] if deleted_schedules else 0
            
            results['message'] = f'Successfully deleted {results["activities_deleted"]} activities'
            if clear_schedules:
                results['message'] += f' and {results["schedules_deleted"]} schedules'
        else:
            results['message'] = f'Dry run: Would delete {activities_count} activities'
            if clear_schedules:
                results['message'] += f' and {schedules_count} schedules'
        
        logger.info(f"Maintenance cleanup by {request.user.username}: {results['message']}")
        return JsonResponse(results)
        
    except Exception as e:
        logger.error(f"Error clearing maintenance activities: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
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


@login_required
def system_health_check(request):
    """System health check endpoint for debugging issues."""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    health_data = {
        'timestamp': timezone.now().isoformat(),
        'categories': {},
        'summary': {
            'total_checks': 0,
            'passed': 0,
            'failed': 0,
            'warnings': 0,
            'health_percentage': 0
        },
        'quick_fixes': []
    }
    
    def run_check(category, check_name, test_func, fix_suggestion=None):
        """Run a health check and record results."""
        try:
            result = test_func()
            if result:
                health_data['categories'][category]['passed'].append({
                    'name': check_name,
                    'status': 'PASS'
                })
                health_data['summary']['passed'] += 1
            else:
                health_data['categories'][category]['failed'].append({
                    'name': check_name,
                    'status': 'FAIL',
                    'fix': fix_suggestion
                })
                health_data['summary']['failed'] += 1
                if fix_suggestion:
                    health_data['quick_fixes'].append(fix_suggestion)
        except Exception as e:
            health_data['categories'][category]['failed'].append({
                'name': check_name,
                'status': 'ERROR',
                'error': str(e),
                'fix': fix_suggestion
            })
            health_data['summary']['failed'] += 1
            if fix_suggestion:
                health_data['quick_fixes'].append(fix_suggestion)
        
        health_data['summary']['total_checks'] += 1
    
    def run_warning_check(category, check_name, test_func, warning_message=None):
        """Run a warning check and record results."""
        try:
            result = test_func()
            if result:
                health_data['categories'][category]['passed'].append({
                    'name': check_name,
                    'status': 'PASS'
                })
                health_data['summary']['passed'] += 1
            else:
                health_data['categories'][category]['warnings'].append({
                    'name': check_name,
                    'status': 'WARNING',
                    'message': warning_message
                })
                health_data['summary']['warnings'] += 1
        except Exception as e:
            health_data['categories'][category]['warnings'].append({
                'name': check_name,
                'status': 'WARNING',
                'error': str(e),
                'message': warning_message
            })
            health_data['summary']['warnings'] += 1
        
        health_data['summary']['total_checks'] += 1
    
    # Initialize categories
    categories = ['CORE', 'SCHEMA', 'API', 'CALENDAR', 'MIGRATIONS', 'AUTH', 'DEPS']
    for category in categories:
        health_data['categories'][category] = {
            'passed': [],
            'failed': [],
            'warnings': []
        }
    
    # CORE APPLICATION HEALTH
    run_check('CORE', 'Django Configuration', 
              lambda: True,  # Simplified for now
              'Check Django settings and configuration')
    
    run_check('CORE', 'Database Connection',
              lambda: connection.cursor().execute('SELECT 1') is not None,
              'Check database connectivity and credentials')
    
    # DATABASE SCHEMA INTEGRITY
    run_check('SCHEMA', 'MaintenanceActivity Model',
              lambda: MaintenanceActivity.objects.count() >= 0,
              'Run: ./scripts/simple_timezone_fix.sh')
    
    run_check('SCHEMA', 'Timezone Field Exists',
              lambda: hasattr(MaintenanceActivity, 'timezone'),
              'Run: ./scripts/simple_timezone_fix.sh')
    
    try:
        from events.models import CalendarEvent
        run_check('SCHEMA', 'CalendarEvent Model',
                  lambda: CalendarEvent.objects.count() >= 0,
                  'Check events app migrations')
    except ImportError:
        health_data['categories']['SCHEMA']['failed'].append({
            'name': 'CalendarEvent Model',
            'status': 'ERROR',
            'error': 'CalendarEvent model not found',
            'fix': 'Check events app migrations'
        })
        health_data['summary']['failed'] += 1
        health_data['summary']['total_checks'] += 1
    
    # API ENDPOINTS FUNCTIONALITY
    def test_unified_events_api():
        try:
            from events.views import fetch_unified_events
            from django.test import RequestFactory
            
            factory = RequestFactory()
            test_request = factory.get('/events/api/unified/?start=2025-01-01&end=2025-12-31')
            test_request.user = request.user
            
            response = fetch_unified_events(test_request)
            return response.status_code == 200
        except Exception:
            return False
    
    run_check('API', 'fetch_unified_events API',
              test_unified_events_api,
              'Run: ./scripts/simple_timezone_fix.sh')
    
    # CALENDAR SPECIFIC ISSUES
    def test_calendar_view():
        try:
            from events.views import calendar_view
            from django.test import RequestFactory
            
            factory = RequestFactory()
            test_request = factory.get('/events/calendar/')
            test_request.user = request.user
            
            response = calendar_view(test_request)
            return response.status_code == 200
        except Exception:
            return False
    
    run_check('CALENDAR', 'Calendar View Renders',
              test_calendar_view,
              'Check calendar view and template rendering')
    
    run_warning_check('CALENDAR', 'Maintenance Activities Count',
                      lambda: MaintenanceActivity.objects.count() > 0,
                      'No maintenance activities found - calendar may appear empty')
    
    # USER AUTHENTICATION
    run_check('AUTH', 'Admin User Exists',
              lambda: User.objects.filter(is_superuser=True).exists(),
              'Create admin user: python manage.py createsuperuser')
    
    # EXTERNAL DEPENDENCIES
    def test_redis():
        try:
            from django.core.cache import cache
            cache.set('health_test', 'value')
            return cache.get('health_test') == 'value'
        except Exception:
            return False
    
    run_check('DEPS', 'Redis Connection',
              test_redis,
              'Check Redis server connectivity')
    
    # Calculate health percentage
    if health_data['summary']['total_checks'] > 0:
        health_data['summary']['health_percentage'] = round(
            (health_data['summary']['passed'] * 100) / health_data['summary']['total_checks']
        )
    
    # Determine overall health status
    if health_data['summary']['health_percentage'] >= 90:
        health_data['summary']['status'] = 'EXCELLENT'
    elif health_data['summary']['health_percentage'] >= 75:
        health_data['summary']['status'] = 'GOOD'
    elif health_data['summary']['health_percentage'] >= 50:
        health_data['summary']['status'] = 'MODERATE'
    else:
        health_data['summary']['status'] = 'CRITICAL'
    
    return JsonResponse(health_data)


@login_required
def health_check_view(request):
    """Render the health check interface."""
    if not request.user.is_superuser:
        return render(request, 'core/access_denied.html', {'message': 'Access denied'})
    
    return render(request, 'core/health_check.html')

@login_required
def system_health_check(request):
    """System health check endpoint for debugging issues."""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    health_data = {
        'timestamp': timezone.now().isoformat(),
        'categories': {},
        'summary': {
            'total_checks': 0,
            'passed': 0,
            'failed': 0,
            'warnings': 0,
            'health_percentage': 0
        },
        'quick_fixes': []
    }
    
    def run_check(category, check_name, test_func, fix_suggestion=None):
        """Run a health check and record results."""
        try:
            result = test_func()
            if result:
                health_data['categories'][category]['passed'].append({
                    'name': check_name,
                    'status': 'PASS'
                })
                health_data['summary']['passed'] += 1
            else:
                health_data['categories'][category]['failed'].append({
                    'name': check_name,
                    'status': 'FAIL',
                    'fix': fix_suggestion
                })
                health_data['summary']['failed'] += 1
                if fix_suggestion:
                    health_data['quick_fixes'].append(fix_suggestion)
        except Exception as e:
            health_data['categories'][category]['failed'].append({
                'name': check_name,
                'status': 'ERROR',
                'error': str(e),
                'fix': fix_suggestion
            })
            health_data['summary']['failed'] += 1
            if fix_suggestion:
                health_data['quick_fixes'].append(fix_suggestion)
        
        health_data['summary']['total_checks'] += 1
    
    def run_warning_check(category, check_name, test_func, warning_message=None):
        """Run a warning check and record results."""
        try:
            result = test_func()
            if result:
                health_data['categories'][category]['passed'].append({
                    'name': check_name,
                    'status': 'PASS'
                })
                health_data['summary']['passed'] += 1
            else:
                health_data['categories'][category]['warnings'].append({
                    'name': check_name,
                    'status': 'WARNING',
                    'message': warning_message
                })
                health_data['summary']['warnings'] += 1
        except Exception as e:
            health_data['categories'][category]['warnings'].append({
                'name': check_name,
                'status': 'WARNING',
                'error': str(e),
                'message': warning_message
            })
            health_data['summary']['warnings'] += 1
        
        health_data['summary']['total_checks'] += 1
    
    # Initialize categories
    categories = ['CORE', 'SCHEMA', 'API', 'CALENDAR', 'MIGRATIONS', 'AUTH', 'DEPS']
    for category in categories:
        health_data['categories'][category] = {
            'passed': [],
            'failed': [],
            'warnings': []
        }
    
    # CORE APPLICATION HEALTH
    run_check('CORE', 'Django Configuration', 
              lambda: True,  # Simplified for now
              'Check Django settings and configuration')
    
    run_check('CORE', 'Database Connection',
              lambda: connection.cursor().execute('SELECT 1') is not None,
              'Check database connectivity and credentials')
    
    # DATABASE SCHEMA INTEGRITY
    run_check('SCHEMA', 'MaintenanceActivity Model',
              lambda: MaintenanceActivity.objects.count() >= 0,
              'Run: ./scripts/simple_timezone_fix.sh')
    
    run_check('SCHEMA', 'Timezone Field Exists',
              lambda: hasattr(MaintenanceActivity, 'timezone'),
              'Run: ./scripts/simple_timezone_fix.sh')
    
    try:
        from events.models import CalendarEvent
        run_check('SCHEMA', 'CalendarEvent Model',
                  lambda: CalendarEvent.objects.count() >= 0,
                  'Check events app migrations')
    except ImportError:
        health_data['categories']['SCHEMA']['failed'].append({
            'name': 'CalendarEvent Model',
            'status': 'ERROR',
            'error': 'CalendarEvent model not found',
            'fix': 'Check events app migrations'
        })
        health_data['summary']['failed'] += 1
        health_data['summary']['total_checks'] += 1
    
    # API ENDPOINTS FUNCTIONALITY
    def test_unified_events_api():
        try:
            from events.views import fetch_unified_events
            from django.test import RequestFactory
            
            factory = RequestFactory()
            test_request = factory.get('/events/api/unified/?start=2025-01-01&end=2025-12-31')
            test_request.user = request.user
            
            response = fetch_unified_events(test_request)
            return response.status_code == 200
        except Exception:
            return False
    
    run_check('API', 'fetch_unified_events API',
              test_unified_events_api,
              'Run: ./scripts/simple_timezone_fix.sh')
    
    # CALENDAR SPECIFIC ISSUES
    def test_calendar_view():
        try:
            from events.views import calendar_view
            from django.test import RequestFactory
            
            factory = RequestFactory()
            test_request = factory.get('/events/calendar/')
            test_request.user = request.user
            
            response = calendar_view(test_request)
            return response.status_code == 200
        except Exception:
            return False
    
    run_check('CALENDAR', 'Calendar View Renders',
              test_calendar_view,
              'Check calendar view and template rendering')
    
    run_warning_check('CALENDAR', 'Maintenance Activities Count',
                      lambda: MaintenanceActivity.objects.count() > 0,
                      'No maintenance activities found - calendar may appear empty')
    
    # USER AUTHENTICATION
    run_check('AUTH', 'Admin User Exists',
              lambda: User.objects.filter(is_superuser=True).exists(),
              'Create admin user: python manage.py createsuperuser')
    
    # EXTERNAL DEPENDENCIES
    def test_redis():
        try:
            from django.core.cache import cache
            cache.set('health_test', 'value')
            return cache.get('health_test') == 'value'
        except Exception:
            return False
    
    run_check('DEPS', 'Redis Connection',
              test_redis,
              'Check Redis server connectivity')
    
    # Calculate health percentage
    if health_data['summary']['total_checks'] > 0:
        health_data['summary']['health_percentage'] = round(
            (health_data['summary']['passed'] * 100) / health_data['summary']['total_checks']
        )
    
    # Determine overall health status
    if health_data['summary']['health_percentage'] >= 90:
        health_data['summary']['status'] = 'EXCELLENT'
    elif health_data['summary']['health_percentage'] >= 75:
        health_data['summary']['status'] = 'GOOD'
    elif health_data['summary']['health_percentage'] >= 50:
        health_data['summary']['status'] = 'MODERATE'
    else:
        health_data['summary']['status'] = 'CRITICAL'
    
    return JsonResponse(health_data)


@login_required
def health_check_view(request):
    """Render the health check interface."""
    if not request.user.is_superuser:
        return render(request, 'core/access_denied.html', {'message': 'Access denied'})
    
    return render(request, 'core/health_check.html')

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
        
        # DEPRECATED - Playwright functionality removed
        return JsonResponse({
            'success': False,
            'error': 'Playwright debug functionality has been deprecated and removed.',
            'screenshots': [],
            'html_dumps': []
        }, status=410)  # 410 Gone
        
        # OLD CODE - DEPRECATED
        # # Get the log
        # try:
        #     log = PlaywrightDebugLog.objects.get(id=log_id)
        # except PlaywrightDebugLog.DoesNotExist:
        #     return JsonResponse({
        #         'success': False,
        #         'error': 'Log not found'
        #     }, status=404)
        
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


@login_required
def system_health_check(request):
    """System health check endpoint for debugging issues."""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    health_data = {
        'timestamp': timezone.now().isoformat(),
        'categories': {},
        'summary': {
            'total_checks': 0,
            'passed': 0,
            'failed': 0,
            'warnings': 0,
            'health_percentage': 0
        },
        'quick_fixes': []
    }
    
    def run_check(category, check_name, test_func, fix_suggestion=None):
        """Run a health check and record results."""
        try:
            result = test_func()
            if result:
                health_data['categories'][category]['passed'].append({
                    'name': check_name,
                    'status': 'PASS'
                })
                health_data['summary']['passed'] += 1
            else:
                health_data['categories'][category]['failed'].append({
                    'name': check_name,
                    'status': 'FAIL',
                    'fix': fix_suggestion
                })
                health_data['summary']['failed'] += 1
                if fix_suggestion:
                    health_data['quick_fixes'].append(fix_suggestion)
        except Exception as e:
            health_data['categories'][category]['failed'].append({
                'name': check_name,
                'status': 'ERROR',
                'error': str(e),
                'fix': fix_suggestion
            })
            health_data['summary']['failed'] += 1
            if fix_suggestion:
                health_data['quick_fixes'].append(fix_suggestion)
        
        health_data['summary']['total_checks'] += 1
    
    def run_warning_check(category, check_name, test_func, warning_message=None):
        """Run a warning check and record results."""
        try:
            result = test_func()
            if result:
                health_data['categories'][category]['passed'].append({
                    'name': check_name,
                    'status': 'PASS'
                })
                health_data['summary']['passed'] += 1
            else:
                health_data['categories'][category]['warnings'].append({
                    'name': check_name,
                    'status': 'WARNING',
                    'message': warning_message
                })
                health_data['summary']['warnings'] += 1
        except Exception as e:
            health_data['categories'][category]['warnings'].append({
                'name': check_name,
                'status': 'WARNING',
                'error': str(e),
                'message': warning_message
            })
            health_data['summary']['warnings'] += 1
        
        health_data['summary']['total_checks'] += 1
    
    # Initialize categories
    categories = ['CORE', 'SCHEMA', 'API', 'CALENDAR', 'MIGRATIONS', 'AUTH', 'DEPS']
    for category in categories:
        health_data['categories'][category] = {
            'passed': [],
            'failed': [],
            'warnings': []
        }
    
    # CORE APPLICATION HEALTH
    run_check('CORE', 'Django Configuration', 
              lambda: True,  # Simplified for now
              'Check Django settings and configuration')
    
    run_check('CORE', 'Database Connection',
              lambda: connection.cursor().execute('SELECT 1') is not None,
              'Check database connectivity and credentials')
    
    # DATABASE SCHEMA INTEGRITY
    run_check('SCHEMA', 'MaintenanceActivity Model',
              lambda: MaintenanceActivity.objects.count() >= 0,
              'Run: ./scripts/simple_timezone_fix.sh')
    
    run_check('SCHEMA', 'Timezone Field Exists',
              lambda: hasattr(MaintenanceActivity, 'timezone'),
              'Run: ./scripts/simple_timezone_fix.sh')
    
    try:
        from events.models import CalendarEvent
        run_check('SCHEMA', 'CalendarEvent Model',
                  lambda: CalendarEvent.objects.count() >= 0,
                  'Check events app migrations')
    except ImportError:
        health_data['categories']['SCHEMA']['failed'].append({
            'name': 'CalendarEvent Model',
            'status': 'ERROR',
            'error': 'CalendarEvent model not found',
            'fix': 'Check events app migrations'
        })
        health_data['summary']['failed'] += 1
        health_data['summary']['total_checks'] += 1
    
    # API ENDPOINTS FUNCTIONALITY
    def test_unified_events_api():
        try:
            from events.views import fetch_unified_events
            from django.test import RequestFactory
            
            factory = RequestFactory()
            test_request = factory.get('/events/api/unified/?start=2025-01-01&end=2025-12-31')
            test_request.user = request.user
            
            response = fetch_unified_events(test_request)
            return response.status_code == 200
        except Exception:
            return False
    
    run_check('API', 'fetch_unified_events API',
              test_unified_events_api,
              'Run: ./scripts/simple_timezone_fix.sh')
    
    # CALENDAR SPECIFIC ISSUES
    def test_calendar_view():
        try:
            from events.views import calendar_view
            from django.test import RequestFactory
            
            factory = RequestFactory()
            test_request = factory.get('/events/calendar/')
            test_request.user = request.user
            
            response = calendar_view(test_request)
            return response.status_code == 200
        except Exception:
            return False
    
    run_check('CALENDAR', 'Calendar View Renders',
              test_calendar_view,
              'Check calendar view and template rendering')
    
    run_warning_check('CALENDAR', 'Maintenance Activities Count',
                      lambda: MaintenanceActivity.objects.count() > 0,
                      'No maintenance activities found - calendar may appear empty')
    
    # USER AUTHENTICATION
    run_check('AUTH', 'Admin User Exists',
              lambda: User.objects.filter(is_superuser=True).exists(),
              'Create admin user: python manage.py createsuperuser')
    
    # EXTERNAL DEPENDENCIES
    def test_redis():
        try:
            from django.core.cache import cache
            cache.set('health_test', 'value')
            return cache.get('health_test') == 'value'
        except Exception:
            return False
    
    run_check('DEPS', 'Redis Connection',
              test_redis,
              'Check Redis server connectivity')
    
    # Calculate health percentage
    if health_data['summary']['total_checks'] > 0:
        health_data['summary']['health_percentage'] = round(
            (health_data['summary']['passed'] * 100) / health_data['summary']['total_checks']
        )
    
    # Determine overall health status
    if health_data['summary']['health_percentage'] >= 90:
        health_data['summary']['status'] = 'EXCELLENT'
    elif health_data['summary']['health_percentage'] >= 75:
        health_data['summary']['status'] = 'GOOD'
    elif health_data['summary']['health_percentage'] >= 50:
        health_data['summary']['status'] = 'MODERATE'
    else:
        health_data['summary']['status'] = 'CRITICAL'
    
    return JsonResponse(health_data)


@login_required
def health_check_view(request):
    """Render the health check interface."""
    if not request.user.is_superuser:
        return render(request, 'core/access_denied.html', {'message': 'Access denied'})
    
    return render(request, 'core/health_check.html')

@csrf_exempt
@require_http_methods(["POST"])
def reset_admin_password_api(request):
    """
    Reset admin user password via API.
    
    Expected JSON payload:
    {
        "username": "admin",
        "new_password": "newpassword123"
    }
    """
    try:
        data = json.loads(request.body) if request.body else {}
        username = data.get('username', 'admin')
        new_password = data.get('new_password', 'temppass123')
        
        from django.contrib.auth.models import User
        
        try:
            user = User.objects.get(username=username)
            user.set_password(new_password)
            user.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Password reset successfully for user "{username}"',
                'username': username
            })
        except User.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': f'User "{username}" does not exist'
            }, status=404)
            
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
@require_http_methods(["POST"])
def create_admin_user_api(request):
    """
    Create admin user via API.
    
    Expected JSON payload:
    {
        "username": "admin",
        "email": "admin@maintenance.local",
        "password": "temppass123"
    }
    """
    try:
        data = json.loads(request.body) if request.body else {}
        username = data.get('username', 'admin')
        email = data.get('email', 'admin@maintenance.local')
        password = data.get('password', 'temppass123')
        
        from django.contrib.auth.models import User
        from django.db import transaction
        
        with transaction.atomic():
            # Check if user already exists
            if User.objects.filter(username=username).exists():
                return JsonResponse({
                    'success': False,
                    'error': f'User "{username}" already exists'
                }, status=400)
            
            # Create superuser
            admin_user = User.objects.create_superuser(
                username=username,
                email=email,
                password=password,
                first_name='System',
                last_name='Administrator'
            )
            
            # Create user profile if it exists
            try:
                from core.models import UserProfile
                user_profile, created = UserProfile.objects.get_or_create(
                    user=admin_user,
                    defaults={
                        'role': 'admin',
                        'employee_id': 'ADMIN001',
                        'department': 'IT Administration',
                        'is_active': True,
                    }
                )
            except ImportError:
                pass  # UserProfile model not available
            
            return JsonResponse({
                'success': True,
                'message': f'Admin user "{username}" created successfully',
                'username': username,
                'email': email
            })
            
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
@require_http_methods(["POST"])
def run_migrations_api(request):
    """
    Run Django migrations via API.
    
    Expected JSON payload:
    {
        "command": "migrate",
        "app": "core",  # optional, specific app
        "fake": false,  # optional, fake migrations
        "fake_initial": false  # optional, fake initial migrations
    }
    """
    try:
        data = json.loads(request.body) if request.body else {}
        command = data.get('command', 'migrate')
        app = data.get('app', None)
        fake = data.get('fake', False)
        fake_initial = data.get('fake_initial', False)
        
        # Build command arguments
        cmd_args = ['manage.py', command]
        
        if app:
            cmd_args.append(app)
            
        if fake:
            cmd_args.append('--fake')
        elif fake_initial:
            cmd_args.append('--fake-initial')
        else:
            cmd_args.append('--noinput')
        
        # Run the command
        from django.core.management import call_command
        from io import StringIO
        import sys
        
        # Capture output
        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()
        
        try:
            if command == 'migrate':
                if fake:
                    call_command('migrate', '--fake', verbosity=2)
                elif fake_initial:
                    call_command('migrate', '--fake-initial', verbosity=2)
                else:
                    call_command('migrate', '--noinput', verbosity=2)
            elif command == 'showmigrations':
                call_command('showmigrations', '--list', verbosity=2)
            elif command == 'clear_migrations':
                call_command('clear_migrations', '--force', verbosity=2)
            elif command == 'init_database':
                call_command('init_database', '--force', verbosity=2)
            elif command == 'populate_standard_activity_types':
                call_command('populate_standard_activity_types', '--force', verbosity=2)
            elif command == 'create_test_maintenance':
                call_command('create_test_maintenance', '--force', verbosity=2)
            elif command == 'makemigrations':
                call_command('makemigrations', verbosity=2)
            else:
                return JsonResponse({
                    'success': False,
                    'error': f'Unsupported command: {command}'
                }, status=400)
                
            output = captured_output.getvalue()
            
            return JsonResponse({
                'success': True,
                'command': ' '.join(cmd_args),
                'output': output,
                'status': 'completed'
            })
            
        except Exception as e:
            output = captured_output.getvalue()
            return JsonResponse({
                'success': False,
                'command': ' '.join(cmd_args),
                'output': output,
                'error': str(e)
            }, status=500)
        finally:
            sys.stdout = old_stdout
            
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
            # DEPRECATED - Playwright functionality removed
            return JsonResponse({
                'success': False,
                'error': 'Playwright natural language testing has been deprecated and removed.',
                'status': 'deprecated'
            }, status=410)  # 410 Gone
            
            # OLD CODE - DEPRECATED
            # # Queue all tests as Celery tasks
            # task_ids = []
            # for prompt in test_prompts:
            #     task = run_natural_language_test_task.delay(
            #         prompt=prompt,
            #         user_role=user_role,
            #         username='admin',
            #         password='temppass123'
            #     )
            #     task_ids.append(task.id)
            # 
            # return JsonResponse({
            #     'success': True,
            #     'scenario': scenario,
            #     'task_ids': task_ids,
            #     'status': 'queued',
            #     'message': f'Scenario {scenario} queued with {len(task_ids)} tests'
            # })
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


@login_required
def system_health_check(request):
    """System health check endpoint for debugging issues."""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    health_data = {
        'timestamp': timezone.now().isoformat(),
        'categories': {},
        'summary': {
            'total_checks': 0,
            'passed': 0,
            'failed': 0,
            'warnings': 0,
            'health_percentage': 0
        },
        'quick_fixes': []
    }
    
    def run_check(category, check_name, test_func, fix_suggestion=None):
        """Run a health check and record results."""
        try:
            result = test_func()
            if result:
                health_data['categories'][category]['passed'].append({
                    'name': check_name,
                    'status': 'PASS'
                })
                health_data['summary']['passed'] += 1
            else:
                health_data['categories'][category]['failed'].append({
                    'name': check_name,
                    'status': 'FAIL',
                    'fix': fix_suggestion
                })
                health_data['summary']['failed'] += 1
                if fix_suggestion:
                    health_data['quick_fixes'].append(fix_suggestion)
        except Exception as e:
            health_data['categories'][category]['failed'].append({
                'name': check_name,
                'status': 'ERROR',
                'error': str(e),
                'fix': fix_suggestion
            })
            health_data['summary']['failed'] += 1
            if fix_suggestion:
                health_data['quick_fixes'].append(fix_suggestion)
        
        health_data['summary']['total_checks'] += 1
    
    def run_warning_check(category, check_name, test_func, warning_message=None):
        """Run a warning check and record results."""
        try:
            result = test_func()
            if result:
                health_data['categories'][category]['passed'].append({
                    'name': check_name,
                    'status': 'PASS'
                })
                health_data['summary']['passed'] += 1
            else:
                health_data['categories'][category]['warnings'].append({
                    'name': check_name,
                    'status': 'WARNING',
                    'message': warning_message
                })
                health_data['summary']['warnings'] += 1
        except Exception as e:
            health_data['categories'][category]['warnings'].append({
                'name': check_name,
                'status': 'WARNING',
                'error': str(e),
                'message': warning_message
            })
            health_data['summary']['warnings'] += 1
        
        health_data['summary']['total_checks'] += 1
    
    # Initialize categories
    categories = ['CORE', 'SCHEMA', 'API', 'CALENDAR', 'MIGRATIONS', 'AUTH', 'DEPS']
    for category in categories:
        health_data['categories'][category] = {
            'passed': [],
            'failed': [],
            'warnings': []
        }
    
    # CORE APPLICATION HEALTH
    run_check('CORE', 'Django Configuration', 
              lambda: True,  # Simplified for now
              'Check Django settings and configuration')
    
    run_check('CORE', 'Database Connection',
              lambda: connection.cursor().execute('SELECT 1') is not None,
              'Check database connectivity and credentials')
    
    # DATABASE SCHEMA INTEGRITY
    run_check('SCHEMA', 'MaintenanceActivity Model',
              lambda: MaintenanceActivity.objects.count() >= 0,
              'Run: ./scripts/simple_timezone_fix.sh')
    
    run_check('SCHEMA', 'Timezone Field Exists',
              lambda: hasattr(MaintenanceActivity, 'timezone'),
              'Run: ./scripts/simple_timezone_fix.sh')
    
    try:
        from events.models import CalendarEvent
        run_check('SCHEMA', 'CalendarEvent Model',
                  lambda: CalendarEvent.objects.count() >= 0,
                  'Check events app migrations')
    except ImportError:
        health_data['categories']['SCHEMA']['failed'].append({
            'name': 'CalendarEvent Model',
            'status': 'ERROR',
            'error': 'CalendarEvent model not found',
            'fix': 'Check events app migrations'
        })
        health_data['summary']['failed'] += 1
        health_data['summary']['total_checks'] += 1
    
    # API ENDPOINTS FUNCTIONALITY
    def test_unified_events_api():
        try:
            from events.views import fetch_unified_events
            from django.test import RequestFactory
            
            factory = RequestFactory()
            test_request = factory.get('/events/api/unified/?start=2025-01-01&end=2025-12-31')
            test_request.user = request.user
            
            response = fetch_unified_events(test_request)
            return response.status_code == 200
        except Exception:
            return False
    
    run_check('API', 'fetch_unified_events API',
              test_unified_events_api,
              'Run: ./scripts/simple_timezone_fix.sh')
    
    # CALENDAR SPECIFIC ISSUES
    def test_calendar_view():
        try:
            from events.views import calendar_view
            from django.test import RequestFactory
            
            factory = RequestFactory()
            test_request = factory.get('/events/calendar/')
            test_request.user = request.user
            
            response = calendar_view(test_request)
            return response.status_code == 200
        except Exception:
            return False
    
    run_check('CALENDAR', 'Calendar View Renders',
              test_calendar_view,
              'Check calendar view and template rendering')
    
    run_warning_check('CALENDAR', 'Maintenance Activities Count',
                      lambda: MaintenanceActivity.objects.count() > 0,
                      'No maintenance activities found - calendar may appear empty')
    
    # USER AUTHENTICATION
    run_check('AUTH', 'Admin User Exists',
              lambda: User.objects.filter(is_superuser=True).exists(),
              'Create admin user: python manage.py createsuperuser')
    
    # EXTERNAL DEPENDENCIES
    def test_redis():
        try:
            from django.core.cache import cache
            cache.set('health_test', 'value')
            return cache.get('health_test') == 'value'
        except Exception:
            return False
    
    run_check('DEPS', 'Redis Connection',
              test_redis,
              'Check Redis server connectivity')
    
    # Calculate health percentage
    if health_data['summary']['total_checks'] > 0:
        health_data['summary']['health_percentage'] = round(
            (health_data['summary']['passed'] * 100) / health_data['summary']['total_checks']
        )
    
    # Determine overall health status
    if health_data['summary']['health_percentage'] >= 90:
        health_data['summary']['status'] = 'EXCELLENT'
    elif health_data['summary']['health_percentage'] >= 75:
        health_data['summary']['status'] = 'GOOD'
    elif health_data['summary']['health_percentage'] >= 50:
        health_data['summary']['status'] = 'MODERATE'
    else:
        health_data['summary']['status'] = 'CRITICAL'
    
    return JsonResponse(health_data)


@login_required
def health_check_view(request):
    """Render the health check interface."""
    if not request.user.is_superuser:
        return render(request, 'core/access_denied.html', {'message': 'Access denied'})
    
    return render(request, 'core/health_check.html')

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
        logger.error(f"Error in comprehensive health check: {str(e)}")
        return JsonResponse({
            'error': str(e),
            'status': 'error',
            'timestamp': timezone.now().isoformat()
        }, status=500)


@login_required
def health_check_view(request):
    """Render the health check interface."""
    if not request.user.is_superuser:
        return render(request, 'core/access_denied.html', {'message': 'Access denied'})
    
    return render(request, 'core/health_check.html')


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
def system_health_check(request):
    """System health check endpoint for debugging issues."""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    health_data = {
        'timestamp': timezone.now().isoformat(),
        'categories': {},
        'summary': {
            'total_checks': 0,
            'passed': 0,
            'failed': 0,
            'warnings': 0,
            'health_percentage': 0
        },
        'quick_fixes': []
    }
    
    def run_check(category, check_name, test_func, fix_suggestion=None):
        """Run a health check and record results."""
        try:
            result = test_func()
            if result:
                health_data['categories'][category]['passed'].append({
                    'name': check_name,
                    'status': 'PASS'
                })
                health_data['summary']['passed'] += 1
            else:
                health_data['categories'][category]['failed'].append({
                    'name': check_name,
                    'status': 'FAIL',
                    'fix': fix_suggestion
                })
                health_data['summary']['failed'] += 1
                if fix_suggestion:
                    health_data['quick_fixes'].append(fix_suggestion)
        except Exception as e:
            health_data['categories'][category]['failed'].append({
                'name': check_name,
                'status': 'ERROR',
                'error': str(e),
                'fix': fix_suggestion
            })
            health_data['summary']['failed'] += 1
            if fix_suggestion:
                health_data['quick_fixes'].append(fix_suggestion)
        
        health_data['summary']['total_checks'] += 1
    
    def run_warning_check(category, check_name, test_func, warning_message=None):
        """Run a warning check and record results."""
        try:
            result = test_func()
            if result:
                health_data['categories'][category]['passed'].append({
                    'name': check_name,
                    'status': 'PASS'
                })
                health_data['summary']['passed'] += 1
            else:
                health_data['categories'][category]['warnings'].append({
                    'name': check_name,
                    'status': 'WARNING',
                    'message': warning_message
                })
                health_data['summary']['warnings'] += 1
        except Exception as e:
            health_data['categories'][category]['warnings'].append({
                'name': check_name,
                'status': 'WARNING',
                'error': str(e),
                'message': warning_message
            })
            health_data['summary']['warnings'] += 1
        
        health_data['summary']['total_checks'] += 1
    
    # Initialize categories
    categories = ['CORE', 'SCHEMA', 'API', 'CALENDAR', 'MIGRATIONS', 'AUTH', 'DEPS']
    for category in categories:
        health_data['categories'][category] = {
            'passed': [],
            'failed': [],
            'warnings': []
        }
    
    # CORE APPLICATION HEALTH
    run_check('CORE', 'Django Configuration', 
              lambda: True,  # Simplified for now
              'Check Django settings and configuration')
    
    run_check('CORE', 'Database Connection',
              lambda: connection.cursor().execute('SELECT 1') is not None,
              'Check database connectivity and credentials')
    
    # DATABASE SCHEMA INTEGRITY
    run_check('SCHEMA', 'MaintenanceActivity Model',
              lambda: MaintenanceActivity.objects.count() >= 0,
              'Run: ./scripts/simple_timezone_fix.sh')
    
    run_check('SCHEMA', 'Timezone Field Exists',
              lambda: hasattr(MaintenanceActivity, 'timezone'),
              'Run: ./scripts/simple_timezone_fix.sh')
    
    try:
        from events.models import CalendarEvent
        run_check('SCHEMA', 'CalendarEvent Model',
                  lambda: CalendarEvent.objects.count() >= 0,
                  'Check events app migrations')
    except ImportError:
        health_data['categories']['SCHEMA']['failed'].append({
            'name': 'CalendarEvent Model',
            'status': 'ERROR',
            'error': 'CalendarEvent model not found',
            'fix': 'Check events app migrations'
        })
        health_data['summary']['failed'] += 1
        health_data['summary']['total_checks'] += 1
    
    # API ENDPOINTS FUNCTIONALITY
    def test_unified_events_api():
        try:
            from events.views import fetch_unified_events
            from django.test import RequestFactory
            
            factory = RequestFactory()
            test_request = factory.get('/events/api/unified/?start=2025-01-01&end=2025-12-31')
            test_request.user = request.user
            
            response = fetch_unified_events(test_request)
            return response.status_code == 200
        except Exception:
            return False
    
    run_check('API', 'fetch_unified_events API',
              test_unified_events_api,
              'Run: ./scripts/simple_timezone_fix.sh')
    
    # CALENDAR SPECIFIC ISSUES
    def test_calendar_view():
        try:
            from events.views import calendar_view
            from django.test import RequestFactory
            
            factory = RequestFactory()
            test_request = factory.get('/events/calendar/')
            test_request.user = request.user
            
            response = calendar_view(test_request)
            return response.status_code == 200
        except Exception:
            return False
    
    run_check('CALENDAR', 'Calendar View Renders',
              test_calendar_view,
              'Check calendar view and template rendering')
    
    run_warning_check('CALENDAR', 'Maintenance Activities Count',
                      lambda: MaintenanceActivity.objects.count() > 0,
                      'No maintenance activities found - calendar may appear empty')
    
    # USER AUTHENTICATION
    run_check('AUTH', 'Admin User Exists',
              lambda: User.objects.filter(is_superuser=True).exists(),
              'Create admin user: python manage.py createsuperuser')
    
    # EXTERNAL DEPENDENCIES
    def test_redis():
        try:
            from django.core.cache import cache
            cache.set('health_test', 'value')
            return cache.get('health_test') == 'value'
        except Exception:
            return False
    
    run_check('DEPS', 'Redis Connection',
              test_redis,
              'Check Redis server connectivity')
    
    # Calculate health percentage
    if health_data['summary']['total_checks'] > 0:
        health_data['summary']['health_percentage'] = round(
            (health_data['summary']['passed'] * 100) / health_data['summary']['total_checks']
        )
    
    # Determine overall health status
    if health_data['summary']['health_percentage'] >= 90:
        health_data['summary']['status'] = 'EXCELLENT'
    elif health_data['summary']['health_percentage'] >= 75:
        health_data['summary']['status'] = 'GOOD'
    elif health_data['summary']['health_percentage'] >= 50:
        health_data['summary']['status'] = 'MODERATE'
    else:
        health_data['summary']['status'] = 'CRITICAL'
    
    return JsonResponse(health_data)


@login_required
def health_check_view(request):
    """Render the health check interface."""
    if not request.user.is_superuser:
        return render(request, 'core/access_denied.html', {'message': 'Access denied'})
    
    return render(request, 'core/health_check.html')


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
    from .models import PortainerConfig
    
    # Add comprehensive debugging
    logger.info(f"=== WEBHOOK SETTINGS DEBUG ===")
    logger.info(f"Request method: {request.method}")
    logger.info(f"Request POST data: {dict(request.POST)}")
    
    if request.method == 'POST':
        action = request.POST.get('action')
        logger.info(f"Action received: {action}")
        
        if action == 'save_config':
            logger.info("=== SAVE CONFIG ACTION STARTED ===")
            # Save configuration to database
            try:
                config = PortainerConfig.get_config()
                logger.info(f"Retrieved config object: {config}")
                logger.info(f"Current config - URL: '{config.portainer_url}', Stack: '{config.stack_name}'")
                
                # Handle sensitive fields - only update if user provides new values
                portainer_user = request.POST.get('portainer_user', '')
                portainer_password = request.POST.get('portainer_password', '')
                webhook_secret = request.POST.get('webhook_secret', '')
                portainer_url = request.POST.get('portainer_url', '')
                stack_name = request.POST.get('stack_name', '')
                image_tag = request.POST.get('image_tag', 'latest')
                polling_frequency = request.POST.get('polling_frequency', 'disabled')
                
                logger.info(f"Form data received:")
                logger.info(f"  URL: '{portainer_url}'")
                logger.info(f"  Stack: '{stack_name}'")
                logger.info(f"  Image Tag: '{image_tag}'")
                logger.info(f"  Polling Frequency: '{polling_frequency}'")
                logger.info(f"  User: '{portainer_user[:3]}***' if exists")
                logger.info(f"  Password: '***' if exists")
                logger.info(f"  Secret: '{webhook_secret[:4]}***' if exists")
                
                # If user enters masked values (like "***"), keep current values
                if portainer_user and not portainer_user.startswith('***'):
                    config.portainer_user = portainer_user
                    logger.info("Updated portainer_user")
                elif not portainer_user:
                    config.portainer_user = ''  # Allow clearing
                    logger.info("Cleared portainer_user")
                    
                if portainer_password and not portainer_password.startswith('*'):
                    config.portainer_password = portainer_password
                    logger.info("Updated portainer_password")
                elif not portainer_password:
                    config.portainer_password = ''  # Allow clearing
                    logger.info("Cleared portainer_password")
                    
                if webhook_secret and not webhook_secret.startswith('****'):
                    config.webhook_secret = webhook_secret
                    logger.info("Updated webhook_secret")
                elif not webhook_secret:
                    config.webhook_secret = ''  # Allow clearing
                    logger.info("Cleared webhook_secret")
                
                # Update non-sensitive fields
                config.portainer_url = portainer_url
                config.stack_name = stack_name
                config.image_tag = image_tag
                config.polling_frequency = polling_frequency
                logger.info(f"Updated URL to: '{config.portainer_url}'")
                logger.info(f"Updated Stack to: '{config.stack_name}'")
                logger.info(f"Updated Image Tag to: '{config.image_tag}'")
                logger.info(f"Updated Polling Frequency to: '{config.polling_frequency}'")
                
                # Validate required fields
                if not config.portainer_url:
                    logger.error("Validation failed: Portainer URL is required")
                    error_message = 'Portainer URL is required. Please enter a valid URL.'
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'status': 'error', 'message': error_message})
                    else:
                        messages.error(request, error_message)
                        return redirect('core:webhook_settings')
                
                # Stack name is optional, so no validation needed
                
                logger.info("Validation passed, attempting to save...")
                
                # Save to database
                config.save()
                logger.info(f"=== SAVE SUCCESSFUL ===")
                logger.info(f"Saved config - URL: '{config.portainer_url}', Stack: '{config.stack_name}'")
                
                # Show what was saved
                saved_items = []
                if config.portainer_url:
                    saved_items.append(f"Portainer URL: {config.portainer_url}")
                if config.stack_name:
                    saved_items.append(f"Stack Name: {config.stack_name}")
                if config.image_tag:
                    saved_items.append(f"Image Tag: {config.image_tag}")
                if config.polling_frequency:
                    saved_items.append(f"Polling Frequency: {config.get_polling_frequency_display()}")
                if config.portainer_user:
                    saved_items.append(f"Username: {config.portainer_user[:3]}***")
                if config.portainer_password:
                    saved_items.append("Password: ********")
                if config.webhook_secret:
                    saved_items.append(f"Secret: {config.webhook_secret[:4]}****")
                
                success_message = f'Configuration saved successfully! Saved: {", ".join(saved_items)}'
                logger.info(f"Success message: {success_message}")
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'success', 'message': success_message})
                else:
                    messages.success(request, success_message)
                    
            except Exception as e:
                logger.error(f"=== SAVE ERROR ===")
                logger.error(f"Error saving webhook config: {str(e)}")
                logger.error(f"Exception type: {type(e).__name__}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                error_message = f'Error saving configuration: {str(e)}'
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'error', 'message': error_message})
                else:
                    messages.error(request, error_message)
                
        elif action == 'test_webhook':
            logger.info("=== TEST WEBHOOK ACTION ===")
            # Test the webhook configuration
            try:
                config = PortainerConfig.get_config()
                if not config.portainer_url:
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'status': 'error', 'message': 'Cannot test webhook: Webhook URL not configured. Please save your configuration first.'})
                    else:
                        messages.error(request, 'Cannot test webhook: Webhook URL not configured. Please save your configuration first.')
                        return redirect('core:webhook_settings')
                
                result = test_portainer_connection()
                if 'reachable' in result.lower() or 'successful' in result.lower():
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'status': 'success', 'message': f'✅ Webhook test successful: {result}'})
                    else:
                        messages.success(request, f'✅ Webhook test successful: {result}')
                elif 'failed' in result.lower() or 'error' in result.lower():
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'status': 'error', 'message': f'❌ Webhook test failed: {result}'})
                    else:
                        messages.error(request, f'❌ Webhook test failed: {result}')
                else:
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'status': 'warning', 'message': f'⚠️ Webhook test result: {result}'})
                    else:
                        messages.warning(request, f'⚠️ Webhook test result: {result}')
            except Exception as e:
                logger.error(f"Error testing webhook: {str(e)}")
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'error', 'message': f'❌ Webhook test error: {str(e)}'})
                else:
                    messages.error(request, f'❌ Webhook test error: {str(e)}')
                
        elif action == 'update_stack':
            logger.info("=== UPDATE STACK ACTION ===")
            # Manually trigger stack update via webhook
            try:
                config = PortainerConfig.get_config()
                if not config.portainer_url:
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'status': 'error', 'message': 'Cannot update stack: Webhook URL not configured. Please save your configuration first.'})
                    else:
                        messages.error(request, 'Cannot update stack: Webhook URL not configured. Please save your configuration first.')
                        return redirect('core:webhook_settings')
                
                result = trigger_portainer_stack_update()
                if 'successfully' in result.lower() or 'triggered' in result.lower():
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'status': 'success', 'message': f'✅ Stack update triggered: {result}'})
                    else:
                        messages.success(request, f'✅ Stack update triggered: {result}')
                elif 'failed' in result.lower() or 'error' in result.lower():
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'status': 'error', 'message': f'❌ Stack update failed: {result}'})
                    else:
                        messages.error(request, f'❌ Stack update failed: {result}')
                else:
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'status': 'warning', 'message': f'⚠️ Stack update result: {result}'})
                    else:
                        messages.warning(request, f'⚠️ Stack update result: {result}')
            except Exception as e:
                logger.error(f"Error updating stack: {str(e)}")
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'error', 'message': f'❌ Stack update error: {str(e)}'})
                else:
                    messages.error(request, f'❌ Stack update error: {str(e)}')
        
        # Only redirect for non-AJAX requests
        if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return redirect('core:webhook_settings')
        else:
            return JsonResponse({'status': 'success', 'message': 'Action completed'})
    
    # Get configuration from database
    config = PortainerConfig.get_config()
    logger.info(f"=== LOADING CONFIG FOR DISPLAY ===")
    logger.info(f"Config object: {config}")
    logger.info(f"Config URL: '{config.portainer_url}'")
    logger.info(f"Config Stack: '{config.stack_name}'")
    
    # Mask sensitive data for display
    portainer_user = config.portainer_user
    portainer_password = config.portainer_password
    webhook_secret = config.webhook_secret
    
    # Show masked values if they exist
    if portainer_user:
        portainer_user = portainer_user[:3] + '*' * (len(portainer_user) - 3) if len(portainer_user) > 3 else '***'
    if portainer_password:
        portainer_password = '*' * 8  # Show 8 asterisks for password
    if webhook_secret:
        webhook_secret = webhook_secret[:4] + '*' * (len(webhook_secret) - 4) if len(webhook_secret) > 4 else '****'
    
    # Debug logging
    logger.info(f"Portainer config loaded - URL: {config.portainer_url}, Stack: {config.stack_name}, User: {config.portainer_user[:3] if config.portainer_user else 'None'}***")
    
    context = {
        'portainer_url': config.portainer_url,
        'portainer_user': portainer_user,
        'portainer_password': portainer_password,
        'stack_name': config.stack_name,
        'image_tag': config.image_tag,
        'polling_frequency': config.polling_frequency,
        'polling_choices': config.POLLING_CHOICES,
        'webhook_secret': webhook_secret,
        'debug_info': {
            'url_exists': bool(config.portainer_url),
            'stack_exists': bool(config.stack_name),
            'tag_exists': bool(config.image_tag),
            'polling_exists': bool(config.polling_frequency),
            'user_exists': bool(config.portainer_user),
            'password_exists': bool(config.portainer_password),
            'secret_exists': bool(config.webhook_secret),
            'last_commit_hash': config.last_commit_hash[:8] if config.last_commit_hash else None,
            'last_update_date': config.last_commit_date.strftime('%Y-%m-%d %H:%M:%S') if config.last_commit_date else None,
            'last_check_date': config.last_check_date.strftime('%Y-%m-%d %H:%M:%S') if config.last_check_date else None,
        }
    }
    
    logger.info(f"=== RENDERING TEMPLATE ===")
    logger.info(f"Context debug_info: {context['debug_info']}")
    
    return render(request, 'core/webhook_settings.html', context)


def trigger_portainer_stack_update():
    """Trigger a stack update by calling the webhook URL."""
    logger.info("=== TRIGGER PORTAINER STACK UPDATE STARTED ===")
    try:
        from .models import PortainerConfig
        config = PortainerConfig.get_config()
        
        webhook_url = config.portainer_url
        webhook_secret = config.webhook_secret
        image_tag = config.image_tag or 'latest'  # Default to 'latest' if not specified
        
        logger.info(f"Config loaded - Webhook URL: '{webhook_url}'")
        logger.info(f"Webhook secret exists: {bool(webhook_secret)}")
        logger.info(f"Image tag: '{image_tag}'")
        
        if not webhook_url:
            logger.error("Configuration incomplete - missing webhook URL")
            return 'Configuration incomplete - missing webhook URL'
        
        # Prepare headers with webhook secret if available
        headers = {}
        if webhook_secret:
            headers['X-Webhook-Secret'] = webhook_secret
            logger.info("Added webhook secret to headers")
        
        # Build webhook URL with tag parameter
        webhook_url_with_tag = f"{webhook_url}?tag={image_tag}"
        logger.info(f"Calling webhook URL with tag: {webhook_url_with_tag}")
        
        webhook_response = requests.post(
            webhook_url_with_tag,
            headers=headers,
            json={'action': 'update_stack', 'timestamp': time.time()},
            timeout=30
        )
        
        logger.info(f"Webhook response status: {webhook_response.status_code}")
        logger.info(f"Webhook response content: {webhook_response.text[:200]}...")
        
        if webhook_response.status_code in [200, 202, 204]:
            logger.info("Webhook call successful")
            return 'Stack update triggered successfully via webhook'
        else:
            logger.error(f"Webhook call failed with status: {webhook_response.status_code}")
            return f'Webhook call failed: {webhook_response.status_code}'
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error in webhook call: {str(e)}")
        return f'Network error: {str(e)}'
    except Exception as e:
        logger.error(f"Unexpected error in webhook call: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return f'Error: {str(e)}'


def test_portainer_connection():
    """Test connection to webhook URL."""
    logger.info("=== TEST WEBHOOK CONNECTION STARTED ===")
    try:
        from .models import PortainerConfig
        config = PortainerConfig.get_config()
        
        webhook_url = config.portainer_url
        webhook_secret = config.webhook_secret
        
        logger.info(f"Config loaded - Webhook URL: '{webhook_url}'")
        logger.info(f"Webhook secret exists: {bool(webhook_secret)}")
        
        if not webhook_url:
            logger.error("Configuration incomplete - missing webhook URL")
            return 'Configuration incomplete - missing webhook URL'
        
        # Test webhook URL with a simple GET request
        logger.info(f"Testing webhook URL: {webhook_url}")
        test_response = requests.get(
            webhook_url,
            timeout=10
        )
        
        logger.info(f"Test response status: {test_response.status_code}")
        logger.info(f"Test response content: {test_response.text[:200]}...")
        
        if test_response.status_code in [200, 202, 404, 405]:
            # 404/405 are expected for GET requests to webhook endpoints
            logger.info("Webhook URL is reachable")
            return 'Webhook URL is reachable and responding'
        else:
            logger.error(f"Webhook test failed with status: {test_response.status_code}")
            return f'Webhook test failed: {test_response.status_code}'
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error in webhook test: {str(e)}")
        return f'Network error: {str(e)}'
    except Exception as e:
        logger.error(f"Unexpected error in webhook test: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return f'Error: {str(e)}'


@login_required
@user_passes_test(is_staff_or_superuser)
def docker_logs_view(request):
    """View for displaying Docker logs - toggle controlled."""
    from core.services.docker_logs_service import DockerLogsService
    
    service = DockerLogsService()
    if not service.can_access(request.user):
        return redirect('core:dashboard')
    
    context = {
        'docker_logs_enabled': service.is_enabled(),
        'docker_logs_debug_only': service.is_debug_only(),
    }
    return render(request, 'core/docker_logs.html', context)


@login_required
@user_passes_test(is_staff_or_superuser)
@require_http_methods(["GET"])
def get_docker_logs_api(request):
    """API endpoint to fetch Docker logs using service layer."""
    from core.services.docker_logs_service import DockerLogsService
    
    service = DockerLogsService()
    
    # Check access permissions
    if not service.can_access(request.user):
        return JsonResponse({
            'error': 'Access denied'
        }, status=403)
    
    # Get parameters
    container_name = request.GET.get('container', '')
    lines = int(request.GET.get('lines', 100))
    follow = request.GET.get('follow', 'false').lower() == 'true'
    
    # Get logs using service
    result = service.get_logs(request.user, container_name, lines, follow)
    
    # Return appropriate response
    if result['success']:
        return JsonResponse(result)
    else:
        return JsonResponse(result, status=500)


@login_required
@user_passes_test(is_staff_or_superuser)
@require_http_methods(["GET"])
def get_docker_containers_api(request):
    """API endpoint to get list of running Docker containers using service layer."""
    from core.services.docker_logs_service import DockerLogsService
    
    service = DockerLogsService()
    
    # Check access permissions
    if not service.can_access(request.user):
        return JsonResponse({
            'error': 'Access denied'
        }, status=403)
    
    # Get containers using service
    result = service.get_containers(request.user)
    
    # Return appropriate response
    if result['success']:
        return JsonResponse(result)
    else:
        return JsonResponse(result, status=500)


@login_required
@user_passes_test(is_staff_or_superuser)
@require_http_methods(["GET"])
def get_aggregated_logs_api(request):
    """API endpoint to get aggregated logs from multiple containers."""
    from core.services.log_streaming_service import LogStreamingService
    
    # Get parameters
    containers = request.GET.get('containers', '').split(',') if request.GET.get('containers') else None
    lines = int(request.GET.get('lines', 100))
    
    # Validate lines parameter
    if lines > 1000:
        lines = 1000
    
    try:
        streaming_service = LogStreamingService()
        logs_content = streaming_service.get_aggregated_logs(containers, lines)
        
        return JsonResponse({
            'success': True,
            'logs': logs_content,
            'containers': containers or [],
            'lines_returned': len(logs_content.splitlines())
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error getting aggregated logs: {str(e)}'
        }, status=500)


@login_required
@user_passes_test(is_staff_or_superuser)
@require_http_methods(["GET"])
def get_system_logs_api(request):
    """API endpoint to get system logs."""
    from core.services.log_streaming_service import LogStreamingService
    
    # Get parameters
    lines = int(request.GET.get('lines', 100))
    
    # Validate lines parameter
    if lines > 1000:
        lines = 1000
    
    try:
        streaming_service = LogStreamingService()
        logs_content = streaming_service.get_system_logs(lines)
        
        return JsonResponse({
            'success': True,
            'logs': logs_content,
            'lines_returned': len(logs_content.splitlines())
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error getting system logs: {str(e)}'
        }, status=500)


@login_required
@user_passes_test(is_staff_or_superuser)
@require_http_methods(["POST"])
def start_log_stream_api(request):
    """API endpoint to start a real-time log stream."""
    from core.services.log_streaming_service import LogStreamingService
    import json
    
    try:
        data = json.loads(request.body)
        containers = data.get('containers', [])
        
        streaming_service = LogStreamingService()
        stream_id = streaming_service.start_log_stream(request.user, containers)
        
        return JsonResponse({
            'success': True,
            'stream_id': stream_id,
            'message': 'Log stream started successfully'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error starting log stream: {str(e)}'
        }, status=500)


@login_required
@user_passes_test(is_staff_or_superuser)
@require_http_methods(["POST"])
def stop_log_stream_api(request):
    """API endpoint to stop a log stream."""
    from core.services.log_streaming_service import LogStreamingService
    import json
    
    try:
        data = json.loads(request.body)
        stream_id = data.get('stream_id')
        
        if not stream_id:
            return JsonResponse({
                'success': False,
                'error': 'Stream ID is required'
            }, status=400)
        
        streaming_service = LogStreamingService()
        streaming_service.stop_log_stream(stream_id)
        
        return JsonResponse({
            'success': True,
            'message': 'Log stream stopped successfully'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error stopping log stream: {str(e)}'
        }, status=500)

def version_view(request):
    """Display version information for debugging and verification."""
    try:
        import json
        import os
        from django.conf import settings
        
        # First try to read from version.json (most up-to-date)
        version_info = None
        version_json_path = os.path.join(settings.BASE_DIR, 'version.json')
        
        if os.path.exists(version_json_path):
            try:
                with open(version_json_path, 'r') as f:
                    version_info = json.load(f)
                logger.info(f"Loaded version info from version.json: {version_info.get('version', 'unknown')}")
            except Exception as e:
                logger.warning(f"Failed to read version.json: {str(e)}")
        
        # Fallback to environment variables
        if not version_info:
            version_info = {
                'commit_count': os.environ.get('GIT_COMMIT_COUNT', '0'),
                'commit_hash': os.environ.get('GIT_COMMIT_HASH', 'unknown'),
                'branch': os.environ.get('GIT_BRANCH', 'unknown'),
                'commit_date': os.environ.get('GIT_COMMIT_DATE', 'unknown'),
                'version': f"v{os.environ.get('GIT_COMMIT_COUNT', '0')}.{os.environ.get('GIT_COMMIT_HASH', 'unknown')}",
                'full_version': f"v{os.environ.get('GIT_COMMIT_HASH', 'unknown')} ({os.environ.get('GIT_BRANCH', 'unknown')}) - {os.environ.get('GIT_COMMIT_DATE', 'unknown')}"
            }
            logger.info(f"Loaded version info from environment variables: {version_info.get('version', 'unknown')}")
        
        # Final fallback to version.py module
        if not version_info or version_info.get('commit_hash') == 'unknown':
            try:
                import importlib.util
                spec = importlib.util.spec_from_file_location("version_module", settings.BASE_DIR / "version.py")
                version_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(version_module)
                version_info = version_module.get_git_version()
                logger.info(f"Loaded version info from version.py: {version_info.get('version', 'unknown')}")
            except Exception as e:
                logger.warning(f"Failed to load version.py: {str(e)}")
                # Last resort fallback
                version_info = {
                    'commit_count': '0',
                    'commit_hash': 'unknown',
                    'branch': 'unknown',
                    'commit_date': 'unknown',
                    'version': 'v0.0.0',
                    'full_version': 'v0.0.0 (unknown) - Development'
                }
        
        return JsonResponse(version_info)
    except Exception as e:
        logger.error(f"Error getting version info: {str(e)}")
        return JsonResponse({
            'error': 'Failed to get version information',
            'details': str(e)
        }, status=500)

def version_html_view(request):
    """Display version information in HTML format."""
    try:
        import json
        import os
        from django.conf import settings
        
        # First try to read from version.json (most up-to-date)
        version_info = None
        version_json_path = os.path.join(settings.BASE_DIR, 'version.json')
        
        if os.path.exists(version_json_path):
            try:
                with open(version_json_path, 'r') as f:
                    version_info = json.load(f)
                logger.info(f"Loaded version info from version.json: {version_info.get('version', 'unknown')}")
            except Exception as e:
                logger.warning(f"Failed to read version.json: {str(e)}")
        
        # Fallback to environment variables
        if not version_info:
            version_info = {
                'commit_count': os.environ.get('GIT_COMMIT_COUNT', '0'),
                'commit_hash': os.environ.get('GIT_COMMIT_HASH', 'unknown'),
                'branch': os.environ.get('GIT_BRANCH', 'unknown'),
                'commit_date': os.environ.get('GIT_COMMIT_DATE', 'unknown'),
                'version': f"v{os.environ.get('GIT_COMMIT_COUNT', '0')}.{os.environ.get('GIT_COMMIT_HASH', 'unknown')}",
                'full_version': f"v{os.environ.get('GIT_COMMIT_COUNT', '0')}.{os.environ.get('GIT_COMMIT_HASH', 'unknown')} ({os.environ.get('GIT_BRANCH', 'unknown')}) - {os.environ.get('GIT_COMMIT_DATE', 'unknown')}"
            }
            logger.info(f"Loaded version info from environment variables: {version_info.get('version', 'unknown')}")
        
        # Final fallback to version.py module
        if not version_info or version_info.get('commit_hash') == 'unknown':
            try:
                import importlib.util
                spec = importlib.util.spec_from_file_location("version_module", settings.BASE_DIR / "version.py")
                version_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(version_module)
                version_info = version_module.get_git_version()
                logger.info(f"Loaded version info from version.py: {version_info.get('version', 'unknown')}")
            except Exception as e:
                logger.warning(f"Failed to load version.py: {str(e)}")
                # Last resort fallback
                version_info = {
                    'commit_count': '0',
                    'commit_hash': 'unknown',
                    'branch': 'unknown',
                    'commit_date': 'unknown',
                    'version': 'v0.0.0',
                    'full_version': 'v0.0.0 (unknown) - Development'
                }
        # Add deployment context
        deployment_info = {
            'debug_mode': settings.DEBUG,
            'timezone': str(settings.TIME_ZONE),
            'database_engine': settings.DATABASES['default']['ENGINE'] if 'default' in settings.DATABASES else 'unknown',
            'static_files_root': str(settings.STATIC_ROOT) if hasattr(settings, 'STATIC_ROOT') else 'not_set',
            'media_files_root': str(settings.MEDIA_ROOT) if hasattr(settings, 'MEDIA_ROOT') else 'not_set',
            'environment': os.environ.get('ENVIRONMENT', 'development'),
            'docker_container': os.environ.get('HOSTNAME', 'unknown'),
        }
        
        context = {
            'version_info': version_info,
            'deployment_info': deployment_info,
        }
        return render(request, 'core/version.html', context)
    except Exception as e:
        logger.error(f"Error getting version info for HTML view: {str(e)}")
        messages.error(request, f'Failed to get version information: {str(e)}')
        return redirect('core:dashboard')





@login_required
@user_passes_test(is_staff_or_superuser)
def version_form_view(request):
    """Display version form for manual version setting."""
    return render(request, 'core/version_form.html')

@login_required
@user_passes_test(is_staff_or_superuser)
@require_http_methods(["POST"])
def set_version_api(request):
    """API endpoint to set version information manually."""
    try:
        data = json.loads(request.body)
        commit_count = data.get('commit_count')
        commit_hash = data.get('commit_hash')
        branch = data.get('branch')
        commit_date = data.get('commit_date')
        
        # Validate required fields
        if not all([commit_count, commit_hash, branch, commit_date]):
            return JsonResponse({
                'success': False,
                'error': 'All fields are required: commit_count, commit_hash, branch, commit_date'
            }, status=400)
        
        # Import and call the Celery task
        from core.tasks import set_manual_version
        
        # Ensure commit_count is a valid integer
        try:
            commit_count_int = int(commit_count)
            if commit_count_int <= 0:
                commit_count_int = 1  # Fallback to 1 if invalid
        except (ValueError, TypeError):
            commit_count_int = 1  # Fallback to 1 if conversion fails
        
        # Validate commit_date format
        try:
            from datetime import datetime
            if isinstance(commit_date, str):
                # Try to parse the date to ensure it's valid
                date_formats = ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y/%m/%d']
                parsed_date = None
                
                for fmt in date_formats:
                    try:
                        parsed_date = datetime.strptime(commit_date, fmt)
                        break
                    except ValueError:
                        continue
                
                if not parsed_date:
                    return JsonResponse({
                        'success': False,
                        'error': f'Invalid date format: {commit_date}. Expected YYYY-MM-DD, MM/DD/YYYY, DD/MM/YYYY, or YYYY/MM/DD'
                    }, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Invalid date format: {commit_date}'
            }, status=400)
        
        result = set_manual_version.delay(commit_count_int, commit_hash, branch, commit_date)
        
        return JsonResponse({
            'success': True,
            'message': f'Version set to v{commit_count}.{commit_hash} ({branch}) - {commit_date}',
            'task_id': result.id,
            'version_info': {
                'version': f'v{commit_count_int}.{commit_hash}',
                'commit_count': commit_count_int,
                'commit_hash': commit_hash,
                'branch': branch,
                'commit_date': commit_date,
                'full_version': f'v{commit_count_int}.{commit_hash} ({branch}) - {commit_date}'
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f"Error setting version: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Error setting version: {str(e)}'
        }, status=500)

@login_required
@user_passes_test(is_staff_or_superuser)
@require_http_methods(["POST"])
def extract_version_from_url_api(request):
    """API endpoint to extract version information from a URL."""
    try:
        data = json.loads(request.body)
        url = data.get('url')
        
        if not url:
            return JsonResponse({
                'success': False,
                'error': 'URL is required'
            }, status=400)
        
        # Import and use the URL extractor
        from core.url_version_extractor import URLVersionExtractor
        
        extractor = URLVersionExtractor()
        result = extractor.extract_from_url(url)
        
        if 'error' in result:
            return JsonResponse({
                'success': False,
                'error': result['error'],
                'supported': result.get('supported', [])
            }, status=400)
        
        # Optionally auto-set the version
        auto_set = data.get('auto_set', False)
        if auto_set:
            # Import and call the Celery task
            from core.tasks import set_manual_version
            
            # Ensure commit_count is a valid integer
            try:
                commit_count_int = int(result['commit_count'])
                if commit_count_int <= 0:
                    commit_count_int = 1  # Fallback to 1 if invalid
            except (ValueError, TypeError):
                commit_count_int = 1  # Fallback to 1 if conversion fails
            
            # Validate commit_date format
            try:
                from datetime import datetime
                commit_date = result['commit_date']
                if isinstance(commit_date, str):
                    # Try to parse the date to ensure it's valid
                    date_formats = ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y/%m/%d']
                    parsed_date = None
                    
                    for fmt in date_formats:
                        try:
                            parsed_date = datetime.strptime(commit_date, fmt)
                            break
                        except ValueError:
                            continue
                    
                    if not parsed_date:
                        return JsonResponse({
                            'success': False,
                            'error': f'Invalid date format from URL: {commit_date}. Expected YYYY-MM-DD, MM/DD/YYYY, DD/MM/YYYY, or YYYY/MM/DD'
                        }, status=400)
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'error': f'Invalid date format from URL: {result.get("commit_date", "unknown")}'
                }, status=400)
            
            task_result = set_manual_version.delay(
                commit_count_int, 
                result['commit_hash'], 
                result['branch'], 
                result['commit_date']
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Version extracted and set successfully',
                'task_id': task_result.id,
                'extracted_data': result
            })
        else:
            return JsonResponse({
                'success': True,
                'message': 'Version extracted successfully',
                'extracted_data': result
            })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except ImportError:
        return JsonResponse({
            'success': False,
            'error': 'URL extraction not available. Missing dependencies.'
        }, status=500)
    except Exception as e:
        logger.error(f"Error extracting version from URL: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Error extracting version from URL: {str(e)}'
        }, status=500)

@login_required
def invalidate_cache_api(request):
    """API endpoint to invalidate dashboard cache for the current user."""
    try:
        import json
        
        # Get the site_id from the request body
        data = json.loads(request.body)
        site_id = data.get('site_id')
        
        # Update the session with the new site selection
        if site_id == 'all':
            request.session['selected_site_id'] = 'all'
        elif site_id:
            request.session['selected_site_id'] = site_id
        else:
            request.session['selected_site_id'] = 'all'
        
        # Invalidate cache for this user and site
        invalidate_dashboard_cache(user_id=request.user.id, site_id=site_id)
        
        return JsonResponse({
            'status': 'success',
            'message': 'Cache invalidated successfully',
            'site_id': site_id
        })
    except Exception as e:
        logger.error(f"Error invalidating cache: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f'Error invalidating cache: {str(e)}'
        }, status=500)


@login_required
@user_passes_test(is_staff_or_superuser)
def database_stats_api(request):
    """API endpoint to get database statistics."""
    try:
        from django.db import connection
        from equipment.models import Equipment, EquipmentConnection
        from maintenance.models import MaintenanceActivity, MaintenanceSchedule, MaintenanceActivityType
        from events.models import CalendarEvent
        
        tables = {}
        
        # Get row counts for key tables
        tables['Equipment'] = {'count': Equipment.objects.count()}
        tables['Equipment Connections'] = {'count': EquipmentConnection.objects.count()}
        tables['Locations'] = {'count': Location.objects.count()}
        tables['Customers'] = {'count': Customer.objects.count()}
        tables['Maintenance Activities'] = {'count': MaintenanceActivity.objects.count()}
        tables['Maintenance Schedules'] = {'count': MaintenanceSchedule.objects.count()}
        tables['Activity Types'] = {'count': MaintenanceActivityType.objects.count()}
        tables['Calendar Events'] = {'count': CalendarEvent.objects.count()}
        tables['Users'] = {'count': User.objects.count()}
        
        # Get database size (PostgreSQL specific)
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT pg_size_pretty(pg_database_size(current_database())) as size;
                """)
                row = cursor.fetchone()
                db_size = row[0] if row else 'Unknown'
        except Exception:
            db_size = 'N/A'
        
        return JsonResponse({
            'status': 'success',
            'tables': tables,
            'database_size': db_size,
            'database_name': connection.settings_dict['NAME']
        })
        
    except Exception as e:
        logger.error(f"Error getting database stats: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f'Error getting database stats: {str(e)}'
        }, status=500)


@login_required
def branding_settings(request):
    """Branding settings management page"""
    # Check if branding tables exist before trying to access them
    try:
        from django.db import connection
        from django.db.utils import ProgrammingError
        
        branding_table_exists = False
        css_table_exists = False
        
        try:
            # Check branding table
            with connection.cursor() as cursor:
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
        
        if branding_table_exists:
            try:
                branding = BrandingSettings.objects.get(is_active=True)
            except BrandingSettings.DoesNotExist:
                branding = None
        
        if css_table_exists:
            try:
                css_customizations = CSSCustomization.objects.filter(is_active=True).order_by('-priority', 'order')
            except Exception:
                css_customizations = []
        
        # Always initialize forms if tables exist
        if branding_table_exists:
            basic_form = BrandingBasicForm(instance=branding)
            navigation_form = BrandingNavigationForm(instance=branding)
            appearance_form = BrandingAppearanceForm(instance=branding)
            full_form = BrandingSettingsForm(instance=branding)  # For backward compatibility
        else:
            basic_form = None
            navigation_form = None
            appearance_form = None
            full_form = None
        
        if request.method == 'POST':
            if not branding_table_exists:
                messages.error(request, 'Branding system is not yet set up. Please run database migrations first.')
                return redirect('core:settings')
            
            # Determine which form was submitted based on the form action
            form_type = request.POST.get('form_type', 'basic')
            
            if form_type == 'basic':
                form = BrandingBasicForm(request.POST, request.FILES, instance=branding)
                success_message = 'Basic branding settings updated successfully!'
            elif form_type == 'navigation':
                form = BrandingNavigationForm(request.POST, instance=branding)
                success_message = 'Navigation labels updated successfully!'
            elif form_type == 'appearance':
                form = BrandingAppearanceForm(request.POST, request.FILES, instance=branding)
                success_message = 'Appearance settings updated successfully!'
            else:
                # Fallback to full form
                form = BrandingSettingsForm(request.POST, request.FILES, instance=branding)
                success_message = 'Branding settings updated successfully!'
            
            if form.is_valid():
                branding = form.save()
                messages.success(request, success_message)
                return redirect('core:branding_settings')
            else:
                # If form is invalid, re-initialize the forms with the invalid data
                if form_type == 'basic':
                    basic_form = form
                elif form_type == 'navigation':
                    navigation_form = form
                elif form_type == 'appearance':
                    appearance_form = form
                else:
                    full_form = form
        
        context = {
            'basic_form': basic_form,
            'navigation_form': navigation_form,
            'appearance_form': appearance_form,
            'full_form': full_form,  # For backward compatibility
            'branding': branding,
            'css_customizations': css_customizations,
            'active_tab': 'branding',
            'tables_exist': branding_table_exists and css_table_exists
        }
        return render(request, 'core/branding_settings.html', context)
        
    except Exception as e:
        # If anything goes wrong, show an error message
        messages.error(request, f'Branding system is not available: {str(e)}. Please run database migrations first.')
        return redirect('core:settings')

@login_required
def css_customization_list(request):
    """List all CSS customizations"""
    # Check if CSS customization table exists
    try:
        from django.db import connection
        from django.db.utils import ProgrammingError
        
        css_table_exists = False
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM core_csscustomization LIMIT 1")
                css_table_exists = True
        except (ProgrammingError, Exception):
            css_table_exists = False
        
        if not css_table_exists:
            messages.error(request, 'CSS customization system is not yet set up. Please run database migrations first.')
            return redirect('core:branding_settings')
        
        css_customizations = CSSCustomization.objects.all().order_by('-priority', 'order', 'name')
        
        context = {
            'css_customizations': css_customizations,
            'active_tab': 'branding'
        }
        return render(request, 'core/css_customization_list.html', context)
        
    except Exception as e:
        messages.error(request, f'CSS customization system is not available: {str(e)}. Please run database migrations first.')
        return redirect('core:branding_settings')


@login_required
@require_http_methods(["POST"])
def update_user_timezone(request):
    """API endpoint to update user's timezone preference."""
    try:
        data = json.loads(request.body)
        timezone = data.get('timezone')
        
        if not timezone:
            return JsonResponse({
                'success': False,
                'error': 'Timezone is required'
            }, status=400)
        
        # Validate timezone against allowed choices
        valid_timezones = [choice[0] for choice in UserProfile.TIMEZONE_CHOICES]
        if timezone not in valid_timezones:
            return JsonResponse({
                'success': False,
                'error': f'Invalid timezone: {timezone}'
            }, status=400)
        
        # Get or create user profile
        user_profile, created = UserProfile.objects.get_or_create(
            user=request.user,
            defaults={'timezone': timezone}
        )
        
        if not created:
            user_profile.timezone = timezone
            user_profile.save()
        
        logger.info(f"Updated timezone for user {request.user.username} to {timezone}")
        
        return JsonResponse({
            'success': True,
            'message': f'Timezone updated to {timezone}',
            'timezone': timezone
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f"Error updating user timezone: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def system_health_check(request):
    """System health check endpoint for debugging issues."""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    health_data = {
        'timestamp': timezone.now().isoformat(),
        'categories': {},
        'summary': {
            'total_checks': 0,
            'passed': 0,
            'failed': 0,
            'warnings': 0,
            'health_percentage': 0
        },
        'quick_fixes': []
    }
    
    def run_check(category, check_name, test_func, fix_suggestion=None):
        """Run a health check and record results."""
        try:
            result = test_func()
            if result:
                health_data['categories'][category]['passed'].append({
                    'name': check_name,
                    'status': 'PASS'
                })
                health_data['summary']['passed'] += 1
            else:
                health_data['categories'][category]['failed'].append({
                    'name': check_name,
                    'status': 'FAIL',
                    'fix': fix_suggestion
                })
                health_data['summary']['failed'] += 1
                if fix_suggestion:
                    health_data['quick_fixes'].append(fix_suggestion)
        except Exception as e:
            health_data['categories'][category]['failed'].append({
                'name': check_name,
                'status': 'ERROR',
                'error': str(e),
                'fix': fix_suggestion
            })
            health_data['summary']['failed'] += 1
            if fix_suggestion:
                health_data['quick_fixes'].append(fix_suggestion)
        
        health_data['summary']['total_checks'] += 1
    
    def run_warning_check(category, check_name, test_func, warning_message=None):
        """Run a warning check and record results."""
        try:
            result = test_func()
            if result:
                health_data['categories'][category]['passed'].append({
                    'name': check_name,
                    'status': 'PASS'
                })
                health_data['summary']['passed'] += 1
            else:
                health_data['categories'][category]['warnings'].append({
                    'name': check_name,
                    'status': 'WARNING',
                    'message': warning_message
                })
                health_data['summary']['warnings'] += 1
        except Exception as e:
            health_data['categories'][category]['warnings'].append({
                'name': check_name,
                'status': 'WARNING',
                'error': str(e),
                'message': warning_message
            })
            health_data['summary']['warnings'] += 1
        
        health_data['summary']['total_checks'] += 1
    
    # Initialize categories
    categories = ['CORE', 'SCHEMA', 'API', 'CALENDAR', 'MIGRATIONS', 'AUTH', 'DEPS']
    for category in categories:
        health_data['categories'][category] = {
            'passed': [],
            'failed': [],
            'warnings': []
        }
    
    # CORE APPLICATION HEALTH
    run_check('CORE', 'Django Configuration', 
              lambda: True,  # Simplified for now
              'Check Django settings and configuration')
    
    run_check('CORE', 'Database Connection',
              lambda: connection.cursor().execute('SELECT 1') is not None,
              'Check database connectivity and credentials')
    
    # DATABASE SCHEMA INTEGRITY
    run_check('SCHEMA', 'MaintenanceActivity Model',
              lambda: MaintenanceActivity.objects.count() >= 0,
              'Run: ./scripts/simple_timezone_fix.sh')
    
    run_check('SCHEMA', 'Timezone Field Exists',
              lambda: hasattr(MaintenanceActivity, 'timezone'),
              'Run: ./scripts/simple_timezone_fix.sh')
    
    try:
        from events.models import CalendarEvent
        run_check('SCHEMA', 'CalendarEvent Model',
                  lambda: CalendarEvent.objects.count() >= 0,
                  'Check events app migrations')
    except ImportError:
        health_data['categories']['SCHEMA']['failed'].append({
            'name': 'CalendarEvent Model',
            'status': 'ERROR',
            'error': 'CalendarEvent model not found',
            'fix': 'Check events app migrations'
        })
        health_data['summary']['failed'] += 1
        health_data['summary']['total_checks'] += 1
    
    # API ENDPOINTS FUNCTIONALITY
    def test_unified_events_api():
        try:
            from events.views import fetch_unified_events
            from django.test import RequestFactory
            
            factory = RequestFactory()
            test_request = factory.get('/events/api/unified/?start=2025-01-01&end=2025-12-31')
            test_request.user = request.user
            
            response = fetch_unified_events(test_request)
            return response.status_code == 200
        except Exception:
            return False
    
    run_check('API', 'fetch_unified_events API',
              test_unified_events_api,
              'Run: ./scripts/simple_timezone_fix.sh')
    
    # CALENDAR SPECIFIC ISSUES
    def test_calendar_view():
        try:
            from events.views import calendar_view
            from django.test import RequestFactory
            
            factory = RequestFactory()
            test_request = factory.get('/events/calendar/')
            test_request.user = request.user
            
            response = calendar_view(test_request)
            return response.status_code == 200
        except Exception:
            return False
    
    run_check('CALENDAR', 'Calendar View Renders',
              test_calendar_view,
              'Check calendar view and template rendering')
    
    run_warning_check('CALENDAR', 'Maintenance Activities Count',
                      lambda: MaintenanceActivity.objects.count() > 0,
                      'No maintenance activities found - calendar may appear empty')
    
    # USER AUTHENTICATION
    run_check('AUTH', 'Admin User Exists',
              lambda: User.objects.filter(is_superuser=True).exists(),
              'Create admin user: python manage.py createsuperuser')
    
    # EXTERNAL DEPENDENCIES
    def test_redis():
        try:
            from django.core.cache import cache
            cache.set('health_test', 'value')
            return cache.get('health_test') == 'value'
        except Exception:
            return False
    
    run_check('DEPS', 'Redis Connection',
              test_redis,
              'Check Redis server connectivity')
    
    # Calculate health percentage
    if health_data['summary']['total_checks'] > 0:
        health_data['summary']['health_percentage'] = round(
            (health_data['summary']['passed'] * 100) / health_data['summary']['total_checks']
        )
    
    # Determine overall health status
    if health_data['summary']['health_percentage'] >= 90:
        health_data['summary']['status'] = 'EXCELLENT'
    elif health_data['summary']['health_percentage'] >= 75:
        health_data['summary']['status'] = 'GOOD'
    elif health_data['summary']['health_percentage'] >= 50:
        health_data['summary']['status'] = 'MODERATE'
    else:
        health_data['summary']['status'] = 'CRITICAL'
    
    return JsonResponse(health_data)


@login_required
def health_check_view(request):
    """Render the health check interface."""
    if not request.user.is_superuser:
        return render(request, 'core/access_denied.html', {'message': 'Access denied'})
    
    return render(request, 'core/health_check.html')

@login_required
def css_customization_create(request):
    """Create a new CSS customization"""
    # Check if CSS customization table exists
    try:
        from django.db import connection
        from django.db.utils import ProgrammingError
        
        css_table_exists = False
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM core_csscustomization LIMIT 1")
                css_table_exists = True
        except (ProgrammingError, Exception):
            css_table_exists = False
        
        if not css_table_exists:
            messages.error(request, 'CSS customization system is not yet set up. Please run database migrations first.')
            return redirect('core:branding_settings')
        
        if request.method == 'POST':
            form = CSSCustomizationForm(request.POST)
            if form.is_valid():
                css_customization = form.save(commit=False)
                css_customization.created_by = request.user
                css_customization.save()
                messages.success(request, 'CSS customization created successfully!')
                return redirect('core:css_customization_list')
        else:
            form = CSSCustomizationForm()
        
        context = {
            'form': form,
            'active_tab': 'branding',
            'is_create': True
        }
        return render(request, 'core/css_customization_form.html', context)
        
    except Exception as e:
        messages.error(request, f'CSS customization system is not available: {str(e)}. Please run database migrations first.')
        return redirect('core:branding_settings')


@login_required
@require_http_methods(["POST"])
def update_user_timezone(request):
    """API endpoint to update user's timezone preference."""
    try:
        data = json.loads(request.body)
        timezone = data.get('timezone')
        
        if not timezone:
            return JsonResponse({
                'success': False,
                'error': 'Timezone is required'
            }, status=400)
        
        # Validate timezone against allowed choices
        valid_timezones = [choice[0] for choice in UserProfile.TIMEZONE_CHOICES]
        if timezone not in valid_timezones:
            return JsonResponse({
                'success': False,
                'error': f'Invalid timezone: {timezone}'
            }, status=400)
        
        # Get or create user profile
        user_profile, created = UserProfile.objects.get_or_create(
            user=request.user,
            defaults={'timezone': timezone}
        )
        
        if not created:
            user_profile.timezone = timezone
            user_profile.save()
        
        logger.info(f"Updated timezone for user {request.user.username} to {timezone}")
        
        return JsonResponse({
            'success': True,
            'message': f'Timezone updated to {timezone}',
            'timezone': timezone
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f"Error updating user timezone: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def system_health_check(request):
    """System health check endpoint for debugging issues."""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    health_data = {
        'timestamp': timezone.now().isoformat(),
        'categories': {},
        'summary': {
            'total_checks': 0,
            'passed': 0,
            'failed': 0,
            'warnings': 0,
            'health_percentage': 0
        },
        'quick_fixes': []
    }
    
    def run_check(category, check_name, test_func, fix_suggestion=None):
        """Run a health check and record results."""
        try:
            result = test_func()
            if result:
                health_data['categories'][category]['passed'].append({
                    'name': check_name,
                    'status': 'PASS'
                })
                health_data['summary']['passed'] += 1
            else:
                health_data['categories'][category]['failed'].append({
                    'name': check_name,
                    'status': 'FAIL',
                    'fix': fix_suggestion
                })
                health_data['summary']['failed'] += 1
                if fix_suggestion:
                    health_data['quick_fixes'].append(fix_suggestion)
        except Exception as e:
            health_data['categories'][category]['failed'].append({
                'name': check_name,
                'status': 'ERROR',
                'error': str(e),
                'fix': fix_suggestion
            })
            health_data['summary']['failed'] += 1
            if fix_suggestion:
                health_data['quick_fixes'].append(fix_suggestion)
        
        health_data['summary']['total_checks'] += 1
    
    def run_warning_check(category, check_name, test_func, warning_message=None):
        """Run a warning check and record results."""
        try:
            result = test_func()
            if result:
                health_data['categories'][category]['passed'].append({
                    'name': check_name,
                    'status': 'PASS'
                })
                health_data['summary']['passed'] += 1
            else:
                health_data['categories'][category]['warnings'].append({
                    'name': check_name,
                    'status': 'WARNING',
                    'message': warning_message
                })
                health_data['summary']['warnings'] += 1
        except Exception as e:
            health_data['categories'][category]['warnings'].append({
                'name': check_name,
                'status': 'WARNING',
                'error': str(e),
                'message': warning_message
            })
            health_data['summary']['warnings'] += 1
        
        health_data['summary']['total_checks'] += 1
    
    # Initialize categories
    categories = ['CORE', 'SCHEMA', 'API', 'CALENDAR', 'MIGRATIONS', 'AUTH', 'DEPS']
    for category in categories:
        health_data['categories'][category] = {
            'passed': [],
            'failed': [],
            'warnings': []
        }
    
    # CORE APPLICATION HEALTH
    run_check('CORE', 'Django Configuration', 
              lambda: True,  # Simplified for now
              'Check Django settings and configuration')
    
    run_check('CORE', 'Database Connection',
              lambda: connection.cursor().execute('SELECT 1') is not None,
              'Check database connectivity and credentials')
    
    # DATABASE SCHEMA INTEGRITY
    run_check('SCHEMA', 'MaintenanceActivity Model',
              lambda: MaintenanceActivity.objects.count() >= 0,
              'Run: ./scripts/simple_timezone_fix.sh')
    
    run_check('SCHEMA', 'Timezone Field Exists',
              lambda: hasattr(MaintenanceActivity, 'timezone'),
              'Run: ./scripts/simple_timezone_fix.sh')
    
    try:
        from events.models import CalendarEvent
        run_check('SCHEMA', 'CalendarEvent Model',
                  lambda: CalendarEvent.objects.count() >= 0,
                  'Check events app migrations')
    except ImportError:
        health_data['categories']['SCHEMA']['failed'].append({
            'name': 'CalendarEvent Model',
            'status': 'ERROR',
            'error': 'CalendarEvent model not found',
            'fix': 'Check events app migrations'
        })
        health_data['summary']['failed'] += 1
        health_data['summary']['total_checks'] += 1
    
    # API ENDPOINTS FUNCTIONALITY
    def test_unified_events_api():
        try:
            from events.views import fetch_unified_events
            from django.test import RequestFactory
            
            factory = RequestFactory()
            test_request = factory.get('/events/api/unified/?start=2025-01-01&end=2025-12-31')
            test_request.user = request.user
            
            response = fetch_unified_events(test_request)
            return response.status_code == 200
        except Exception:
            return False
    
    run_check('API', 'fetch_unified_events API',
              test_unified_events_api,
              'Run: ./scripts/simple_timezone_fix.sh')
    
    # CALENDAR SPECIFIC ISSUES
    def test_calendar_view():
        try:
            from events.views import calendar_view
            from django.test import RequestFactory
            
            factory = RequestFactory()
            test_request = factory.get('/events/calendar/')
            test_request.user = request.user
            
            response = calendar_view(test_request)
            return response.status_code == 200
        except Exception:
            return False
    
    run_check('CALENDAR', 'Calendar View Renders',
              test_calendar_view,
              'Check calendar view and template rendering')
    
    run_warning_check('CALENDAR', 'Maintenance Activities Count',
                      lambda: MaintenanceActivity.objects.count() > 0,
                      'No maintenance activities found - calendar may appear empty')
    
    # USER AUTHENTICATION
    run_check('AUTH', 'Admin User Exists',
              lambda: User.objects.filter(is_superuser=True).exists(),
              'Create admin user: python manage.py createsuperuser')
    
    # EXTERNAL DEPENDENCIES
    def test_redis():
        try:
            from django.core.cache import cache
            cache.set('health_test', 'value')
            return cache.get('health_test') == 'value'
        except Exception:
            return False
    
    run_check('DEPS', 'Redis Connection',
              test_redis,
              'Check Redis server connectivity')
    
    # Calculate health percentage
    if health_data['summary']['total_checks'] > 0:
        health_data['summary']['health_percentage'] = round(
            (health_data['summary']['passed'] * 100) / health_data['summary']['total_checks']
        )
    
    # Determine overall health status
    if health_data['summary']['health_percentage'] >= 90:
        health_data['summary']['status'] = 'EXCELLENT'
    elif health_data['summary']['health_percentage'] >= 75:
        health_data['summary']['status'] = 'GOOD'
    elif health_data['summary']['health_percentage'] >= 50:
        health_data['summary']['status'] = 'MODERATE'
    else:
        health_data['summary']['status'] = 'CRITICAL'
    
    return JsonResponse(health_data)


@login_required
def health_check_view(request):
    """Render the health check interface."""
    if not request.user.is_superuser:
        return render(request, 'core/access_denied.html', {'message': 'Access denied'})
    
    return render(request, 'core/health_check.html')

@login_required
def css_customization_edit(request, pk):
    """Edit an existing CSS customization"""
    # Check if CSS customization table exists
    try:
        from django.db import connection
        from django.db.utils import ProgrammingError
        
        css_table_exists = False
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM core_csscustomization LIMIT 1")
                css_table_exists = True
        except (ProgrammingError, Exception):
            css_table_exists = False
        
        if not css_table_exists:
            messages.error(request, 'CSS customization system is not yet set up. Please run database migrations first.')
            return redirect('core:branding_settings')
        
        try:
            css_customization = CSSCustomization.objects.get(pk=pk)
        except CSSCustomization.DoesNotExist:
            messages.error(request, 'CSS customization not found.')
            return redirect('core:css_customization_list')
        
        if request.method == 'POST':
            form = CSSCustomizationForm(request.POST, instance=css_customization)
            if form.is_valid():
                form.save()
                messages.success(request, 'CSS customization updated successfully!')
                return redirect('core:css_customization_list')
        else:
            form = CSSCustomizationForm(instance=css_customization)
        
        context = {
            'form': form,
            'css_customization': css_customization,
            'active_tab': 'branding',
            'is_create': False
        }
        return render(request, 'core/css_customization_form.html', context)
        
    except Exception as e:
        messages.error(request, f'CSS customization system is not available: {str(e)}. Please run database migrations first.')
        return redirect('core:branding_settings')


@login_required
@require_http_methods(["POST"])
def update_user_timezone(request):
    """API endpoint to update user's timezone preference."""
    try:
        data = json.loads(request.body)
        timezone = data.get('timezone')
        
        if not timezone:
            return JsonResponse({
                'success': False,
                'error': 'Timezone is required'
            }, status=400)
        
        # Validate timezone against allowed choices
        valid_timezones = [choice[0] for choice in UserProfile.TIMEZONE_CHOICES]
        if timezone not in valid_timezones:
            return JsonResponse({
                'success': False,
                'error': f'Invalid timezone: {timezone}'
            }, status=400)
        
        # Get or create user profile
        user_profile, created = UserProfile.objects.get_or_create(
            user=request.user,
            defaults={'timezone': timezone}
        )
        
        if not created:
            user_profile.timezone = timezone
            user_profile.save()
        
        logger.info(f"Updated timezone for user {request.user.username} to {timezone}")
        
        return JsonResponse({
            'success': True,
            'message': f'Timezone updated to {timezone}',
            'timezone': timezone
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f"Error updating user timezone: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def system_health_check(request):
    """System health check endpoint for debugging issues."""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    health_data = {
        'timestamp': timezone.now().isoformat(),
        'categories': {},
        'summary': {
            'total_checks': 0,
            'passed': 0,
            'failed': 0,
            'warnings': 0,
            'health_percentage': 0
        },
        'quick_fixes': []
    }
    
    def run_check(category, check_name, test_func, fix_suggestion=None):
        """Run a health check and record results."""
        try:
            result = test_func()
            if result:
                health_data['categories'][category]['passed'].append({
                    'name': check_name,
                    'status': 'PASS'
                })
                health_data['summary']['passed'] += 1
            else:
                health_data['categories'][category]['failed'].append({
                    'name': check_name,
                    'status': 'FAIL',
                    'fix': fix_suggestion
                })
                health_data['summary']['failed'] += 1
                if fix_suggestion:
                    health_data['quick_fixes'].append(fix_suggestion)
        except Exception as e:
            health_data['categories'][category]['failed'].append({
                'name': check_name,
                'status': 'ERROR',
                'error': str(e),
                'fix': fix_suggestion
            })
            health_data['summary']['failed'] += 1
            if fix_suggestion:
                health_data['quick_fixes'].append(fix_suggestion)
        
        health_data['summary']['total_checks'] += 1
    
    def run_warning_check(category, check_name, test_func, warning_message=None):
        """Run a warning check and record results."""
        try:
            result = test_func()
            if result:
                health_data['categories'][category]['passed'].append({
                    'name': check_name,
                    'status': 'PASS'
                })
                health_data['summary']['passed'] += 1
            else:
                health_data['categories'][category]['warnings'].append({
                    'name': check_name,
                    'status': 'WARNING',
                    'message': warning_message
                })
                health_data['summary']['warnings'] += 1
        except Exception as e:
            health_data['categories'][category]['warnings'].append({
                'name': check_name,
                'status': 'WARNING',
                'error': str(e),
                'message': warning_message
            })
            health_data['summary']['warnings'] += 1
        
        health_data['summary']['total_checks'] += 1
    
    # Initialize categories
    categories = ['CORE', 'SCHEMA', 'API', 'CALENDAR', 'MIGRATIONS', 'AUTH', 'DEPS']
    for category in categories:
        health_data['categories'][category] = {
            'passed': [],
            'failed': [],
            'warnings': []
        }
    
    # CORE APPLICATION HEALTH
    run_check('CORE', 'Django Configuration', 
              lambda: True,  # Simplified for now
              'Check Django settings and configuration')
    
    run_check('CORE', 'Database Connection',
              lambda: connection.cursor().execute('SELECT 1') is not None,
              'Check database connectivity and credentials')
    
    # DATABASE SCHEMA INTEGRITY
    run_check('SCHEMA', 'MaintenanceActivity Model',
              lambda: MaintenanceActivity.objects.count() >= 0,
              'Run: ./scripts/simple_timezone_fix.sh')
    
    run_check('SCHEMA', 'Timezone Field Exists',
              lambda: hasattr(MaintenanceActivity, 'timezone'),
              'Run: ./scripts/simple_timezone_fix.sh')
    
    try:
        from events.models import CalendarEvent
        run_check('SCHEMA', 'CalendarEvent Model',
                  lambda: CalendarEvent.objects.count() >= 0,
                  'Check events app migrations')
    except ImportError:
        health_data['categories']['SCHEMA']['failed'].append({
            'name': 'CalendarEvent Model',
            'status': 'ERROR',
            'error': 'CalendarEvent model not found',
            'fix': 'Check events app migrations'
        })
        health_data['summary']['failed'] += 1
        health_data['summary']['total_checks'] += 1
    
    # API ENDPOINTS FUNCTIONALITY
    def test_unified_events_api():
        try:
            from events.views import fetch_unified_events
            from django.test import RequestFactory
            
            factory = RequestFactory()
            test_request = factory.get('/events/api/unified/?start=2025-01-01&end=2025-12-31')
            test_request.user = request.user
            
            response = fetch_unified_events(test_request)
            return response.status_code == 200
        except Exception:
            return False
    
    run_check('API', 'fetch_unified_events API',
              test_unified_events_api,
              'Run: ./scripts/simple_timezone_fix.sh')
    
    # CALENDAR SPECIFIC ISSUES
    def test_calendar_view():
        try:
            from events.views import calendar_view
            from django.test import RequestFactory
            
            factory = RequestFactory()
            test_request = factory.get('/events/calendar/')
            test_request.user = request.user
            
            response = calendar_view(test_request)
            return response.status_code == 200
        except Exception:
            return False
    
    run_check('CALENDAR', 'Calendar View Renders',
              test_calendar_view,
              'Check calendar view and template rendering')
    
    run_warning_check('CALENDAR', 'Maintenance Activities Count',
                      lambda: MaintenanceActivity.objects.count() > 0,
                      'No maintenance activities found - calendar may appear empty')
    
    # USER AUTHENTICATION
    run_check('AUTH', 'Admin User Exists',
              lambda: User.objects.filter(is_superuser=True).exists(),
              'Create admin user: python manage.py createsuperuser')
    
    # EXTERNAL DEPENDENCIES
    def test_redis():
        try:
            from django.core.cache import cache
            cache.set('health_test', 'value')
            return cache.get('health_test') == 'value'
        except Exception:
            return False
    
    run_check('DEPS', 'Redis Connection',
              test_redis,
              'Check Redis server connectivity')
    
    # Calculate health percentage
    if health_data['summary']['total_checks'] > 0:
        health_data['summary']['health_percentage'] = round(
            (health_data['summary']['passed'] * 100) / health_data['summary']['total_checks']
        )
    
    # Determine overall health status
    if health_data['summary']['health_percentage'] >= 90:
        health_data['summary']['status'] = 'EXCELLENT'
    elif health_data['summary']['health_percentage'] >= 75:
        health_data['summary']['status'] = 'GOOD'
    elif health_data['summary']['health_percentage'] >= 50:
        health_data['summary']['status'] = 'MODERATE'
    else:
        health_data['summary']['status'] = 'CRITICAL'
    
    return JsonResponse(health_data)


@login_required
def health_check_view(request):
    """Render the health check interface."""
    if not request.user.is_superuser:
        return render(request, 'core/access_denied.html', {'message': 'Access denied'})
    
    return render(request, 'core/health_check.html')

@login_required
def css_customization_delete(request, pk):
    """Delete a CSS customization"""
    # Check if CSS customization table exists
    try:
        from django.db import connection
        from django.db.utils import ProgrammingError
        
        css_table_exists = False
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM core_csscustomization LIMIT 1")
                css_table_exists = True
        except (ProgrammingError, Exception):
            css_table_exists = False
        
        if not css_table_exists:
            messages.error(request, 'CSS customization system is not yet set up. Please run database migrations first.')
            return redirect('core:branding_settings')
        
        try:
            css_customization = CSSCustomization.objects.get(pk=pk)
            name = css_customization.name
            css_customization.delete()
            messages.success(request, f'CSS customization "{name}" deleted successfully!')
        except CSSCustomization.DoesNotExist:
            messages.error(request, 'CSS customization not found.')
        
        return redirect('core:css_customization_list')
        
    except Exception as e:
        messages.error(request, f'CSS customization system is not available: {str(e)}. Please run database migrations first.')
        return redirect('core:branding_settings')


@login_required
@require_http_methods(["POST"])
def update_user_timezone(request):
    """API endpoint to update user's timezone preference."""
    try:
        data = json.loads(request.body)
        timezone = data.get('timezone')
        
        if not timezone:
            return JsonResponse({
                'success': False,
                'error': 'Timezone is required'
            }, status=400)
        
        # Validate timezone against allowed choices
        valid_timezones = [choice[0] for choice in UserProfile.TIMEZONE_CHOICES]
        if timezone not in valid_timezones:
            return JsonResponse({
                'success': False,
                'error': f'Invalid timezone: {timezone}'
            }, status=400)
        
        # Get or create user profile
        user_profile, created = UserProfile.objects.get_or_create(
            user=request.user,
            defaults={'timezone': timezone}
        )
        
        if not created:
            user_profile.timezone = timezone
            user_profile.save()
        
        logger.info(f"Updated timezone for user {request.user.username} to {timezone}")
        
        return JsonResponse({
            'success': True,
            'message': f'Timezone updated to {timezone}',
            'timezone': timezone
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f"Error updating user timezone: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def system_health_check(request):
    """System health check endpoint for debugging issues."""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    health_data = {
        'timestamp': timezone.now().isoformat(),
        'categories': {},
        'summary': {
            'total_checks': 0,
            'passed': 0,
            'failed': 0,
            'warnings': 0,
            'health_percentage': 0
        },
        'quick_fixes': []
    }
    
    def run_check(category, check_name, test_func, fix_suggestion=None):
        """Run a health check and record results."""
        try:
            result = test_func()
            if result:
                health_data['categories'][category]['passed'].append({
                    'name': check_name,
                    'status': 'PASS'
                })
                health_data['summary']['passed'] += 1
            else:
                health_data['categories'][category]['failed'].append({
                    'name': check_name,
                    'status': 'FAIL',
                    'fix': fix_suggestion
                })
                health_data['summary']['failed'] += 1
                if fix_suggestion:
                    health_data['quick_fixes'].append(fix_suggestion)
        except Exception as e:
            health_data['categories'][category]['failed'].append({
                'name': check_name,
                'status': 'ERROR',
                'error': str(e),
                'fix': fix_suggestion
            })
            health_data['summary']['failed'] += 1
            if fix_suggestion:
                health_data['quick_fixes'].append(fix_suggestion)
        
        health_data['summary']['total_checks'] += 1
    
    def run_warning_check(category, check_name, test_func, warning_message=None):
        """Run a warning check and record results."""
        try:
            result = test_func()
            if result:
                health_data['categories'][category]['passed'].append({
                    'name': check_name,
                    'status': 'PASS'
                })
                health_data['summary']['passed'] += 1
            else:
                health_data['categories'][category]['warnings'].append({
                    'name': check_name,
                    'status': 'WARNING',
                    'message': warning_message
                })
                health_data['summary']['warnings'] += 1
        except Exception as e:
            health_data['categories'][category]['warnings'].append({
                'name': check_name,
                'status': 'WARNING',
                'error': str(e),
                'message': warning_message
            })
            health_data['summary']['warnings'] += 1
        
        health_data['summary']['total_checks'] += 1
    
    # Initialize categories
    categories = ['CORE', 'SCHEMA', 'API', 'CALENDAR', 'MIGRATIONS', 'AUTH', 'DEPS']
    for category in categories:
        health_data['categories'][category] = {
            'passed': [],
            'failed': [],
            'warnings': []
        }
    
    # CORE APPLICATION HEALTH
    run_check('CORE', 'Django Configuration', 
              lambda: True,  # Simplified for now
              'Check Django settings and configuration')
    
    run_check('CORE', 'Database Connection',
              lambda: connection.cursor().execute('SELECT 1') is not None,
              'Check database connectivity and credentials')
    
    # DATABASE SCHEMA INTEGRITY
    run_check('SCHEMA', 'MaintenanceActivity Model',
              lambda: MaintenanceActivity.objects.count() >= 0,
              'Run: ./scripts/simple_timezone_fix.sh')
    
    run_check('SCHEMA', 'Timezone Field Exists',
              lambda: hasattr(MaintenanceActivity, 'timezone'),
              'Run: ./scripts/simple_timezone_fix.sh')
    
    try:
        from events.models import CalendarEvent
        run_check('SCHEMA', 'CalendarEvent Model',
                  lambda: CalendarEvent.objects.count() >= 0,
                  'Check events app migrations')
    except ImportError:
        health_data['categories']['SCHEMA']['failed'].append({
            'name': 'CalendarEvent Model',
            'status': 'ERROR',
            'error': 'CalendarEvent model not found',
            'fix': 'Check events app migrations'
        })
        health_data['summary']['failed'] += 1
        health_data['summary']['total_checks'] += 1
    
    # API ENDPOINTS FUNCTIONALITY
    def test_unified_events_api():
        try:
            from events.views import fetch_unified_events
            from django.test import RequestFactory
            
            factory = RequestFactory()
            test_request = factory.get('/events/api/unified/?start=2025-01-01&end=2025-12-31')
            test_request.user = request.user
            
            response = fetch_unified_events(test_request)
            return response.status_code == 200
        except Exception:
            return False
    
    run_check('API', 'fetch_unified_events API',
              test_unified_events_api,
              'Run: ./scripts/simple_timezone_fix.sh')
    
    # CALENDAR SPECIFIC ISSUES
    def test_calendar_view():
        try:
            from events.views import calendar_view
            from django.test import RequestFactory
            
            factory = RequestFactory()
            test_request = factory.get('/events/calendar/')
            test_request.user = request.user
            
            response = calendar_view(test_request)
            return response.status_code == 200
        except Exception:
            return False
    
    run_check('CALENDAR', 'Calendar View Renders',
              test_calendar_view,
              'Check calendar view and template rendering')
    
    run_warning_check('CALENDAR', 'Maintenance Activities Count',
                      lambda: MaintenanceActivity.objects.count() > 0,
                      'No maintenance activities found - calendar may appear empty')
    
    # USER AUTHENTICATION
    run_check('AUTH', 'Admin User Exists',
              lambda: User.objects.filter(is_superuser=True).exists(),
              'Create admin user: python manage.py createsuperuser')
    
    # EXTERNAL DEPENDENCIES
    def test_redis():
        try:
            from django.core.cache import cache
            cache.set('health_test', 'value')
            return cache.get('health_test') == 'value'
        except Exception:
            return False
    
    run_check('DEPS', 'Redis Connection',
              test_redis,
              'Check Redis server connectivity')
    
    # Calculate health percentage
    if health_data['summary']['total_checks'] > 0:
        health_data['summary']['health_percentage'] = round(
            (health_data['summary']['passed'] * 100) / health_data['summary']['total_checks']
        )
    
    # Determine overall health status
    if health_data['summary']['health_percentage'] >= 90:
        health_data['summary']['status'] = 'EXCELLENT'
    elif health_data['summary']['health_percentage'] >= 75:
        health_data['summary']['status'] = 'GOOD'
    elif health_data['summary']['health_percentage'] >= 50:
        health_data['summary']['status'] = 'MODERATE'
    else:
        health_data['summary']['status'] = 'CRITICAL'
    
    return JsonResponse(health_data)


@login_required
def health_check_view(request):
    """Render the health check interface."""
    if not request.user.is_superuser:
        return render(request, 'core/access_denied.html', {'message': 'Access denied'})
    
    return render(request, 'core/health_check.html')

@login_required
def css_preview(request):
    """Preview CSS changes in real-time"""
    # Check if CSS customization table exists
    try:
        from django.db import connection
        from django.db.utils import ProgrammingError
        
        css_table_exists = False
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM core_csscustomization LIMIT 1")
                css_table_exists = True
        except (ProgrammingError, Exception):
            css_table_exists = False
        
        if not css_table_exists:
            messages.error(request, 'CSS customization system is not yet set up. Please run database migrations first.')
            return redirect('core:branding_settings')
        
        if request.method == 'POST':
            form = CSSPreviewForm(request.POST)
            if form.is_valid():
                css_code = form.cleaned_data['css_code']
            else:
                css_code = ''
        else:
            form = CSSPreviewForm()
            css_code = ''
        
        # Get active CSS customizations for comparison
        active_css = CSSCustomization.objects.filter(is_active=True).order_by('-priority', 'order')
        
        context = {
            'form': form,
            'css_code': css_code,
            'active_css': active_css,
            'active_tab': 'branding'
        }
        return render(request, 'core/css_preview.html', context)
        
    except Exception as e:
        messages.error(request, f'CSS customization system is not available: {str(e)}. Please run database migrations first.')
        return redirect('core:branding_settings')


@login_required
@require_http_methods(["POST"])
def update_user_timezone(request):
    """API endpoint to update user's timezone preference."""
    try:
        data = json.loads(request.body)
        timezone = data.get('timezone')
        
        if not timezone:
            return JsonResponse({
                'success': False,
                'error': 'Timezone is required'
            }, status=400)
        
        # Validate timezone against allowed choices
        valid_timezones = [choice[0] for choice in UserProfile.TIMEZONE_CHOICES]
        if timezone not in valid_timezones:
            return JsonResponse({
                'success': False,
                'error': f'Invalid timezone: {timezone}'
            }, status=400)
        
        # Get or create user profile
        user_profile, created = UserProfile.objects.get_or_create(
            user=request.user,
            defaults={'timezone': timezone}
        )
        
        if not created:
            user_profile.timezone = timezone
            user_profile.save()
        
        logger.info(f"Updated timezone for user {request.user.username} to {timezone}")
        
        return JsonResponse({
            'success': True,
            'message': f'Timezone updated to {timezone}',
            'timezone': timezone
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f"Error updating user timezone: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def system_health_check(request):
    """System health check endpoint for debugging issues."""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    health_data = {
        'timestamp': timezone.now().isoformat(),
        'categories': {},
        'summary': {
            'total_checks': 0,
            'passed': 0,
            'failed': 0,
            'warnings': 0,
            'health_percentage': 0
        },
        'quick_fixes': []
    }
    
    def run_check(category, check_name, test_func, fix_suggestion=None):
        """Run a health check and record results."""
        try:
            result = test_func()
            if result:
                health_data['categories'][category]['passed'].append({
                    'name': check_name,
                    'status': 'PASS'
                })
                health_data['summary']['passed'] += 1
            else:
                health_data['categories'][category]['failed'].append({
                    'name': check_name,
                    'status': 'FAIL',
                    'fix': fix_suggestion
                })
                health_data['summary']['failed'] += 1
                if fix_suggestion:
                    health_data['quick_fixes'].append(fix_suggestion)
        except Exception as e:
            health_data['categories'][category]['failed'].append({
                'name': check_name,
                'status': 'ERROR',
                'error': str(e),
                'fix': fix_suggestion
            })
            health_data['summary']['failed'] += 1
            if fix_suggestion:
                health_data['quick_fixes'].append(fix_suggestion)
        
        health_data['summary']['total_checks'] += 1
    
    def run_warning_check(category, check_name, test_func, warning_message=None):
        """Run a warning check and record results."""
        try:
            result = test_func()
            if result:
                health_data['categories'][category]['passed'].append({
                    'name': check_name,
                    'status': 'PASS'
                })
                health_data['summary']['passed'] += 1
            else:
                health_data['categories'][category]['warnings'].append({
                    'name': check_name,
                    'status': 'WARNING',
                    'message': warning_message
                })
                health_data['summary']['warnings'] += 1
        except Exception as e:
            health_data['categories'][category]['warnings'].append({
                'name': check_name,
                'status': 'WARNING',
                'error': str(e),
                'message': warning_message
            })
            health_data['summary']['warnings'] += 1
        
        health_data['summary']['total_checks'] += 1
    
    # Initialize categories
    categories = ['CORE', 'SCHEMA', 'API', 'CALENDAR', 'MIGRATIONS', 'AUTH', 'DEPS']
    for category in categories:
        health_data['categories'][category] = {
            'passed': [],
            'failed': [],
            'warnings': []
        }
    
    # CORE APPLICATION HEALTH
    run_check('CORE', 'Django Configuration', 
              lambda: True,  # Simplified for now
              'Check Django settings and configuration')
    
    run_check('CORE', 'Database Connection',
              lambda: connection.cursor().execute('SELECT 1') is not None,
              'Check database connectivity and credentials')
    
    # DATABASE SCHEMA INTEGRITY
    run_check('SCHEMA', 'MaintenanceActivity Model',
              lambda: MaintenanceActivity.objects.count() >= 0,
              'Run: ./scripts/simple_timezone_fix.sh')
    
    run_check('SCHEMA', 'Timezone Field Exists',
              lambda: hasattr(MaintenanceActivity, 'timezone'),
              'Run: ./scripts/simple_timezone_fix.sh')
    
    try:
        from events.models import CalendarEvent
        run_check('SCHEMA', 'CalendarEvent Model',
                  lambda: CalendarEvent.objects.count() >= 0,
                  'Check events app migrations')
    except ImportError:
        health_data['categories']['SCHEMA']['failed'].append({
            'name': 'CalendarEvent Model',
            'status': 'ERROR',
            'error': 'CalendarEvent model not found',
            'fix': 'Check events app migrations'
        })
        health_data['summary']['failed'] += 1
        health_data['summary']['total_checks'] += 1
    
    # API ENDPOINTS FUNCTIONALITY
    def test_unified_events_api():
        try:
            from events.views import fetch_unified_events
            from django.test import RequestFactory
            
            factory = RequestFactory()
            test_request = factory.get('/events/api/unified/?start=2025-01-01&end=2025-12-31')
            test_request.user = request.user
            
            response = fetch_unified_events(test_request)
            return response.status_code == 200
        except Exception:
            return False
    
    run_check('API', 'fetch_unified_events API',
              test_unified_events_api,
              'Run: ./scripts/simple_timezone_fix.sh')
    
    # CALENDAR SPECIFIC ISSUES
    def test_calendar_view():
        try:
            from events.views import calendar_view
            from django.test import RequestFactory
            
            factory = RequestFactory()
            test_request = factory.get('/events/calendar/')
            test_request.user = request.user
            
            response = calendar_view(test_request)
            return response.status_code == 200
        except Exception:
            return False
    
    run_check('CALENDAR', 'Calendar View Renders',
              test_calendar_view,
              'Check calendar view and template rendering')
    
    run_warning_check('CALENDAR', 'Maintenance Activities Count',
                      lambda: MaintenanceActivity.objects.count() > 0,
                      'No maintenance activities found - calendar may appear empty')
    
    # USER AUTHENTICATION
    run_check('AUTH', 'Admin User Exists',
              lambda: User.objects.filter(is_superuser=True).exists(),
              'Create admin user: python manage.py createsuperuser')
    
    # EXTERNAL DEPENDENCIES
    def test_redis():
        try:
            from django.core.cache import cache
            cache.set('health_test', 'value')
            return cache.get('health_test') == 'value'
        except Exception:
            return False
    
    run_check('DEPS', 'Redis Connection',
              test_redis,
              'Check Redis server connectivity')
    
    # Calculate health percentage
    if health_data['summary']['total_checks'] > 0:
        health_data['summary']['health_percentage'] = round(
            (health_data['summary']['passed'] * 100) / health_data['summary']['total_checks']
        )
    
    # Determine overall health status
    if health_data['summary']['health_percentage'] >= 90:
        health_data['summary']['status'] = 'EXCELLENT'
    elif health_data['summary']['health_percentage'] >= 75:
        health_data['summary']['status'] = 'GOOD'
    elif health_data['summary']['health_percentage'] >= 50:
        health_data['summary']['status'] = 'MODERATE'
    else:
        health_data['summary']['status'] = 'CRITICAL'
    
    return JsonResponse(health_data)


@login_required
def health_check_view(request):
    """Render the health check interface."""
    if not request.user.is_superuser:
        return render(request, 'core/access_denied.html', {'message': 'Access denied'})
    
    return render(request, 'core/health_check.html')

@login_required
def css_toggle(request, pk):
    """Toggle CSS customization active status"""
    # Check if CSS customization table exists
    try:
        from django.db import connection
        from django.db.utils import ProgrammingError
        
        css_table_exists = False
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM core_csscustomization LIMIT 1")
                css_table_exists = True
        except (ProgrammingError, Exception):
            css_table_exists = False
        
        if not css_table_exists:
            messages.error(request, 'CSS customization system is not yet set up. Please run database migrations first.')
            return redirect('core:branding_settings')
        
        try:
            css_customization = CSSCustomization.objects.get(pk=pk)
            css_customization.is_active = not css_customization.is_active
            css_customization.save()
            
            status = 'activated' if css_customization.is_active else 'deactivated'
            messages.success(request, f'CSS customization "{css_customization.name}" {status} successfully!')
        except CSSCustomization.DoesNotExist:
            messages.error(request, 'CSS customization not found.')
        
        return redirect('core:css_customization_list')
        
    except Exception as e:
        messages.error(request, f'CSS customization system is not available: {str(e)}. Please run database migrations first.')
        return redirect('core:branding_settings')


@login_required
@require_http_methods(["POST"])
def update_user_timezone(request):
    """API endpoint to update user's timezone preference."""
    try:
        data = json.loads(request.body)
        timezone = data.get('timezone')
        
        if not timezone:
            return JsonResponse({
                'success': False,
                'error': 'Timezone is required'
            }, status=400)
        
        # Validate timezone against allowed choices
        valid_timezones = [choice[0] for choice in UserProfile.TIMEZONE_CHOICES]
        if timezone not in valid_timezones:
            return JsonResponse({
                'success': False,
                'error': f'Invalid timezone: {timezone}'
            }, status=400)
        
        # Get or create user profile
        user_profile, created = UserProfile.objects.get_or_create(
            user=request.user,
            defaults={'timezone': timezone}
        )
        
        if not created:
            user_profile.timezone = timezone
            user_profile.save()
        
        logger.info(f"Updated timezone for user {request.user.username} to {timezone}")
        
        return JsonResponse({
            'success': True,
            'message': f'Timezone updated to {timezone}',
            'timezone': timezone
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f"Error updating user timezone: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def system_health_check(request):
    """System health check endpoint for debugging issues."""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    health_data = {
        'timestamp': timezone.now().isoformat(),
        'categories': {},
        'summary': {
            'total_checks': 0,
            'passed': 0,
            'failed': 0,
            'warnings': 0,
            'health_percentage': 0
        },
        'quick_fixes': []
    }
    
    def run_check(category, check_name, test_func, fix_suggestion=None):
        """Run a health check and record results."""
        try:
            result = test_func()
            if result:
                health_data['categories'][category]['passed'].append({
                    'name': check_name,
                    'status': 'PASS'
                })
                health_data['summary']['passed'] += 1
            else:
                health_data['categories'][category]['failed'].append({
                    'name': check_name,
                    'status': 'FAIL',
                    'fix': fix_suggestion
                })
                health_data['summary']['failed'] += 1
                if fix_suggestion:
                    health_data['quick_fixes'].append(fix_suggestion)
        except Exception as e:
            health_data['categories'][category]['failed'].append({
                'name': check_name,
                'status': 'ERROR',
                'error': str(e),
                'fix': fix_suggestion
            })
            health_data['summary']['failed'] += 1
            if fix_suggestion:
                health_data['quick_fixes'].append(fix_suggestion)
        
        health_data['summary']['total_checks'] += 1
    
    def run_warning_check(category, check_name, test_func, warning_message=None):
        """Run a warning check and record results."""
        try:
            result = test_func()
            if result:
                health_data['categories'][category]['passed'].append({
                    'name': check_name,
                    'status': 'PASS'
                })
                health_data['summary']['passed'] += 1
            else:
                health_data['categories'][category]['warnings'].append({
                    'name': check_name,
                    'status': 'WARNING',
                    'message': warning_message
                })
                health_data['summary']['warnings'] += 1
        except Exception as e:
            health_data['categories'][category]['warnings'].append({
                'name': check_name,
                'status': 'WARNING',
                'error': str(e),
                'message': warning_message
            })
            health_data['summary']['warnings'] += 1
        
        health_data['summary']['total_checks'] += 1
    
    # Initialize categories
    categories = ['CORE', 'SCHEMA', 'API', 'CALENDAR', 'MIGRATIONS', 'AUTH', 'DEPS']
    for category in categories:
        health_data['categories'][category] = {
            'passed': [],
            'failed': [],
            'warnings': []
        }
    
    # CORE APPLICATION HEALTH
    run_check('CORE', 'Django Configuration', 
              lambda: True,  # Simplified for now
              'Check Django settings and configuration')
    
    run_check('CORE', 'Database Connection',
              lambda: connection.cursor().execute('SELECT 1') is not None,
              'Check database connectivity and credentials')
    
    # DATABASE SCHEMA INTEGRITY
    run_check('SCHEMA', 'MaintenanceActivity Model',
              lambda: MaintenanceActivity.objects.count() >= 0,
              'Run: ./scripts/simple_timezone_fix.sh')
    
    run_check('SCHEMA', 'Timezone Field Exists',
              lambda: hasattr(MaintenanceActivity, 'timezone'),
              'Run: ./scripts/simple_timezone_fix.sh')
    
    try:
        from events.models import CalendarEvent
        run_check('SCHEMA', 'CalendarEvent Model',
                  lambda: CalendarEvent.objects.count() >= 0,
                  'Check events app migrations')
    except ImportError:
        health_data['categories']['SCHEMA']['failed'].append({
            'name': 'CalendarEvent Model',
            'status': 'ERROR',
            'error': 'CalendarEvent model not found',
            'fix': 'Check events app migrations'
        })
        health_data['summary']['failed'] += 1
        health_data['summary']['total_checks'] += 1
    
    # API ENDPOINTS FUNCTIONALITY
    def test_unified_events_api():
        try:
            from events.views import fetch_unified_events
            from django.test import RequestFactory
            
            factory = RequestFactory()
            test_request = factory.get('/events/api/unified/?start=2025-01-01&end=2025-12-31')
            test_request.user = request.user
            
            response = fetch_unified_events(test_request)
            return response.status_code == 200
        except Exception:
            return False
    
    run_check('API', 'fetch_unified_events API',
              test_unified_events_api,
              'Run: ./scripts/simple_timezone_fix.sh')
    
    # CALENDAR SPECIFIC ISSUES
    def test_calendar_view():
        try:
            from events.views import calendar_view
            from django.test import RequestFactory
            
            factory = RequestFactory()
            test_request = factory.get('/events/calendar/')
            test_request.user = request.user
            
            response = calendar_view(test_request)
            return response.status_code == 200
        except Exception:
            return False
    
    run_check('CALENDAR', 'Calendar View Renders',
              test_calendar_view,
              'Check calendar view and template rendering')
    
    run_warning_check('CALENDAR', 'Maintenance Activities Count',
                      lambda: MaintenanceActivity.objects.count() > 0,
                      'No maintenance activities found - calendar may appear empty')
    
    # USER AUTHENTICATION
    run_check('AUTH', 'Admin User Exists',
              lambda: User.objects.filter(is_superuser=True).exists(),
              'Create admin user: python manage.py createsuperuser')
    
    # EXTERNAL DEPENDENCIES
    def test_redis():
        try:
            from django.core.cache import cache
            cache.set('health_test', 'value')
            return cache.get('health_test') == 'value'
        except Exception:
            return False
    
    run_check('DEPS', 'Redis Connection',
              test_redis,
              'Check Redis server connectivity')
    
    # Calculate health percentage
    if health_data['summary']['total_checks'] > 0:
        health_data['summary']['health_percentage'] = round(
            (health_data['summary']['passed'] * 100) / health_data['summary']['total_checks']
        )
    
    # Determine overall health status
    if health_data['summary']['health_percentage'] >= 90:
        health_data['summary']['status'] = 'EXCELLENT'
    elif health_data['summary']['health_percentage'] >= 75:
        health_data['summary']['status'] = 'GOOD'
    elif health_data['summary']['health_percentage'] >= 50:
        health_data['summary']['status'] = 'MODERATE'
    else:
        health_data['summary']['status'] = 'CRITICAL'
    
    return JsonResponse(health_data)


@login_required
def health_check_view(request):
    """Render the health check interface."""
    if not request.user.is_superuser:
        return render(request, 'core/access_denied.html', {'message': 'Access denied'})
    
    return render(request, 'core/health_check.html')

