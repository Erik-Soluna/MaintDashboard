"""
Views for equipment management.
Converted and improved from the original web2py controllers.
"""

import json
import logging
import csv
import io
import os
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

import re
from datetime import datetime, timedelta
import mimetypes
try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PyPDF2 = None
    PYPDF2_AVAILABLE = False

from .models import Equipment, EquipmentDocument, EquipmentComponent
from core.models import EquipmentCategory, Location
from maintenance.models import MaintenanceReport
from .forms import EquipmentForm, EquipmentComponentForm, EquipmentDocumentForm

logger = logging.getLogger(__name__)


def create_default_maintenance_schedules(equipment, user):
    """Create default maintenance schedules for imported equipment."""
    from maintenance.models import MaintenanceSchedule, MaintenanceActivityType
    from datetime import date, timedelta
    
    try:
        # Get or create default activity types based on equipment category
        category_name = equipment.category.name.lower() if equipment.category else ''
        
        # Define default maintenance types based on category
        default_schedules = []
        
        if 'transformer' in category_name:
            default_schedules = [
                {'name': 'Annual Inspection', 'frequency': 'annual', 'frequency_days': 365},
                {'name': 'Oil Sampling', 'frequency': 'semi_annual', 'frequency_days': 180},
                {'name': 'Visual Inspection', 'frequency': 'quarterly', 'frequency_days': 90},
            ]
        elif 'protection' in category_name or 'relay' in category_name:
            default_schedules = [
                {'name': 'Annual Testing', 'frequency': 'annual', 'frequency_days': 365},
                {'name': 'Quarterly Inspection', 'frequency': 'quarterly', 'frequency_days': 90},
            ]
        elif 'breaker' in category_name or 'switch' in category_name:
            default_schedules = [
                {'name': 'Annual Maintenance', 'frequency': 'annual', 'frequency_days': 365},
                {'name': 'Semi-Annual Inspection', 'frequency': 'semi_annual', 'frequency_days': 180},
            ]
        else:
            # Generic maintenance for other equipment
            default_schedules = [
                {'name': 'Annual Inspection', 'frequency': 'annual', 'frequency_days': 365},
                {'name': 'Quarterly Check', 'frequency': 'quarterly', 'frequency_days': 90},
            ]
        
        created_schedules = []
        
        for schedule_def in default_schedules:
            # Patch: Always set category when creating MaintenanceActivityType
            if not equipment.category or not equipment.category.activitytypecategory_set.exists():
                logger.error(f"Cannot create MaintenanceActivityType for '{schedule_def['name']}' because equipment category is missing or has no linked ActivityTypeCategory.")
                continue
            # Use the first ActivityTypeCategory as default (or customize as needed)
            activity_type_category = equipment.category.activitytypecategory_set.first()
            activity_type, created = MaintenanceActivityType.objects.get_or_create(
                name=schedule_def['name'],
                category=activity_type_category,
                defaults={
                    'description': f'Default {schedule_def["name"]} for {equipment.category.name if equipment.category else "equipment"}',
                    'estimated_duration_hours': 2,
                    'frequency_days': schedule_def['frequency_days'],
                    'is_mandatory': True,
                    'created_by': user,
                }
            )
            
            # Check if schedule already exists for this equipment and activity type
            existing_schedule = MaintenanceSchedule.objects.filter(
                equipment=equipment,
                activity_type=activity_type
            ).first()
            
            if not existing_schedule:
                # Create maintenance schedule
                schedule = MaintenanceSchedule.objects.create(
                    equipment=equipment,
                    activity_type=activity_type,
                    frequency=schedule_def['frequency'],
                    frequency_days=schedule_def['frequency_days'],
                    start_date=date.today(),
                    auto_generate=True,
                    advance_notice_days=30,
                    created_by=user
                )
                created_schedules.append(schedule)
                logger.info(f"Created maintenance schedule: {schedule_def['name']} for {equipment.name}")
        
        return created_schedules
        
    except Exception as e:
        logger.error(f"Error creating maintenance schedules for equipment {equipment.name}: {str(e)}")
        return []


