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


__all__ = ["map_view", "locations_settings", "locations_api", "location_detail_api", "add_location", "edit_location", "export_sites_csv", "import_sites_csv", "delete_location", "export_locations_csv", "import_locations_csv", "bulk_edit_locations", "bulk_locations_view"]
