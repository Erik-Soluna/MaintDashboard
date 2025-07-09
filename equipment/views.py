"""
Views for equipment management.
Converted and improved from the original web2py controllers.
"""

import json
import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

from .models import Equipment, EquipmentDocument, EquipmentComponent
from core.models import EquipmentCategory, Location
from .forms import EquipmentForm, EquipmentComponentForm, EquipmentDocumentForm

logger = logging.getLogger(__name__)


@login_required
def equipment_list(request):
    """List all equipment with filtering and search."""
    queryset = Equipment.objects.select_related('category', 'location').all()
    
    # Filter by selected site (from session or URL parameter)
    selected_site_id = request.GET.get('site_id') or request.session.get('selected_site_id')
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
            Q(manufacturer__icontains=search_term)
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
    selected_site_id = request.GET.get('site_id') or request.session.get('selected_site_id')
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
    
    context = {
        'equipment': equipment,
        'maintenance_status': maintenance_status,
        'last_maintenance': last_maintenance,
    }
    
    return render(request, 'equipment/equipment_detail.html', context)


@login_required
def add_equipment(request):
    """Add new equipment (improved from original web2py version)."""
    if request.method == 'POST':
        form = EquipmentForm(request.POST, request.FILES)
        if form.is_valid():
            equipment = form.save(commit=False)
            equipment.created_by = request.user
            equipment.updated_by = request.user
            equipment.save()
            
            messages.success(request, f'Equipment "{equipment.name}" added successfully!')
            return redirect('equipment:equipment_detail', equipment_id=equipment.id)
    else:
        form = EquipmentForm()
    
    context = {
        'form': form,
        'categories': EquipmentCategory.objects.filter(is_active=True),
        'locations': Location.objects.filter(is_active=True),
    }
    
    return render(request, 'equipment/add_equipment.html', context)


@login_required
def edit_equipment(request, equipment_id):
    """Edit existing equipment."""
    equipment = get_object_or_404(Equipment, id=equipment_id)
    
    if request.method == 'POST':
        form = EquipmentForm(request.POST, request.FILES, instance=equipment)
        if form.is_valid():
            equipment = form.save(commit=False)
            equipment.updated_by = request.user
            equipment.save()
            
            messages.success(request, f'Equipment "{equipment.name}" updated successfully!')
            return redirect('equipment:equipment_detail', equipment_id=equipment.id)
    else:
        form = EquipmentForm(instance=equipment)
    
    context = {
        'form': form,
        'equipment': equipment,
        'categories': EquipmentCategory.objects.filter(is_active=True),
        'locations': Location.objects.filter(is_active=True),
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
                Q(asset_tag__icontains=search_term)
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
        Q(asset_tag__icontains=search_term)
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