@login_required
def equipment_list(request):
    """List all equipment with filtering and search."""
    queryset = Equipment.objects.select_related('category', 'location').all()
    
    # Filter by selected site (from session or URL parameter)
    selected_site_id = request.GET.get('site_id')
    if selected_site_id is None:
        selected_site_id = request.session.get('selected_site_id')
    
    if selected_site_id:
        try:
            selected_site = Location.objects.get(id=selected_site_id, is_site=True)
            queryset = queryset.filter(
                Q(location__parent_location=selected_site) | Q(location=selected_site)
            )
        except Location.DoesNotExist:
            pass
    
    # Search functionality
    search_term = request.GET.get('search', '')
    if search_term:
        queryset = queryset.filter(
            Q(name__icontains=search_term) |
            Q(manufacturer_serial__icontains=search_term) |
            Q(asset_tag__icontains=search_term) |
            Q(manufacturer__icontains=search_term) |
            Q(category__name__icontains=search_term) |
            Q(location__name__icontains=search_term) |
            Q(model_number__icontains=search_term)
        )
    
    # Filter by category
    category_id = request.GET.get('category')
    if category_id:
        queryset = queryset.filter(category_id=category_id)
        
    # Filter by location
    location_id = request.GET.get('location')
    if location_id:
        queryset = queryset.filter(location_id=location_id)
    
    # Filter by status
    status = request.GET.get('status')
    if status:
        queryset = queryset.filter(status=status)
    
    # Pagination
    paginator = Paginator(queryset, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_term': search_term,
        'categories': EquipmentCategory.objects.filter(is_active=True),
        'locations': Location.objects.filter(is_active=True),
        'statuses': Equipment.STATUS_CHOICES,
        'selected_category': category_id,
        'selected_location': location_id,
        'selected_status': status,
    }
    
    return render(request, 'equipment/equipment_list.html', context)


@login_required
def manage_equipment(request):
    """
    Equipment management view (replicates original web2py functionality).
    """
    equipment_queryset = Equipment.objects.select_related(
        'category', 'location'
    ).all()
    
    # Filter by selected site (from session or URL parameter)
    selected_site_id = request.GET.get('site_id')
    if selected_site_id is None:
        selected_site_id = request.session.get('selected_site_id')
    
    if selected_site_id:
        try:
            selected_site = Location.objects.get(id=selected_site_id, is_site=True)
            equipment_queryset = equipment_queryset.filter(
                Q(location__parent_location=selected_site) | Q(location=selected_site)
            )
        except Location.DoesNotExist:
            pass
    
    equipment_list = equipment_queryset
    
    # Convert to list of dictionaries for JSON compatibility (like original)
    equipment_data = []
    for eq in equipment_list:
        equipment_data.append({
            'id': eq.id,
            'name': eq.name,
            'category': eq.category.name if eq.category else '',
            'manufacturer_serial': eq.manufacturer_serial,
            'location': eq.location.name if eq.location else '',
            'status': eq.get_status_display(),
            'asset_tag': eq.asset_tag,
        })
    
    context = {
        'equipment_list': equipment_data,
        'fields': ['name', 'category', 'manufacturer_serial', 'location'],
        'field_labels': {
            'name': 'Equipment Name',
            'category': 'Category',
            'manufacturer_serial': 'Serial',
            'location': 'Location'
        },
        'json': json,
    }
    
    return render(request, 'equipment/manage_equipment.html', context)


@login_required
def equipment_detail(request, equipment_id):
    """Display detailed information for specific equipment."""
    equipment = get_object_or_404(
        Equipment.objects.select_related('category', 'location'),
        id=equipment_id
    )
    
    # Get maintenance status (replaces the broken maintenance schedule from original)
    maintenance_status = equipment.get_maintenance_status()
    last_maintenance = equipment.get_last_maintenance_date()
    
    # For AJAX requests, return JSON (like original)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        equipment_data = {
            'id': equipment.id,
            'name': equipment.name,
            'category': equipment.category.name if equipment.category else None,
            'manufacturer_serial': equipment.manufacturer_serial,
            'asset_tag': equipment.asset_tag,
            'location': equipment.location.name if equipment.location else None,
            'status': equipment.get_status_display(),
            'manufacturer': equipment.manufacturer,
            'model_number': equipment.model_number,
            'power_ratings': equipment.power_ratings,
            'trip_setpoints': equipment.trip_setpoints,
            'warranty_details': equipment.warranty_details,
            'installed_upgrades': equipment.installed_upgrades,
            'dga_due_date': equipment.dga_due_date.isoformat() if equipment.dga_due_date else None,
            'next_maintenance_date': equipment.next_maintenance_date.isoformat() if equipment.next_maintenance_date else None,
            'maintenance_status': maintenance_status,
            'last_maintenance': last_maintenance.isoformat() if last_maintenance else None,
        }
        return JsonResponse({'status': 'success', 'equipment': equipment_data})
    
    # Get counts for maintenance reports tab
    completed_count = equipment.maintenance_activities.filter(status='completed').count()
    pending_count = equipment.maintenance_activities.filter(status='pending').count()
    overdue_count = equipment.maintenance_activities.filter(status='overdue').count()
    maintenance_docs_count = equipment.documents.filter(document_type='maintenance').count()
    
    context = {
        'equipment': equipment,
        'maintenance_status': maintenance_status,
        'last_maintenance': last_maintenance,
        'completed_count': completed_count,
        'pending_count': pending_count,
        'overdue_count': overdue_count,
        'maintenance_docs_count': maintenance_docs_count,
    }
    
    return render(request, 'equipment/equipment_detail.html', context)


