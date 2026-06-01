"""debug views (split from the original monolithic views.py)."""
import logging
import csv
import io
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg
from django.utils import timezone
from datetime import timedelta, datetime
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import render_to_string
import json
from django.db.models.signals import post_save
from django.dispatch import receiver
from ..models import (
    MaintenanceActivity, MaintenanceActivityType, 
    MaintenanceSchedule, MaintenanceChecklist,
    ActivityTypeCategory, ActivityTypeTemplate, MaintenanceReport,
    MaintenanceTimelineEntry
)
from equipment.models import Equipment
from core.models import EquipmentCategory, UserProfile
from equipment.models import Equipment, EquipmentDocument
from ..forms import (
    MaintenanceActivityForm, MaintenanceScheduleForm, 
    MaintenanceActivityTypeForm, EnhancedMaintenanceActivityTypeForm,
    ActivityTypeCategoryForm, ActivityTypeTemplateForm
)
from events.models import CalendarEvent
from ..models import (
    EquipmentCategorySchedule, GlobalSchedule, ScheduleOverride
)
from ..forms import (
    EquipmentCategoryScheduleForm, GlobalScheduleForm, ScheduleOverrideForm
)
from django.contrib.auth.models import User
from core.models import Location
from core.utils import get_all_descendant_location_ids  # noqa: F401
from .helpers import *  # noqa: F401,F403 (shared helpers + globals)


