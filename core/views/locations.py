"""locations views (split from the original monolithic views.py)."""
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
from core.rbac import permission_required, user_has_permission


def _auto_grid(count, area_x, area_y, area_w, area_h, pad):
    """Lay `count` items out in a centered grid within the given area.
    Returns a list of (x, y, w, h) rectangles in canvas coordinates."""
    import math
    rects = []
    if count <= 0:
        return rects
    cols = max(1, int(math.ceil(math.sqrt(count))))
    rows = max(1, int(math.ceil(count / cols)))
    cell_w = (area_w - pad * (cols + 1)) / cols
    cell_h = (area_h - pad * (rows + 1)) / rows
    cell_w = max(cell_w, 1)
    cell_h = max(cell_h, 1)
    for i in range(count):
        r, c = divmod(i, cols)
        x = area_x + pad + c * (cell_w + pad)
        y = area_y + pad + r * (cell_h + pad)
        rects.append((round(x, 1), round(y, 1), round(cell_w, 1), round(cell_h, 1)))
    return rects


def _equipment_health(status, open_issues, has_critical_issue, maint):
    """Reduce a piece of equipment to one of five facility-map health levels."""
    if has_critical_issue or maint == 'overdue':
        return 'critical'
    if open_issues > 0 or maint == 'due':
        return 'warning'
    if status == 'maintenance':
        return 'maintenance'
    if status == 'active':
        return 'ok'
    return 'idle'