@login_required
def add_equipment(request):
    """Add new equipment (improved from original web2py version)."""
    if request.method == 'POST':
        form = EquipmentForm(request.POST, request.FILES, request=request)
        if form.is_valid():
            equipment = form.save(commit=False)
            equipment.created_by = request.user
            equipment.updated_by = request.user
            equipment.save()
            
            messages.success(request, f'Equipment "{equipment.name}" added successfully!')
            return redirect('equipment:equipment_detail', equipment_id=equipment.id)
    else:
        form = EquipmentForm(request=request)
    
    # Get selected site and locations for template
    selected_site = None
    if request.session.get('selected_site_id'):
        try:
            selected_site = Location.objects.get(id=request.session['selected_site_id'], is_site=True)
        except Location.DoesNotExist:
            pass
    
    # Get locations for the template
    if selected_site:
        locations = Location.objects.filter(
            parent_location=selected_site,
            is_active=True
        ).select_related('parent_location').prefetch_related('child_locations').order_by('name')
    else:
        locations = Location.objects.filter(
            is_site=False,
            is_active=True
        ).select_related('parent_location').prefetch_related('child_locations').order_by('name')
    
    context = {
        'form': form,
        'categories': EquipmentCategory.objects.filter(is_active=True),
        'locations': locations,
        'selected_site': selected_site,
    }
    
    return render(request, 'equipment/add_equipment.html', context)


@login_required
def edit_equipment(request, equipment_id):
    """Edit existing equipment."""
    equipment = get_object_or_404(Equipment, id=equipment_id)
    
    if request.method == 'POST':
        form = EquipmentForm(request.POST, request.FILES, instance=equipment, request=request)
        if form.is_valid():
            equipment = form.save(commit=False)
            equipment.updated_by = request.user
            equipment.save()
            
            messages.success(request, f'Equipment "{equipment.name}" updated successfully!')
            return redirect('equipment:equipment_detail', equipment_id=equipment.id)
    else:
        form = EquipmentForm(instance=equipment, request=request)
    
    # Get selected site and locations for template
    selected_site = None
    if request.session.get('selected_site_id'):
        try:
            selected_site = Location.objects.get(id=request.session['selected_site_id'], is_site=True)
        except Location.DoesNotExist:
            pass
    
    # Get locations for the template
    if selected_site:
        locations = Location.objects.filter(
            parent_location=selected_site,
            is_active=True
        ).select_related('parent_location').prefetch_related('child_locations').order_by('name')
    else:
        locations = Location.objects.filter(
            is_site=False,
            is_active=True
        ).select_related('parent_location').prefetch_related('child_locations').order_by('name')
    
    context = {
        'form': form,
        'equipment': equipment,
        'categories': EquipmentCategory.objects.filter(is_active=True),
        'locations': locations,
        'selected_site': selected_site,
    }
    
    return render(request, 'equipment/edit_equipment.html', context)


@login_required
@require_http_methods(["POST"])
def delete_equipment(request, equipment_id):
    """Delete equipment (AJAX endpoint)."""
    try:
        equipment = get_object_or_404(Equipment, id=equipment_id)
        equipment_name = equipment.name
        equipment.delete()
        
        return JsonResponse({
            'status': 'success', 
            'message': f'Equipment "{equipment_name}" deleted successfully'
        })
    except Exception as e:
        logger.error(f"Error deleting equipment {equipment_id}: {str(e)}")
        return JsonResponse({
            'status': 'error', 
            'message': f'Error deleting equipment: {str(e)}'
        })


@login_required
def get_equipment_data(request):
    """
    AJAX endpoint to get equipment data with pagination.
    Replicates original web2py functionality.
    """
    try:
        page = int(request.GET.get('page', 1))
        items_per_page = int(request.GET.get('items_per_page', 20))
        search_term = request.GET.get('search_term', '')
        
        # Build query
        queryset = Equipment.objects.select_related('category', 'location')
        if search_term:
            queryset = queryset.filter(
                Q(name__icontains=search_term) |
                Q(manufacturer_serial__icontains=search_term) |
                Q(asset_tag__icontains=search_term) |
                Q(manufacturer__icontains=search_term) |
                Q(category__name__icontains=search_term) |
                Q(location__name__icontains=search_term) |
                Q(model_number__icontains=search_term)
            )
        
        # Pagination
        paginator = Paginator(queryset, items_per_page)
        page_obj = paginator.get_page(page)
        
        # Convert to list format
        equipment_list = []
        for equipment in page_obj:
            equipment_list.append({
                'id': equipment.id,
                'name': equipment.name,
                'category_name': equipment.category.name if equipment.category else '',
                'manufacturer_serial': equipment.manufacturer_serial,
                'location_name': equipment.location.name if equipment.location else '',
                'asset_tag': equipment.asset_tag,
                'status': equipment.get_status_display(),
            })
        
        return JsonResponse({
            'status': 'success',
            'equipment': equipment_list,
            'pagination': {
                'total_records': paginator.count,
                'total_pages': paginator.num_pages,
                'current_page': page_obj.number,
                'items_per_page': items_per_page,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            },
        })
    except Exception as e:
        logger.error(f"Error in get_equipment_data: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f'Failed to retrieve equipment data: {str(e)}',
        })


