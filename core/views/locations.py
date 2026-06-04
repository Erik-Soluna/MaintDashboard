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
        for child in sorted(children_by_loc.get(p.id, []),
                            key=lambda l: (l.grid_row if l.grid_row is not None else 9999,
                                           l.grid_col if l.grid_col is not None else 9999,
                                           natural_sort_key(l.name))):
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

    def assign_cells(rc_list, auto_cols=None):
        """Place items on a uniform grid by (row, col). Explicit cells (both set)
        are honored; the rest auto-fill row-major into free cells. Returns
        (cells, ncols). auto_cols sets the width when nothing is explicitly placed."""
        n = len(rc_list)
        explicit = [(r, c) for (r, c) in rc_list if r is not None and c is not None]
        default_cols = auto_cols or int(math.ceil(math.sqrt(max(1, n))))
        if not explicit:
            ncols = max(1, default_cols)
            return [divmod(i, ncols) for i in range(n)], ncols
        ncols = max([c for (r, c) in explicit] + [default_cols - 1]) + 1
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

    # Uniform POD blocks on a grid: every POD is the same fixed-size block, placed
    # at its (grid_row, grid_col) cell (unplaced PODs auto-fill row-major). MDC tiles
    # flow inside each block via CSS (the block scrolls if needed), so only PODs are
    # positioned here. Empty grid cells are allowed → the map mirrors the site.
    POD_W, POD_H = 250, 210
    auto_cols = max(1, int((canvas_w - PAD) // (POD_W + PAD)))

    # Each block is a real POD plus, if needed, a synthetic "Site-level" block for
    # equipment NOT captured by any POD — attached directly to the site, or under
    # an inactive direct child not shown as a POD. Without this it was invisible.
    blocks = [{'pod': p, 'gr': p.grid_row, 'gc': p.grid_col} for p in pods]

    rendered_loc_ids = set()
    for p in pods:
        rendered_loc_ids.add(p.id)
        stack = [p.id]
        while stack:
            for ch in children_by_loc.get(stack.pop(), []):
                rendered_loc_ids.add(ch.id)
                stack.append(ch.id)
    orphan_eq = [e for e in equipment if e.location_id not in rendered_loc_ids]
    if orphan_eq:
        site_tiles = []
        for g in category_groups(orphan_eq):
            site_tiles.append({'id': None, 'name': g['name'], 'count': g['count'],
                               'counts': g['counts'], 'equipment': g['equipment'],
                               'equipment_groups': [], 'children': []})
        blocks.append({'pod': None, 'gr': None, 'gc': None,
                       'name': 'Site-level', 'tiles': site_tiles})

    cells, ncols = assign_cells([(b['gr'], b['gc']) for b in blocks], auto_cols)
    nrows = max((r for (r, c) in cells), default=0) + 1

    # Center each block within its cell square (split the PAD gutter both sides).
    cx, cy = PAD // 2, PAD // 2
    pods_payload = []
    for b, (r, c) in zip(blocks, cells):
        px = PAD + c * (POD_W + PAD) + cx
        py = PAD + r * (POD_H + PAD) + cy
        if b['pod'] is not None:
            block_id, block_name = b['pod'].id, b['pod'].name
            mdcs_payload = [{
                'id': (loc.id if loc is not None else None),
                'name': node['name'],
                'count': node['count'], 'counts': node['counts'],
                'equipment': node.get('equipment', []),
                'equipment_groups': node.get('equipment_groups', []),
                'children': node.get('children', []),
            } for (loc, node) in build_pod_tiles(b['pod'])]
        else:
            block_id, block_name, mdcs_payload = None, b['name'], b['tiles']
        pods_payload.append({
            'id': block_id, 'name': block_name, 'row': r, 'col': c,
            'x': round(px, 1), 'y': round(py, 1), 'w': POD_W, 'h': POD_H,
            'mdcs': mdcs_payload,
        })

    canvas_w = max(canvas_w, PAD + ncols * (POD_W + PAD))
    canvas_h = max(site.layout_height or 0, PAD + nrows * (POD_H + PAD))
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

    # Flat hierarchical list of locations under the site (for the "move equipment" picker).
    site_locations = []
    if selected_site:
        from core.utils import get_all_descendant_location_ids
        locs = (Location.objects
                .filter(id__in=get_all_descendant_location_ids(selected_site))
                .select_related('parent_location', 'parent_location__parent_location'))

        def _label(loc):
            parts, cur = [], loc
            while cur is not None and cur.id != selected_site.id:
                parts.append(cur.name)
                cur = cur.parent_location
            return ' › '.join(reversed(parts)) or loc.name
        site_locations = sorted(
            ({'id': l.id, 'label': _label(l)} for l in locs),
            key=lambda x: natural_sort_key(x['label']))

    context = {
        'sites': sites,
        'selected_site': selected_site,
        'selected_site_id': str(selected_site.id) if selected_site else '',
        'site_layout_json': json.dumps(site_layout) if site_layout else 'null',
        'can_edit_map': user_has_permission(request.user, 'site_map.write'),
        'can_add_equipment': user_has_permission(request.user, 'equipment.create'),
        'can_edit_equipment': user_has_permission(request.user, 'equipment.edit'),
        'equipment_categories': EquipmentCategory.objects.filter(is_active=True).order_by('name'),
        'site_locations': site_locations,
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


@permission_required('site_map.write')
@require_http_methods(["GET", "POST"])
def import_map_layout(request):
    """CSV for the facility-map grid. GET with ?site_id= exports the site's CURRENT
    layout (so you can edit & re-upload); GET without it returns a blank template.
    POST ingests pod,pod_row,pod_col,mdc,mdc_row,mdc_col and CREATES any missing
    POD/MDC locations under the site, then sets their grid cells. A blank mdc places
    just the POD. Coordinates are 0-based; blank = leave as-is."""
    if request.method == 'GET':
        out = StringIO()
        writer = csv.writer(out)
        writer.writerow(['pod', 'pod_row', 'pod_col', 'mdc', 'mdc_row', 'mdc_col'])
        site = Location.objects.filter(id=request.GET.get('site_id'), is_site=True).first()
        if site:
            # Effective POD cell (grid coords if set, else the auto-placed cell).
            layout = _build_site_layout(site)
            pod_cell = {p['id']: (p.get('row'), p.get('col')) for p in layout.get('pods', [])}
            pods = sorted(Location.objects.filter(parent_location=site),
                          key=lambda l: (l.grid_row if l.grid_row is not None else 9999,
                                         l.grid_col if l.grid_col is not None else 9999,
                                         natural_sort_key(l.name)))
            for pod in pods:
                pr, pc = pod_cell.get(pod.id, (pod.grid_row, pod.grid_col))
                mdcs = sorted(Location.objects.filter(parent_location=pod),
                              key=lambda l: (l.grid_row if l.grid_row is not None else 9999,
                                             l.grid_col if l.grid_col is not None else 9999,
                                             natural_sort_key(l.name)))
                if mdcs:
                    for mdc in mdcs:
                        writer.writerow([pod.name, pr, pc, mdc.name,
                                         mdc.grid_row if mdc.grid_row is not None else '',
                                         mdc.grid_col if mdc.grid_col is not None else ''])
                else:
                    writer.writerow([pod.name, pr, pc, '', '', ''])
            fname = f'map_layout_{site.name}.csv'.replace(' ', '_')
        else:
            # No site -> blank template with a couple of example rows.
            writer.writerow(['POD 1', 0, 0, 'MDC 1', '', ''])
            writer.writerow(['POD 1', 0, 0, 'MDC 2', '', ''])
            writer.writerow(['POD 2', 0, 1, '', '', ''])
            fname = 'map_layout_template.csv'
        resp = HttpResponse(out.getvalue(), content_type='text/csv')
        resp['Content-Disposition'] = f'attachment; filename="{fname}"'
        return resp

    site = get_object_or_404(Location, id=request.POST.get('site_id'), is_site=True)
    upload = request.FILES.get('file')
    if not upload:
        return JsonResponse({'success': False, 'error': 'No CSV file uploaded.'}, status=400)
    try:
        text = upload.read().decode('utf-8-sig')
    except Exception:
        return JsonResponse({'success': False, 'error': 'Could not read the file as UTF-8 text.'}, status=400)

    def norm(k):
        return (k or '').strip().lower().replace(' ', '_')

    def gi(v):
        v = (v or '').strip()
        if not v:
            return None
        try:
            return max(0, int(float(v)))
        except (TypeError, ValueError):
            return None

    pods_created = mdcs_created = positioned = 0
    errors = []
    pod_cache = {}
    reader = csv.DictReader(StringIO(text))
    for i, raw in enumerate(reader, start=2):  # row 1 is the header
        row = {norm(k): (v or '').strip() for k, v in raw.items()}
        pod_name = row.get('pod') or row.get('pod_name')
        if not pod_name:
            errors.append(f'Row {i}: missing "pod".')
            continue
        pod = pod_cache.get(pod_name.lower())
        if pod is None:
            pod, created = Location.objects.get_or_create(
                name=pod_name, parent_location=site,
                defaults={'is_site': False, 'is_active': True})
            pods_created += 1 if created else 0
            pod_cache[pod_name.lower()] = pod
        pr, pc = gi(row.get('pod_row')), gi(row.get('pod_col'))
        if pr is not None and pc is not None and (pod.grid_row, pod.grid_col) != (pr, pc):
            pod.grid_row, pod.grid_col = pr, pc
            pod.save(update_fields=['grid_row', 'grid_col'])
            positioned += 1
        mdc_name = row.get('mdc') or row.get('mdc_name')
        if mdc_name:
            mdc, created = Location.objects.get_or_create(
                name=mdc_name, parent_location=pod,
                defaults={'is_site': False, 'is_active': True})
            mdcs_created += 1 if created else 0
            mr, mc = gi(row.get('mdc_row')), gi(row.get('mdc_col'))
            if mr is not None and mc is not None and (mdc.grid_row, mdc.grid_col) != (mr, mc):
                mdc.grid_row, mdc.grid_col = mr, mc
                mdc.save(update_fields=['grid_row', 'grid_col'])
                positioned += 1

    return JsonResponse({'success': True, 'pods_created': pods_created,
                         'mdcs_created': mdcs_created, 'positioned': positioned,
                         'errors': errors[:50]})


@permission_required('site_map.write')
@require_POST
def add_map_location(request):
    """Create a location/sub-location from the map's right-click menu. JSON:
    {site_id, name, parent_id?, grid_row?, grid_col?}. parent_id defaults to the
    site (a new POD); otherwise it's a child under that POD/MDC. Optional grid
    cell positions a new POD."""
    from core.utils import get_all_descendant_location_ids
    try:
        data = json.loads(request.body or b'{}')
    except (ValueError, TypeError):
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

    name = (data.get('name') or '').strip()
    if not name:
        return JsonResponse({'success': False, 'error': 'A name is required.'}, status=400)
    site = get_object_or_404(Location, id=data.get('site_id'), is_site=True)

    parent_id = data.get('parent_id')
    if parent_id:
        allowed = set(get_all_descendant_location_ids(site, include_inactive=True)) | {site.id}
        try:
            parent_id = int(parent_id)
        except (TypeError, ValueError):
            return JsonResponse({'success': False, 'error': 'Invalid parent.'}, status=400)
        if parent_id not in allowed:
            return JsonResponse({'success': False, 'error': 'Parent is not part of this site.'}, status=400)
        parent = get_object_or_404(Location, id=parent_id)
    else:
        parent = site

    if Location.objects.filter(name=name, parent_location=parent).exists():
        return JsonResponse({'success': False, 'error': f'"{name}" already exists here.'}, status=400)

    def gi(v):
        try:
            return max(0, int(v))
        except (TypeError, ValueError):
            return None

    loc = Location.objects.create(
        name=name, parent_location=parent, is_site=False, is_active=True,
        grid_row=gi(data.get('grid_row')), grid_col=gi(data.get('grid_col')))
    return JsonResponse({'success': True, 'id': loc.id, 'name': loc.name})


@permission_required('equipment.create')
@require_POST
def add_map_equipment(request):
    """Create equipment under a map location (right-click → Add equipment). JSON:
    {site_id, location_id, name, category_id, status?, manufacturer_serial?, asset_tag?}.
    name/serial/asset_tag are unique; blank serial/asset_tag are auto-generated."""
    import uuid
    from core.utils import get_all_descendant_location_ids
    try:
        data = json.loads(request.body or b'{}')
    except (ValueError, TypeError):
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

    name = (data.get('name') or '').strip()
    if not name:
        return JsonResponse({'success': False, 'error': 'Equipment name is required.'}, status=400)
    if Equipment.objects.filter(name=name).exists():
        return JsonResponse({'success': False, 'error': f'Equipment "{name}" already exists.'}, status=400)

    site = get_object_or_404(Location, id=data.get('site_id'), is_site=True)
    allowed = set(get_all_descendant_location_ids(site, include_inactive=True)) | {site.id}
    try:
        loc_id = int(data.get('location_id'))
    except (TypeError, ValueError):
        return JsonResponse({'success': False, 'error': 'Invalid location.'}, status=400)
    if loc_id not in allowed:
        return JsonResponse({'success': False, 'error': 'Location is not part of this site.'}, status=400)
    location = get_object_or_404(Location, id=loc_id)

    category = EquipmentCategory.objects.filter(id=data.get('category_id')).first()
    if not category:
        return JsonResponse({'success': False, 'error': 'A category is required.'}, status=400)

    status = data.get('status') or 'active'
    serial = (data.get('manufacturer_serial') or '').strip() or f'AUTO-{uuid.uuid4().hex[:10].upper()}'
    asset = (data.get('asset_tag') or '').strip() or f'AUTO-{uuid.uuid4().hex[:10].upper()}'
    eq = Equipment.objects.create(
        name=name, category=category, location=location, status=status,
        manufacturer_serial=serial, asset_tag=asset, is_active=True)
    return JsonResponse({'success': True, 'id': eq.id, 'name': eq.name})


@permission_required('equipment.edit')
@require_POST
def move_map_equipment(request):
    """Move equipment to a different location (right-click chip → Move). JSON:
    {site_id, equipment_id, location_id}. Target must be under the site."""
    from core.utils import get_all_descendant_location_ids
    try:
        data = json.loads(request.body or b'{}')
    except (ValueError, TypeError):
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    eq = get_object_or_404(Equipment, id=data.get('equipment_id'))
    site = get_object_or_404(Location, id=data.get('site_id'), is_site=True)
    allowed = set(get_all_descendant_location_ids(site, include_inactive=True)) | {site.id}
    try:
        loc_id = int(data.get('location_id'))
    except (TypeError, ValueError):
        return JsonResponse({'success': False, 'error': 'Invalid location.'}, status=400)
    if loc_id not in allowed:
        return JsonResponse({'success': False, 'error': 'Target location is not part of this site.'}, status=400)
    location = get_object_or_404(Location, id=loc_id)
    eq.location = location
    eq.save(update_fields=['location'])
    return JsonResponse({'success': True, 'name': eq.name, 'location': location.name})


@permission_required('site_map.write')
@require_POST
def remove_map_location(request):
    """Delete a location from the map — only if it holds NO equipment and has no
    child locations (right-click a POD/sub-location → Remove)."""
    try:
        data = json.loads(request.body or b'{}')
    except (ValueError, TypeError):
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    loc = get_object_or_404(Location, id=data.get('location_id'))
    if loc.is_site:
        return JsonResponse({'success': False, 'error': 'Cannot remove a site from the map.'}, status=400)
    if loc.equipment.exists():
        return JsonResponse({'success': False, 'error': f'"{loc.name}" still has equipment — move or remove it first.'}, status=400)
    if loc.child_locations.exists():
        return JsonResponse({'success': False, 'error': f'"{loc.name}" has sub-locations — remove those first.'}, status=400)
    name = loc.name
    loc.delete()
    return JsonResponse({'success': True, 'name': name})


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
        csv_data = csv.reader(StringIO(file_data))
        
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
        csv_data = csv.reader(StringIO(file_data))
        
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
                        if location.equipment.exists():
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


__all__ = ["map_view", "save_map_layout", "import_map_layout", "add_map_location", "add_map_equipment", "move_map_equipment", "remove_map_location", "locations_settings", "locations_api", "location_detail_api", "add_location", "edit_location", "export_sites_csv", "import_sites_csv", "delete_location", "export_locations_csv", "import_locations_csv", "bulk_edit_locations", "bulk_locations_view"]