@login_required
def debug_equipment_filtering(request):
    """Debug view to help troubleshoot equipment filtering issues."""
    from core.models import Location
    from equipment.models import Equipment
    from django.db.models import Q
    from django.db import connection
    
    # Get current site selection
    selected_site_id = request.GET.get('site_id')
    if selected_site_id is None:
        selected_site_id = request.session.get('selected_site_id')
    
    # Get all equipment - compare with and without is_active filter
    all_equipment_active = Equipment.objects.filter(is_active=True).select_related('category', 'location', 'location__parent_location')
    all_equipment_total = Equipment.objects.select_related('category', 'location', 'location__parent_location').all()
    all_equipment = all_equipment_active  # Use active for main display
    
    # Get site info
    selected_site = None
    is_all_sites = False
    
    if selected_site_id:
        if selected_site_id == 'all':
            # Handle "All Sites" selection
            is_all_sites = True
        else:
            try:
                selected_site = Location.objects.get(id=selected_site_id, is_site=True)
            except (Location.DoesNotExist, ValueError):
                pass
    else:
        # No site selected, treat as "All Sites"
        is_all_sites = True
    
    # OLD METHOD (one level deep) - for comparison
    old_filtered_equipment = all_equipment
    if selected_site:
        old_filtered_equipment = all_equipment.filter(
            Q(location__parent_location=selected_site) | Q(location=selected_site)
        )
    
    # NEW METHOD (recursive) - what bulk_add_activity uses
    new_filtered_equipment = all_equipment
    location_ids = None
    location_hierarchy_details = []
    if selected_site:
        location_ids = get_all_descendant_location_ids(selected_site, include_inactive=True)
        
        # Get detailed hierarchy information
        def get_location_hierarchy(loc, depth=0):
            """Get full location hierarchy details."""
            children = Location.objects.filter(parent_location_id=loc.id).select_related('parent_location')
            result = {
                'id': loc.id,
                'name': loc.name,
                'is_active': loc.is_active,
                'is_site': loc.is_site,
                'depth': depth,
                'equipment_count': Equipment.objects.filter(location_id=loc.id, is_active=True).count(),
                'children': []
            }
            for child in children:
                result['children'].append(get_location_hierarchy(child, depth + 1))
            return result
        
        location_hierarchy_details = get_location_hierarchy(selected_site)
        new_filtered_equipment = all_equipment.filter(location_id__in=location_ids)
        
        # RAW SQL QUERY to verify what's actually in the database
        with connection.cursor() as cursor:
            # Get all locations that should belong to this site
            cursor.execute("""
                WITH RECURSIVE location_tree AS (
                    SELECT id, name, parent_location_id, is_active, is_site, 0 as depth
                    FROM core_location
                    WHERE id = %s
                    UNION ALL
                    SELECT l.id, l.name, l.parent_location_id, l.is_active, l.is_site, lt.depth + 1
                    FROM core_location l
                    INNER JOIN location_tree lt ON l.parent_location_id = lt.id
                    WHERE lt.depth < 10
                )
                SELECT id, name, parent_location_id, is_active, is_site, depth
                FROM location_tree
                ORDER BY depth, name;
            """, [selected_site.id])
            raw_location_hierarchy = cursor.fetchall()
            
            # Get equipment count per location
            cursor.execute("""
                SELECT l.id, l.name, COUNT(e.id) as equipment_count
                FROM core_location l
                LEFT JOIN equipment_equipment e ON e.location_id = l.id AND e.is_active = true
                WHERE l.id = ANY(%s)
                GROUP BY l.id, l.name
                ORDER BY l.name;
            """, [list(location_ids)])
            equipment_by_location = cursor.fetchall()
            
            # CRITICAL DIAGNOSTIC: Get ALL equipment and their location_ids to see what's actually in the database
            cursor.execute("""
                SELECT e.id, e.name, e.location_id, l.name as location_name, 
                       l.parent_location_id, l.is_active as location_active,
                       CASE WHEN e.location_id = ANY(%s) THEN true ELSE false END as location_in_filter
                FROM equipment_equipment e
                LEFT JOIN core_location l ON e.location_id = l.id
                WHERE e.is_active = true
                ORDER BY e.location_id, e.name;
            """, [list(location_ids)])
            all_equipment_location_check = cursor.fetchall()
            
            # Get equipment that SHOULD be in filter but location_id doesn't match
            cursor.execute("""
                SELECT e.id, e.name, e.location_id, l.name as location_name,
                       l.parent_location_id, 
                       (SELECT name FROM core_location WHERE id = l.parent_location_id) as parent_name
                FROM equipment_equipment e
                LEFT JOIN core_location l ON e.location_id = l.id
                WHERE e.is_active = true
                AND e.location_id IS NOT NULL
                AND e.location_id NOT IN (SELECT unnest(%s::int[]))
                ORDER BY e.name;
            """, [list(location_ids)])
            equipment_not_in_filter = cursor.fetchall()
            
            # CRITICAL: Find equipment in PODs with SAME NAME but different location_id (belongs to other sites)
            # This identifies equipment that might be incorrectly assigned
            cursor.execute("""
                WITH target_pods AS (
                    SELECT id, name, parent_location_id
                    FROM core_location
                    WHERE id = ANY(%s)
                    AND is_site = false
                ),
                all_pods_with_same_name AS (
                    SELECT l.id, l.name, l.parent_location_id, 
                           (SELECT name FROM core_location WHERE id = l.parent_location_id AND is_site = true) as site_name,
                           (SELECT id FROM core_location WHERE id = l.parent_location_id AND is_site = true) as site_id
                    FROM core_location l
                    WHERE l.is_site = false
                    AND l.name IN (SELECT name FROM target_pods)
                )
                SELECT e.id, e.name, e.location_id, 
                       l.name as location_name,
                       l.parent_location_id,
                       apsn.site_name as actual_site_name,
                       apsn.site_id as actual_site_id,
                       tp.name as target_pod_name,
                       tp.id as target_pod_id
                FROM equipment_equipment e
                INNER JOIN all_pods_with_same_name apsn ON e.location_id = apsn.id
                INNER JOIN core_location l ON e.location_id = l.id
                LEFT JOIN target_pods tp ON tp.name = l.name
                WHERE e.is_active = true
                AND apsn.site_id != %s
                AND tp.id IS NOT NULL
                ORDER BY l.name, e.name;
            """, [list(location_ids), selected_site.id])
            equipment_in_duplicate_pods = cursor.fetchall()
            
            # Get ALL equipment with their actual site (using get_site_location logic)
            cursor.execute("""
                SELECT e.id, e.name, e.location_id, l.name as location_name, 
                       l.parent_location_id, l.is_active as location_active,
                       CASE 
                           WHEN l.is_site = true THEN l.id
                           WHEN l.parent_location_id IS NULL THEN NULL
                           ELSE (
                               WITH RECURSIVE find_site AS (
                                   SELECT id, parent_location_id, is_site
                                   FROM core_location
                                   WHERE id = l.parent_location_id
                                   UNION ALL
                                   SELECT loc.id, loc.parent_location_id, loc.is_site
                                   FROM core_location loc
                                   INNER JOIN find_site fs ON loc.id = fs.parent_location_id
                                   WHERE fs.is_site = false AND fs.parent_location_id IS NOT NULL
                               )
                               SELECT id FROM find_site WHERE is_site = true LIMIT 1
                           )
                       END as actual_site_id
                FROM equipment_equipment e
                LEFT JOIN core_location l ON e.location_id = l.id
                WHERE e.is_active = true
                ORDER BY e.name;
            """)
            all_equipment_with_sites = cursor.fetchall()
    else:
        raw_location_hierarchy = []
        equipment_by_location = []
        all_equipment_with_sites = []
    
    # Diagnostic information
    diagnostics = {
        'equipment_with_null_location': all_equipment.filter(location__isnull=True).count(),
        'equipment_with_inactive_location': all_equipment.filter(location__is_active=False).count(),
        'equipment_by_location_status': {},
        'location_hierarchy_depth': {},
    }
    
    # Check equipment location status
    for equipment in all_equipment[:100]:  # Sample first 100
        if equipment.location:
            status = 'active' if equipment.location.is_active else 'inactive'
            diagnostics['equipment_by_location_status'][status] = diagnostics['equipment_by_location_status'].get(status, 0) + 1
            
            # Check hierarchy depth
            depth = 0
            current = equipment.location
            while current and current.parent_location:
                depth += 1
                current = current.parent_location
            max_depth = diagnostics['location_hierarchy_depth'].get('max', 0)
            if depth > max_depth:
                diagnostics['location_hierarchy_depth']['max'] = depth
        else:
            diagnostics['equipment_by_location_status']['null'] = diagnostics['equipment_by_location_status'].get('null', 0) + 1
    
    # Get SQL queries for inspection
    old_query_sql = str(old_filtered_equipment.query) if selected_site else "N/A (all sites)"
    new_query_sql = str(new_filtered_equipment.query) if selected_site else "N/A (all sites)"
    
    # Get all sites
    all_sites = Location.objects.filter(is_site=True)
    
    # Get location IDs if site is selected
    location_ids_list = list(location_ids) if location_ids else []
    
    context = {
        'all_equipment': all_equipment,
        'old_filtered_equipment': old_filtered_equipment,
        'new_filtered_equipment': new_filtered_equipment,
        'selected_site': selected_site,
        'all_sites': all_sites,
        'selected_site_id': selected_site_id,
        'total_equipment': all_equipment.count(),
        'total_equipment_all': all_equipment_total.count(),
        'total_equipment_active': all_equipment_active.count(),
        'old_filtered_count': old_filtered_equipment.count(),
        'new_filtered_count': new_filtered_equipment.count(),
        'location_ids': location_ids_list,
        'diagnostics': diagnostics,
        'old_query_sql': old_query_sql,
        'new_query_sql': new_query_sql,
        'raw_location_hierarchy': raw_location_hierarchy if selected_site else [],
        'equipment_by_location': equipment_by_location if selected_site else [],
        'all_equipment_with_sites': all_equipment_with_sites if selected_site else [],
        'all_equipment_location_check': all_equipment_location_check if selected_site else [],
        'equipment_not_in_filter': equipment_not_in_filter if selected_site else [],
        'equipment_in_duplicate_pods': equipment_in_duplicate_pods if selected_site else [],
        'location_hierarchy_details': location_hierarchy_details if selected_site else None,
    }
    
    return render(request, 'maintenance/debug_equipment_filtering.html', context)


__all__ = ["debug_equipment_filtering"]