@login_required
def search_equipment(request):
    """
    Search equipment (AJAX endpoint).
    Replicates original web2py functionality.
    """
    search_term = request.GET.get('search_term')
    if not search_term:
        return JsonResponse({
            'status': 'error', 
            'message': 'No search term provided'
        })
    
    # Search query
    queryset = Equipment.objects.filter(
        Q(name__icontains=search_term) |
        Q(manufacturer_serial__icontains=search_term) |
        Q(asset_tag__icontains=search_term) |
        Q(manufacturer__icontains=search_term) |
        Q(category__name__icontains=search_term) |
        Q(location__name__icontains=search_term) |
        Q(model_number__icontains=search_term)
    ).select_related('category', 'location')
    
    # Convert to list format (like original)
    equipment_list = []
    for equipment in queryset:
        equipment_list.append({
            'id': equipment.id,
            'name': equipment.name,
            'category': equipment.category.name if equipment.category else '',
            'manufacturer_serial': equipment.manufacturer_serial,
            'location': equipment.location.name if equipment.location else '',
            'asset_tag': equipment.asset_tag,
        })
    
    return JsonResponse({
        'status': 'success', 
        'equipment': equipment_list
    })


@login_required
def equipment_components(request, equipment_id):
    """View and manage equipment components."""
    equipment = get_object_or_404(Equipment, id=equipment_id)
    components = equipment.components.all()
    
    context = {
        'equipment': equipment,
        'components': components,
    }
    
    return render(request, 'equipment/equipment_components.html', context)


@login_required
def add_component(request, equipment_id):
    """Add component to equipment."""
    equipment = get_object_or_404(Equipment, id=equipment_id)
    
    if request.method == 'POST':
        form = EquipmentComponentForm(request.POST)
        if form.is_valid():
            component = form.save(commit=False)
            component.equipment = equipment
            component.created_by = request.user
            component.save()
            
            messages.success(request, f'Component "{component.name}" added successfully!')
            return redirect('equipment:equipment_components', equipment_id=equipment.id)
    else:
        form = EquipmentComponentForm()
    
    context = {
        'form': form,
        'equipment': equipment,
    }
    
    return render(request, 'equipment/add_component.html', context)


@login_required
def equipment_documents(request, equipment_id):
    """View and manage equipment documents."""
    equipment = get_object_or_404(Equipment, id=equipment_id)
    documents = equipment.documents.all()
    
    context = {
        'equipment': equipment,
        'documents': documents,
    }
    
    return render(request, 'equipment/equipment_documents.html', context)


@login_required
def add_document(request, equipment_id):
    """Add document to equipment."""
    equipment = get_object_or_404(Equipment, id=equipment_id)
    
    if request.method == 'POST':
        form = EquipmentDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.equipment = equipment
            document.created_by = request.user
            document.save()
            
            messages.success(request, f'Document "{document.title}" added successfully!')
            return redirect('equipment:equipment_documents', equipment_id=equipment.id)
    else:
        form = EquipmentDocumentForm()
    
    context = {
        'form': form,
        'equipment': equipment,
    }
    
    return render(request, 'equipment/add_document.html', context)