def _build_site_layout(site):
    """Build the facility floor-plan for one site as a nested hierarchy:
    POD zones -> MDC tiles -> equipment (collapsed behind each MDC).

    POD and MDC zones are positioned from saved layout_* coords when present,
    otherwise auto-flowed so the map is usable before anything is hand-placed.
    Equipment is NOT individually positioned — it flows inside its MDC tile and
    is revealed on click (there can be dozens of PDUs per MDC)."""
    import math
    from equipment.models import Equipment, EquipmentIssue
    from core.utils import get_all_descendant_location_ids

    PAD, HEADER, TILE_W, TILE_H, TPAD = 24, 28, 156, 58, 10
    canvas_w = site.layout_width or 1280

    pods = sorted(
        Location.objects.filter(parent_location=site, is_active=True),
        key=lambda l: natural_sort_key(l.name),
    )
    pod_ids = {p.id for p in pods}

    site_loc_ids = get_all_descendant_location_ids(site, include_inactive=True)
    # Show ALL equipment under the site (matching the equipment list, which does
    # not filter on is_active). Filtering is_active=True here hid equipment that
    # was wrongly deactivated by the old edit bug — visible on the list but not
    # the map. Coloring is driven by operational status, not is_active.
    equipment = list(
        Equipment.objects.filter(location_id__in=site_loc_ids)
        .select_related('location', 'category')
    )
    eq_ids = [e.id for e in equipment]

    issues_by_eq = {}
    for row in (EquipmentIssue.objects
                .filter(equipment_id__in=eq_ids, status__in=['open', 'in_progress'])
                .values('equipment')
                .annotate(total=Count('id'), crit=Count('id', filter=Q(severity='critical')))):
        issues_by_eq[row['equipment']] = (row['total'], row['crit'])

    now = timezone.now()
    soon = now + timedelta(days=14)
    overdue_ids = set(MaintenanceActivity.objects
                      .filter(equipment_id__in=eq_ids, status='overdue')
                      .values_list('equipment_id', flat=True))
    due_ids = set(MaintenanceActivity.objects
                  .filter(equipment_id__in=eq_ids, status__in=['scheduled', 'pending'],
                          scheduled_start__lte=soon)
                  .values_list('equipment_id', flat=True))

    def eq_payload(e):
        total, crit = issues_by_eq.get(e.id, (0, 0))
        maint = 'overdue' if e.id in overdue_ids else ('due' if e.id in due_ids else 'ok')
        health = _equipment_health(e.status, total, crit > 0, maint)
        tip = [e.name, f"Status: {e.get_status_display()}"]
        if total:
            tip.append(f"{total} open issue{'s' if total != 1 else ''}" + (f" ({crit} critical)" if crit else ""))
        if maint == 'overdue':
            tip.append("Maintenance overdue")
        elif maint == 'due':
            tip.append("Maintenance due soon")
        return {'id': e.id, 'name': e.name, 'health': health, 'open_issues': total,
                'tooltip': " • ".join(tip)}

    # Build the location/equipment tree. Each POD's tiles are its direct child
    # locations (MDCs, cabinets, …); within a tile, sub-locations nest recursively
    # to arbitrary depth (POD › MDC › Network Cabinet › switches). Equipment sitting
    # directly on a POD (no sub-location) is bucketed BY CATEGORY into synthetic
    # tiles ("Transformer", "VFD", …) instead of one generic "Unzoned" tile.
    HEALTH_LEVELS = ('critical', 'warning', 'maintenance', 'ok', 'idle')
    eq_by_loc = {}
    for e in equipment:
        eq_by_loc.setdefault(e.location_id, []).append(e)
    children_by_loc = {}
    for loc in Location.objects.filter(id__in=site_loc_ids):
        if loc.parent_location_id:
            children_by_loc.setdefault(loc.parent_location_id, []).append(loc)

    def category_groups(eq_list):
        """Group a flat equipment list into expandable per-category groups
        (Transformer, Switchgear, PDU, …) so types are never mixed/mistaken."""
        buckets = {}
        for e in eq_list:
            cat = e.category
            b = buckets.setdefault(cat.id if cat else None,
                                   {'name': cat.name if cat else 'Uncategorized', 'eq': []})
            b['eq'].append(e)
        groups = []
        for key in sorted(buckets, key=lambda k: natural_sort_key(buckets[k]['name'])):
            b = buckets[key]
            chips = [eq_payload(e) for e in sorted(b['eq'], key=lambda e: natural_sort_key(e.name))]
            counts = {lvl: 0 for lvl in HEALTH_LEVELS}
            for ep in chips:
                counts[ep['health']] += 1
            groups.append({'name': b['name'], 'equipment': chips,
                           'count': len(chips), 'counts': counts})
        return groups

    def build_node(loc):
        """Recursive sub-location node: its direct equipment grouped by category,
        plus nested child locations. Counts aggregate over the whole subtree."""
        eq_groups = category_groups(eq_by_loc.get(loc.id, []))
        kids = [build_node(c) for c in sorted(children_by_loc.get(loc.id, []),
                                              key=lambda l: natural_sort_key(l.name))]
        counts = {lvl: 0 for lvl in HEALTH_LEVELS}
        total = 0
        for g in eq_groups:
            total += g['count']
            for lvl in HEALTH_LEVELS:
                counts[lvl] += g['counts'][lvl]
        for k in kids:
            total += k['count']
            for lvl in HEALTH_LEVELS:
                counts[lvl] += k['counts'][lvl]
        return {'id': loc.id, 'name': loc.name, 'equipment_groups': eq_groups,
                'children': kids, 'count': total, 'counts': counts}

    def build_pod_tiles(p):
        """A POD's tiles: its direct child locations (shown if active or non-empty)
        plus per-category buckets for equipment sitting directly on the POD."""
        tiles = []
        for child in sorted(children_by_loc.get(p.id, []), key=lambda l: natural_sort_key(l.name)):
            node = build_node(child)
            if child.is_active or node['count'] > 0:
                tiles.append((child, node))
        cat_buckets = {}
        for e in sorted(eq_by_loc.get(p.id, []), key=lambda e: natural_sort_key(e.name)):
            cat = e.category
            b = cat_buckets.setdefault(cat.id if cat else None,
                                       {'label': cat.name if cat else 'Uncategorized', 'eq': []})
            b['eq'].append(e)
        for key in sorted(cat_buckets, key=lambda k: natural_sort_key(cat_buckets[k]['label'])):
            b = cat_buckets[key]
            eqs = [eq_payload(e) for e in b['eq']]
            counts = {lvl: 0 for lvl in HEALTH_LEVELS}
            for ep in eqs:
                counts[ep['health']] += 1
            tiles.append((None, {'id': None, 'name': b['label'], 'equipment': eqs,
                                 'children': [], 'count': len(eqs), 'counts': counts}))
        return tiles

    def assign_cells(rc_list):
        """Place items on a grid. Each item is an (row, col) pair where both are set
        (explicit placement) or both None (auto). Explicit cells are honored; the
        rest auto-fill row-major into free cells. Returns (cells, ncols)."""
        n = len(rc_list)
        explicit = [(r, c) for (r, c) in rc_list if r is not None and c is not None]
        if not explicit:
            ncols = max(1, int(math.ceil(math.sqrt(max(1, n)))))
            return [divmod(i, ncols) for i in range(n)], ncols
        ncols = max([c for (r, c) in explicit] + [int(math.ceil(math.sqrt(max(1, n)))) - 1]) + 1
        used = set(explicit)
        cells = [(r, c) if (r is not None and c is not None) else None for (r, c) in rc_list]
        cursor = 0
        for i in range(n):
            if cells[i] is not None:
                continue
            while True:
                rr, cc = divmod(cursor, ncols)
                cursor += 1
                if (rr, cc) not in used:
                    used.add((rr, cc)); cells[i] = (rr, cc); break
        return cells, ncols

    # Pass 1 — per-POD tiles, grid the MDC tiles inside each POD, derive POD size.
    pod_meta = []
    for p in pods:
        tiles = build_pod_tiles(p)
        rc = [((loc.grid_row, loc.grid_col) if loc is not None else (None, None))
              for (loc, node) in tiles]
        cells, ncols = assign_cells(rc)
        nrows = max((r for (r, c) in cells), default=0) + 1
        comp_w = ncols * TILE_W + (ncols + 1) * TPAD
        comp_h = HEADER + nrows * TILE_H + (nrows + 1) * TPAD
        pod_meta.append({'pod': p, 'tiles': tiles, 'cells': cells,
                         'comp_w': comp_w, 'comp_h': comp_h})

    # Pass 2 — position PODs. Grid (table: col widths / row heights sized to content)
    # when any POD has a grid cell; otherwise legacy free-form / auto-flow wrapping.
    pods_have_grid = any(m['pod'].grid_row is not None and m['pod'].grid_col is not None
                         for m in pod_meta)
    pod_pos = {}
    if pods_have_grid:
        cells, ncols = assign_cells([(m['pod'].grid_row, m['pod'].grid_col) for m in pod_meta])
        nrows = max((r for (r, c) in cells), default=0) + 1
        col_w, row_h = [0] * ncols, [0] * nrows
        for m, (r, c) in zip(pod_meta, cells):
            col_w[c] = max(col_w[c], m['comp_w'])
            row_h[r] = max(row_h[r], m['comp_h'])
        col_x, row_y = [PAD] * ncols, [PAD] * nrows
        for c in range(1, ncols):
            col_x[c] = col_x[c - 1] + col_w[c - 1] + PAD
        for r in range(1, nrows):
            row_y[r] = row_y[r - 1] + row_h[r - 1] + PAD
        for m, (r, c) in zip(pod_meta, cells):
            pod_pos[m['pod'].id] = (col_x[c], row_y[r], m['comp_w'], m['comp_h'])
        canvas_h_auto = (row_y[-1] + row_h[-1] + PAD) if nrows else PAD
    else:
        x_cur, y_cur, rh = PAD, PAD, 0
        for m in pod_meta:
            p, comp_w, comp_h = m['pod'], m['comp_w'], m['comp_h']
            if x_cur + comp_w > canvas_w and x_cur > PAD:
                x_cur, y_cur, rh = PAD, y_cur + rh + PAD, 0
            px = p.layout_x if p.layout_x is not None else x_cur
            py = p.layout_y if p.layout_y is not None else y_cur
            pod_pos[p.id] = (px, py, p.layout_width or comp_w, p.layout_height or comp_h)
            x_cur += comp_w + PAD
            rh = max(rh, comp_h)
        canvas_h_auto = y_cur + rh + PAD

    # Pass 3 — payloads, positioning each tile inside its POD.
    pods_payload = []
    for m in pod_meta:
        p = m['pod']
        px, py, pw, ph = pod_pos[p.id]
        mdcs_payload = []
        for (loc, node), (r, c) in zip(m['tiles'], m['cells']):
            tx = px + TPAD + c * (TILE_W + TPAD)
            ty = py + HEADER + TPAD + r * (TILE_H + TPAD)
            # legacy pixel override only for non-grid sites where the MDC has one
            if not pods_have_grid and loc is not None and loc.grid_col is None and loc.layout_x is not None:
                tx, ty = loc.layout_x, loc.layout_y
            tw = (loc.layout_width if loc and loc.layout_width and loc.grid_col is None else TILE_W)
            th = (loc.layout_height if loc and loc.layout_height and loc.grid_row is None else TILE_H)
            mdcs_payload.append({
                # Real location -> its id (draggable/saveable); synthetic category
                # tile -> null id (renders + expands, excluded from layout save).
                'id': (loc.id if loc is not None else None),
                'name': node['name'],
                'x': round(tx, 1), 'y': round(ty, 1), 'w': round(tw, 1), 'h': round(th, 1),
                'count': node['count'], 'counts': node['counts'],
                # Category tiles carry flat 'equipment'; location tiles carry
                # 'equipment_groups' (category groups) + nested 'children'.
                'equipment': node.get('equipment', []),
                'equipment_groups': node.get('equipment_groups', []),
                'children': node.get('children', []),
            })
        pods_payload.append({
            'id': p.id, 'name': p.name,
            'x': round(px, 1), 'y': round(py, 1), 'w': round(pw, 1), 'h': round(ph, 1),
            'mdcs': mdcs_payload,
        })

    canvas_h = site.layout_height or canvas_h_auto
    return {
        'site': {'id': site.id, 'name': site.name, 'width': canvas_w, 'height': canvas_h},
        'pods': pods_payload,
        'equipment_total': len(equipment),
    }