@login_required
def import_equipment_csv(request):
    """Import equipment from CSV file."""
    if request.method == 'POST':
        if 'csv_file' not in request.FILES:
            messages.error(request, 'No file uploaded.')
            return redirect('equipment:import_equipment_csv')
        
        csv_file = request.FILES['csv_file']
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Please upload a CSV file.')
            return redirect('equipment:import_equipment_csv')
        
        try:
            file_data = csv_file.read().decode('utf-8')
            io_string = io.StringIO(file_data)
            reader = csv.DictReader(io_string)
            
            created_count = 0
            errors = []
            
            for row_num, row in enumerate(reader, start=2):
                try:
                    # Required fields
                    name = row.get('name', '').strip()
                    category_name = row.get('category', '').strip()
                    manufacturer_serial = row.get('manufacturer_serial', '').strip()
                    asset_tag = row.get('asset_tag', '').strip()
                    location_name = row.get('location', '').strip()
                    
                    if not all([name, category_name, manufacturer_serial, asset_tag, location_name]):
                        errors.append(f"Row {row_num}: Missing required fields")
                        continue
                    
                    # Get or create category
                    category, created = EquipmentCategory.objects.get_or_create(
                        name=category_name,
                        defaults={'created_by': request.user}
                    )
                    
                    # Get or create location
                    location, created = Location.objects.get_or_create(
                        name=location_name,
                        defaults={'created_by': request.user}
                    )
                    
                    # Check if equipment already exists
                    if Equipment.objects.filter(
                        Q(name=name) | Q(manufacturer_serial=manufacturer_serial) | Q(asset_tag=asset_tag)
                    ).exists():
                        errors.append(f"Row {row_num}: Equipment with this name, serial, or asset tag already exists")
                        continue
                    
                    # Create equipment
                    equipment = Equipment.objects.create(
                        name=name,
                        category=category,
                        manufacturer_serial=manufacturer_serial,
                        asset_tag=asset_tag,
                        location=location,
                        manufacturer=row.get('manufacturer', '').strip(),
                        model_number=row.get('model_number', '').strip(),
                        power_ratings=row.get('power_ratings', '').strip(),
                        trip_setpoints=row.get('trip_setpoints', '').strip(),
                        warranty_details=row.get('warranty_details', '').strip(),
                        status=row.get('status', 'active').strip(),
                        created_by=request.user,
                        updated_by=request.user
                    )
                    
                    # Create default maintenance schedules for imported equipment
                    try:
                        schedules_created = create_default_maintenance_schedules(equipment, request.user)
                        if schedules_created:
                            logger.info(f"Created {len(schedules_created)} maintenance schedules for imported equipment: {equipment.name}")
                    except Exception as e:
                        logger.error(f"Error creating maintenance schedules for imported equipment {equipment.name}: {str(e)}")
                    
                    created_count += 1
                    
                except Exception as e:
                    errors.append(f"Row {row_num}: {str(e)}")
                    continue
            
            if created_count > 0:
                messages.success(request, f'Successfully imported {created_count} equipment items.')
            
            if errors:
                error_msg = "Errors occurred during import:\n" + "\n".join(errors[:10])
                if len(errors) > 10:
                    error_msg += f"\n... and {len(errors) - 10} more errors"
                messages.error(request, error_msg)
            
            return redirect('equipment:equipment_list')
            
        except Exception as e:
            messages.error(request, f'Error processing CSV file: {str(e)}')
            return redirect('equipment:import_equipment_csv')
    
    return render(request, 'equipment/import_equipment_csv.html')


@login_required
def import_locations_csv(request):
    """Import locations from CSV file."""
    if request.method == 'POST':
        if 'csv_file' not in request.FILES:
            messages.error(request, 'No file uploaded.')
            return redirect('equipment:import_locations_csv')
        
        csv_file = request.FILES['csv_file']
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Please upload a CSV file.')
            return redirect('equipment:import_locations_csv')
        
        try:
            file_data = csv_file.read().decode('utf-8')
            io_string = io.StringIO(file_data)
            reader = csv.DictReader(io_string)
            
            created_count = 0
            errors = []
            
            for row_num, row in enumerate(reader, start=2):
                try:
                    # Required fields
                    name = row.get('name', '').strip()
                    is_site = row.get('is_site', 'false').strip().lower() == 'true'
                    parent_location_name = row.get('parent_location', '').strip()
                    
                    if not name:
                        errors.append(f"Row {row_num}: Missing location name")
                        continue
                    
                    # Check if location already exists
                    if Location.objects.filter(name=name).exists():
                        errors.append(f"Row {row_num}: Location '{name}' already exists")
                        continue
                    
                    # Get parent location if specified
                    parent_location = None
                    if parent_location_name:
                        try:
                            parent_location = Location.objects.get(name=parent_location_name)
                        except Location.DoesNotExist:
                            errors.append(f"Row {row_num}: Parent location '{parent_location_name}' not found")
                            continue
                    
                    # Create location
                    location = Location.objects.create(
                        name=name,
                        parent_location=parent_location,
                        is_site=is_site,
                        address=row.get('address', '').strip(),
                        latitude=float(row.get('latitude', 0)) if row.get('latitude') else None,
                        longitude=float(row.get('longitude', 0)) if row.get('longitude') else None,
                        created_by=request.user,
                        updated_by=request.user
                    )
                    
                    created_count += 1
                    
                except Exception as e:
                    errors.append(f"Row {row_num}: {str(e)}")
                    continue
            
            if created_count > 0:
                messages.success(request, f'Successfully imported {created_count} locations.')
            
            if errors:
                error_msg = "Errors occurred during import:\n" + "\n".join(errors[:10])
                if len(errors) > 10:
                    error_msg += f"\n... and {len(errors) - 10} more errors"
                messages.error(request, error_msg)
            
            return redirect('core:locations_settings')
            
        except Exception as e:
            messages.error(request, f'Error processing CSV file: {str(e)}')
            return redirect('equipment:import_locations_csv')
    
    return render(request, 'equipment/import_locations_csv.html')


@login_required
def export_equipment_csv(request):
    """Export equipment data to CSV file."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="equipment_export.csv"'
    
    writer = csv.writer(response)
    
    # Write header
    writer.writerow([
        'Name',
        'Category',
        'Manufacturer Serial',
        'Asset Tag',
        'Location',
        'Status',
        'Manufacturer',
        'Model Number',
        'Power Ratings',
        'Trip Setpoints',
        'Warranty Details',
        'Installed Upgrades',
        'DGA Due Date',
        'Next Maintenance Date',
        'Commissioning Date',
        'Warranty Expiry Date',
        'Is Active'
    ])
    
    # Get equipment data
    from .models import Equipment
    equipment_list = Equipment.objects.select_related('category', 'location').all()
    
    # Apply site filter if provided
    site_id = request.GET.get('site_id')
    if site_id:
        from django.db.models import Q
        equipment_list = equipment_list.filter(
            Q(location__parent_location_id=site_id) | Q(location_id=site_id)
        )
    
    # Write data rows
    for equipment in equipment_list:
        writer.writerow([
            equipment.name,
            equipment.category.name if equipment.category else '',
            equipment.manufacturer_serial,
            equipment.asset_tag,
            equipment.location.get_full_path() if equipment.location else '',
            equipment.status,
            equipment.manufacturer,
            equipment.model_number,
            equipment.power_ratings,
            equipment.trip_setpoints,
            equipment.warranty_details,
            equipment.installed_upgrades,
            equipment.dga_due_date.isoformat() if equipment.dga_due_date else '',
            equipment.next_maintenance_date.isoformat() if equipment.next_maintenance_date else '',
            equipment.commissioning_date.isoformat() if equipment.commissioning_date else '',
            equipment.warranty_expiry_date.isoformat() if equipment.warranty_expiry_date else '',
            equipment.is_active
        ])
    
    return response


@login_required
@require_http_methods(["POST"])
def import_equipment_csv(request):
    """Import equipment data from CSV file."""
    if 'csv_file' not in request.FILES:
        messages.error(request, 'No CSV file provided.')
        return redirect('equipment:equipment_list')
    
    csv_file = request.FILES['csv_file']
    
    if not csv_file.name.endswith('.csv'):
        messages.error(request, 'Please upload a CSV file.')
        return redirect('equipment:equipment_list')
    
    try:
        # Read CSV file
        file_data = csv_file.read().decode('utf-8')
        csv_data = csv.reader(io.StringIO(file_data))
        
        # Skip header row
        header = next(csv_data)
        
        # Import data
        from .models import Equipment
        from core.models import EquipmentCategory, Location
        from datetime import datetime
        
        imported_count = 0
        error_count = 0
        
        for row_num, row in enumerate(csv_data, start=2):
            try:
                if len(row) < 3:  # Must have at least name, category, and serial
                    continue
                
                name = row[0].strip()
                category_name = row[1].strip()
                manufacturer_serial = row[2].strip()
                asset_tag = row[3].strip() if len(row) > 3 else ''
                location_path = row[4].strip() if len(row) > 4 else ''
                status = row[5].strip() if len(row) > 5 else 'active'
                
                if not name or not manufacturer_serial:
                    continue
                
                # Get or create category
                category = None
                if category_name:
                    category, created = EquipmentCategory.objects.get_or_create(
                        name=category_name,
                        defaults={'description': f'Imported category: {category_name}'}
                    )
                
                # Find location by path
                location = None
                if location_path:
                    # Try to find location by full path
                    for loc in Location.objects.all():
                        if loc.get_full_path() == location_path:
                            location = loc
                            break
                
                # Check if equipment already exists
                if Equipment.objects.filter(manufacturer_serial=manufacturer_serial).exists():
                    error_count += 1
                    continue
                
                # Create equipment
                equipment_data = {
                    'name': name,
                    'category': category,
                    'manufacturer_serial': manufacturer_serial,
                    'asset_tag': asset_tag or f'AUTO_{manufacturer_serial}',
                    'location': location,
                    'status': status if status in ['active', 'inactive', 'maintenance', 'retired'] else 'active',
                    'manufacturer': row[6].strip() if len(row) > 6 else '',
                    'model_number': row[7].strip() if len(row) > 7 else '',
                    'power_ratings': row[8].strip() if len(row) > 8 else '',
                    'trip_setpoints': row[9].strip() if len(row) > 9 else '',
                    'warranty_details': row[10].strip() if len(row) > 10 else '',
                    'installed_upgrades': row[11].strip() if len(row) > 11 else '',
                    'is_active': True if len(row) <= 16 else str(row[16]).lower() in ['true', '1', 'yes'],
                    'created_by': request.user
                }
                
                # Parse dates
                date_fields = [
                    ('dga_due_date', 12),
                    ('next_maintenance_date', 13),
                    ('commissioning_date', 14),
                    ('warranty_expiry_date', 15)
                ]
                
                for field_name, index in date_fields:
                    if len(row) > index and row[index].strip():
                        try:
                            equipment_data[field_name] = datetime.fromisoformat(row[index].strip()).date()
                        except ValueError:
                            pass  # Skip invalid dates
                
                Equipment.objects.create(**equipment_data)
                imported_count += 1
                
            except Exception as e:
                error_count += 1
                print(f"Error importing row {row_num}: {str(e)}")
                continue
        
        if imported_count > 0:
            messages.success(request, f'Successfully imported {imported_count} equipment items.')
        if error_count > 0:
            messages.warning(request, f'{error_count} rows had errors and were skipped.')
            
    except Exception as e:
        messages.error(request, f'Error reading CSV file: {str(e)}')
    
    return redirect('equipment:equipment_list')


@login_required
def export_locations_csv(request):
    """Export locations to CSV file."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="locations_export.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'name', 'parent_location', 'is_site', 'address', 'latitude', 'longitude'
    ])
    
    locations = Location.objects.all()
    for location in locations:
        writer.writerow([
            location.name,
            location.parent_location.name if location.parent_location else '',
            location.is_site,
            location.address,
            location.latitude,
            location.longitude
        ])
    
    return response