@login_required
def map_view(request):
    """Per-site facility floor-plan map: POD/container zones with equipment placed
    inside, color-coded by status / open issues / maintenance-due. Honors the
    global site selector; falls back to an auto-grid where nothing is hand-placed."""
    sites = sorted(
        Location.objects.filter(is_site=True, is_active=True),
        key=lambda s: natural_sort_key(s.name),
    )

    selected_site_id = request.GET.get('site_id') or request.session.get('selected_site_id')
    selected_site = None
    if selected_site_id and selected_site_id != 'all':
        selected_site = next((s for s in sites if str(s.id) == str(selected_site_id)), None)
    if selected_site is None and sites:
        selected_site = sites[0]

    site_layout = _build_site_layout(selected_site) if selected_site else None

    context = {
        'sites': sites,
        'selected_site': selected_site,
        'selected_site_id': str(selected_site.id) if selected_site else '',
        'site_layout_json': json.dumps(site_layout) if site_layout else 'null',
        'can_edit_map': user_has_permission(request.user, 'site_map.write'),
    }
    return render(request, 'core/map.html', context)


@permission_required('site_map.write')
@require_POST
def save_map_layout(request):
    """Persist facility-map zone positions from the drag editor. Accepts JSON:
    {site_id, canvas:{width,height}, zones:[...]}. Each zone is either a grid
    placement {id, grid_row, grid_col} (preferred) or legacy pixels {id,x,y,w,h}.
    Zones are POD/MDC locations under the site (validated)."""
    from core.utils import get_all_descendant_location_ids
    try:
        data = json.loads(request.body or b'{}')
    except (ValueError, TypeError):
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

    site = get_object_or_404(Location, id=data.get('site_id'), is_site=True)

    def num(v):
        try:
            return round(float(v), 1)
        except (TypeError, ValueError):
            return None

    canvas = data.get('canvas') or {}
    cw, ch = num(canvas.get('width')), num(canvas.get('height'))
    fields = []
    if cw:
        site.layout_width = cw; fields.append('layout_width')
    if ch:
        site.layout_height = ch; fields.append('layout_height')
    if fields:
        site.save(update_fields=fields)

    # Zones are POD/MDC locations under this site. Restrict updates to that set.
    allowed_ids = set(get_all_descendant_location_ids(site, include_inactive=True))
    def grid_int(v):
        try:
            return max(0, int(v))
        except (TypeError, ValueError):
            return None

    zones_saved = 0
    for z in data.get('zones', []):
        try:
            zid = int(z.get('id'))
        except (TypeError, ValueError):
            continue
        if zid not in allowed_ids:
            continue
        if 'grid_row' in z or 'grid_col' in z:
            # Grid placement (preferred): row/col cell on the site/POD grid.
            zones_saved += Location.objects.filter(id=zid).update(
                grid_row=grid_int(z.get('grid_row')), grid_col=grid_int(z.get('grid_col')),
            )
        else:
            # Legacy free-form pixel placement.
            zones_saved += Location.objects.filter(id=zid).update(
                layout_x=num(z.get('x')), layout_y=num(z.get('y')),
                layout_width=num(z.get('w')), layout_height=num(z.get('h')),
            )

    return JsonResponse({'success': True, 'zones_saved': zones_saved})


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

    # MDC-level locations (children of PODs) — targets for the Generate PDUs modal.
    mdc_locations = sorted(
        Location.objects.filter(is_site=False, parent_location__is_site=False, is_active=True)
            .select_related('parent_location', 'parent_location__parent_location'),
        key=lambda l: natural_sort_key(l.get_hierarchical_display()),
    )
    for mdc in mdc_locations:
        site_loc = mdc.get_site_location()
        mdc.site_id = site_loc.id if site_loc else ''

    context = {
        'locations': locations,
        'sites': sites,
        'customers': customers,
        'mdc_locations': mdc_locations,
    }
    return render(request, 'core/locations_settings.html', context)


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


@permission_required('site_map.write')
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


@permission_required('site_map.write')
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


@permission_required('site_map.write')
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


@permission_required('site_map.write')
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


@permission_required('site_map.write')
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
@permission_required('site_map.write')
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


__all__ = ["map_view", "save_map_layout", "locations_settings", "locations_api", "location_detail_api", "add_location", "edit_location", "export_sites_csv", "import_sites_csv", "delete_location", "export_locations_csv", "import_locations_csv", "bulk_edit_locations", "bulk_locations_view"]