@login_required
@require_http_methods(["POST"])
def scan_reports(request, equipment_id):
    """Scan maintenance reports for issues and extract findings."""
    logger.info(f"Starting scan_reports for equipment_id: {equipment_id}")
    
    try:
        equipment = get_object_or_404(Equipment, id=equipment_id)
        logger.info(f"Found equipment: {equipment.name} (ID: {equipment.id})")
        
        # Get maintenance reports for this equipment
        maintenance_reports = MaintenanceReport.objects.filter(
            maintenance_activity__equipment=equipment
        ).select_related('maintenance_activity', 'created_by')
        
        documents_scanned = maintenance_reports.count()
        logger.info(f"Found {documents_scanned} maintenance reports for equipment {equipment.name}")
        
        findings = []
        processed_files = 0
        failed_files = 0
        
        for report in maintenance_reports:
            logger.info(f"Processing maintenance report: {report.title}")
            if not report.file or not report.file.path:
                logger.warning(f"Report {report.title} has no file attached or path, skipping")
                failed_files += 1
                continue
            try:
                import os
                if not os.path.exists(report.file.path):
                    logger.error(f"File does not exist: {report.file.path}")
                    failed_files += 1
                    continue
                if not os.access(report.file.path, os.R_OK):
                    logger.error(f"Cannot read file due to permissions: {report.file.path}")
                    failed_files += 1
                    continue
                text_content = extract_text_from_file(report.file.path)
                logger.info(f"Successfully extracted {len(text_content)} characters from {report.title}")
                if not text_content.strip():
                    logger.warning(f"Extracted text is empty for {report.title}")
                    failed_files += 1
                    continue
                
                # Generate summary from content
                summary_lines = '\n'.join(text_content.strip().splitlines()[:5])
                
                # Status detection based on content
                status = 'unknown'
                status_keywords = {
                    'ok': ['ok', 'normal', 'no critical', 'no issues', 'no problems', 'pass', 'satisfactory'],
                    'warning': ['warning', 'caution', 'monitor', 'attention', 'observe'],
                    'critical': ['critical', 'fault', 'failure', 'issue', 'problem', 'error', 'defect', 'broken'],
                }
                text_lower = text_content.lower()
                if any(k in text_lower for k in status_keywords['critical']):
                    status = 'critical'
                elif any(k in text_lower for k in status_keywords['warning']):
                    status = 'warning'
                elif any(k in text_lower for k in status_keywords['ok']):
                    status = 'ok'
                
                findings.append({
                    'document': report.title,
                    'type': 'Maintenance Report',
                    'status': status,
                    'summary': summary_lines,
                    'report_type': report.get_report_type_display(),
                    'activity_title': report.maintenance_activity.title,
                    'activity_status': report.maintenance_activity.get_status_display(),
                    'findings_summary': report.findings_summary,
                    'report_status': report.get_status_display(),
                    'created_by': report.created_by.get_full_name() if report.created_by else 'Unknown',
                    'created_at': report.created_at.strftime('%Y-%m-%d %H:%M') if report.created_at else '',
                    'approved_by': report.approved_by.get_full_name() if report.approved_by else None,
                    'approved_at': report.approved_at.strftime('%Y-%m-%d %H:%M') if report.approved_at else '',
                })
                processed_files += 1
            except Exception as e:
                logger.error(f"Error processing report {report.title}: {str(e)}", exc_info=True)
                failed_files += 1
                continue
        
        logger.info(f"Scan completed. Processed: {processed_files}, Failed: {failed_files}, Total findings: {len(findings)}")
        return JsonResponse({
            'status': 'success',
            'documents_scanned': documents_scanned,
            'documents_processed': processed_files,
            'documents_failed': failed_files,
            'findings': findings
        })
    except Exception as e:
        logger.error(f"Error in scan_reports for equipment_id {equipment_id}: {str(e)}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def analyze_reports(request, equipment_id):
    """Perform detailed analysis of maintenance reports and generate insights."""
    try:
        equipment = get_object_or_404(Equipment, id=equipment_id)
        
        # Get maintenance activities for trends
        activities = equipment.maintenance_activities.all()
        
        # Generate maintenance trends (last 12 months)
        trends = generate_maintenance_trends(activities)
        
        # Analyze maintenance patterns
        analysis = analyze_maintenance_patterns(activities)
        
        # Generate insights
        insights = generate_maintenance_insights(equipment, activities)
        
        return JsonResponse({
            'status': 'success',
            'analysis': analysis,
            'insights': insights,
            'trends': trends
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


def extract_text_from_file(file_path):
    """Extract text from uploaded file (supports .txt and .pdf)."""
    logger.info(f"Attempting to extract text from file: {file_path}")
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.pdf' and PYPDF2_AVAILABLE:
        try:
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = ''
                for page in reader.pages:
                    text += page.extract_text() or ''
                logger.info(f"Extracted {len(text)} characters from PDF file {file_path}")
                return text
        except Exception as e:
            logger.error(f"Failed to extract text from PDF: {file_path}: {str(e)}")
            return ''
    elif ext == '.pdf' and not PYPDF2_AVAILABLE:
        logger.warning(f"PyPDF2 not available - cannot extract text from PDF: {file_path}")
        return ''
    # Fallback to text extraction for .txt and others
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            logger.info(f"Successfully read {len(content)} characters using UTF-8 encoding")
            return content
    except UnicodeDecodeError as e:
        logger.warning(f"UTF-8 decode failed for {file_path}: {str(e)}")
        try:
            with open(file_path, 'r', encoding='latin-1') as f:
                content = f.read()
                logger.info(f"Successfully read {len(content)} characters using latin-1 encoding")
                return content
        except Exception as e2:
            logger.error(f"Latin-1 decode also failed for {file_path}: {str(e2)}")
            return ''
    except FileNotFoundError as e:
        logger.error(f"File not found: {file_path} - {str(e)}")
        return ''
    except PermissionError as e:
        logger.error(f"Permission denied reading file: {file_path} - {str(e)}")
        return ''
    except Exception as e:
        logger.error(f"Unexpected error reading file {file_path}: {str(e)}")
        return ''


def generate_maintenance_trends(activities):
    """Generate maintenance activity trends over time."""
    # Get last 12 months
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    # Group activities by month
    monthly_data = {}
    for activity in activities.filter(scheduled_start__gte=start_date):
        month_key = activity.scheduled_start.strftime('%Y-%m')
        if month_key not in monthly_data:
            monthly_data[month_key] = 0
        monthly_data[month_key] += 1
    
    # Create labels and data for chart
    labels = []
    data = []
    
    current_date = start_date
    while current_date <= end_date:
        month_key = current_date.strftime('%Y-%m')
        labels.append(current_date.strftime('%b %Y'))
        data.append(monthly_data.get(month_key, 0))
        current_date = current_date.replace(day=1) + timedelta(days=32)
        current_date = current_date.replace(day=1)
    
    return {
        'labels': labels,
        'data': data
    }


def analyze_maintenance_patterns(activities):
    """Analyze maintenance activity patterns."""
    findings = []
    
    # Analyze completion rates
    total_activities = activities.count()
    completed_activities = activities.filter(status='completed').count()
    if total_activities > 0:
        completion_rate = (completed_activities / total_activities) * 100
        findings.append({
            'type': 'Completion Rate',
            'description': f'{completion_rate:.1f}% of maintenance activities are completed on time',
            'confidence': min(completion_rate, 100)
        })
    
    # Analyze overdue activities
    overdue_activities = activities.filter(status='overdue').count()
    if overdue_activities > 0:
        findings.append({
            'type': 'Overdue Activities',
            'description': f'{overdue_activities} maintenance activities are overdue',
            'confidence': 90
        })
    
    # Analyze activity types
    activity_types = activities.values('activity_type__name').annotate(
        count=Count('id')
    ).order_by('-count')[:3]
    
    if activity_types:
        most_common = activity_types[0]
        findings.append({
            'type': 'Most Common Activity',
            'description': f'Most frequent maintenance type: {most_common["activity_type__name"]} ({most_common["count"]} times)',
            'confidence': 85
        })
    
    return {'findings': findings}


def generate_maintenance_insights(equipment, activities):
    """Generate actionable insights from maintenance data."""
    insights = []
    
    # Check for overdue activities
    overdue_count = activities.filter(status='overdue').count()
    if overdue_count > 0:
        insights.append(f"⚠️ {overdue_count} maintenance activities are overdue and require immediate attention")
    
    # Check maintenance frequency
    recent_activities = activities.filter(
        scheduled_start__gte=datetime.now() - timedelta(days=30)
    ).count()
    
    if recent_activities == 0:
        insights.append("📅 No maintenance activities scheduled in the last 30 days")
    elif recent_activities > 5:
        insights.append("⚡ High maintenance activity - consider reviewing maintenance schedule")
    
    # Check equipment age
    if equipment.commissioning_date:
        age_years = (datetime.now().date() - equipment.commissioning_date).days / 365
        if age_years > 10:
            insights.append("🔧 Equipment is over 10 years old - consider replacement planning")
    
    # Check warranty status
    if equipment.warranty_expiry_date and equipment.warranty_expiry_date < datetime.now().date():
        insights.append("📋 Warranty has expired - consider extended warranty options")
    
    return insights