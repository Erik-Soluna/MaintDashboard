"""activity_types views (split from the original monolithic views.py)."""
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
def activity_type_list(request):
    """List maintenance activity types."""
    try:
        activity_types = MaintenanceActivityType.objects.filter(is_active=True)
        
        context = {'activity_types': activity_types}
        return render(request, 'maintenance/activity_type_list.html', context)
        
    except Exception as e:
        logger.error(f"Database error in activity_type_list: {str(e)}")
        
        # Try alternative query
        try:
            activity_types = MaintenanceActivityType.objects.all()
            
            context = {
                'activity_types': activity_types,
                'database_error': True,
                'error_message': 'Database schema issue detected. Some functionality may be limited.'
            }
            return render(request, 'maintenance/activity_type_list.html', context)
            
        except Exception as fallback_error:
            logger.error(f"Fallback query also failed: {str(fallback_error)}")
            messages.error(request, 'Database connection issue. Please contact support.')
            return redirect('maintenance:maintenance_list')


@login_required
def add_activity_type(request):
    """Add new maintenance activity type."""
    if request.method == 'POST':
        form = MaintenanceActivityTypeForm(request.POST)
        if form.is_valid():
            activity_type = form.save(commit=False)
            activity_type.created_by = request.user
            activity_type.save()
            form.save_m2m()  # Save many-to-many relationships
            
            messages.success(request, f'Activity type "{activity_type.name}" created successfully!')
            return redirect('maintenance:activity_type_list')
        else:
            # Debug: Log form errors
            print(f"Form errors: {form.errors}")
            print(f"Form data: {request.POST}")
            messages.error(request, f'Error creating activity type. Please check the form.')
    else:
        form = MaintenanceActivityTypeForm()
    
    # Debug: Log form field data
    print(f"Category choices: {list(form.fields['category'].queryset.values_list('name', flat=True))}")
    print(f"Equipment categories: {list(form.fields['applicable_equipment_categories'].queryset.values_list('name', flat=True))}")
    
    context = {'form': form}
    return render(request, 'maintenance/add_activity_type.html', context)


@login_required
def edit_activity_type(request, activity_type_id):
    """Edit maintenance activity type."""
    activity_type = get_object_or_404(MaintenanceActivityType, id=activity_type_id)
    
    if request.method == 'POST':
        form = MaintenanceActivityTypeForm(request.POST, instance=activity_type)
        if form.is_valid():
            activity_type = form.save(commit=False)
            activity_type.updated_by = request.user
            activity_type.save()
            form.save_m2m()  # Save many-to-many relationships
            
            messages.success(request, f'Activity type "{activity_type.name}" updated successfully!')
            return redirect('maintenance:activity_type_list')
        else:
            # Debug: Log form errors
            print(f"Form errors: {form.errors}")
            print(f"Form data: {request.POST}")
            messages.error(request, f'Error updating activity type. Please check the form.')
    else:
        form = MaintenanceActivityTypeForm(instance=activity_type)
    
    context = {
        'form': form,
        'activity_type': activity_type,
    }
    
    return render(request, 'maintenance/edit_activity_type.html', context)


@login_required
def activity_type_categories(request):
    """List activity type categories."""
    categories = ActivityTypeCategory.objects.filter(is_active=True).annotate(
        activity_count=Count('activity_types')
    ).order_by('sort_order', 'name')
    
    context = {
        'categories': categories,
        'page_title': 'Activity Type Categories'
    }
    return render(request, 'maintenance/activity_type_categories.html', context)


@login_required
def add_activity_type_category(request):
    """Add new activity type category."""
    if request.method == 'POST':
        form = ActivityTypeCategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.created_by = request.user
            category.save()
            messages.success(request, f'Activity type category "{category.name}" created successfully!')
            return redirect('maintenance:activity_type_categories')
    else:
        form = ActivityTypeCategoryForm()
    
    context = {
        'form': form,
        'page_title': 'Add Activity Type Category'
    }
    return render(request, 'maintenance/add_activity_type_category.html', context)


@login_required
def edit_activity_type_category(request, category_id):
    """Edit activity type category and manage its activity types."""
    category = get_object_or_404(ActivityTypeCategory, id=category_id)
    
    # Get activity types for this category
    activity_types = MaintenanceActivityType.objects.filter(
        category=category,
        is_active=True
    ).order_by('name')
    
    if request.method == 'POST':
        form = ActivityTypeCategoryForm(request.POST, instance=category)
        if form.is_valid():
            category = form.save(commit=False)
            category.updated_by = request.user
            category.save()
            messages.success(request, f'Activity type category "{category.name}" updated successfully!')
            return redirect('maintenance:activity_type_categories')
    else:
        form = ActivityTypeCategoryForm(instance=category)
    
    context = {
        'form': form,
        'category': category,
        'activity_types': activity_types,
        'page_title': 'Edit Activity Type Category'
    }
    return render(request, 'maintenance/edit_activity_type_category.html', context)


@login_required
def activity_type_templates(request):
    """List activity type templates."""
    templates = ActivityTypeTemplate.objects.filter(is_active=True).select_related(
        'equipment_category', 'category'
    ).order_by('equipment_category__name', 'sort_order', 'name')
    
    equipment_categories = EquipmentCategory.objects.filter(is_active=True)
    
    # Filter by equipment category if specified
    category_filter = request.GET.get('category')
    if category_filter:
        templates = templates.filter(equipment_category_id=category_filter)
    
    context = {
        'templates': templates,
        'equipment_categories': equipment_categories,
        'selected_category': category_filter,
        'page_title': 'Activity Type Templates'
    }
    return render(request, 'maintenance/activity_type_templates.html', context)


@login_required
def add_activity_type_template(request):
    """Add new activity type template."""
    if request.method == 'POST':
        form = ActivityTypeTemplateForm(request.POST)
        if form.is_valid():
            template = form.save(commit=False)
            template.created_by = request.user
            template.save()
            messages.success(request, f'Activity type template "{template.name}" created successfully!')
            return redirect('maintenance:activity_type_templates')
    else:
        form = ActivityTypeTemplateForm()
    
    context = {
        'form': form,
        'page_title': 'Add Activity Type Template'
    }
    return render(request, 'maintenance/add_activity_type_template.html', context)


@login_required
def edit_activity_type_template(request, template_id):
    """Edit activity type template."""
    template = get_object_or_404(ActivityTypeTemplate, id=template_id)
    
    if request.method == 'POST':
        form = ActivityTypeTemplateForm(request.POST, instance=template)
        if form.is_valid():
            template = form.save(commit=False)
            template.updated_by = request.user
            template.save()
            messages.success(request, f'Activity type template "{template.name}" updated successfully!')
            return redirect('maintenance:activity_type_templates')
    else:
        form = ActivityTypeTemplateForm(instance=template)
    
    context = {
        'form': form,
        'template': template,
        'page_title': 'Edit Activity Type Template'
    }
    return render(request, 'maintenance/edit_activity_type_template.html', context)


@login_required
def enhanced_activity_type_list(request):
    """Enhanced activity type list with categories and filtering."""
    activity_types = MaintenanceActivityType.objects.filter(is_active=True).select_related(
        'category', 'template'
    ).prefetch_related('applicable_equipment_categories')
    
    categories = ActivityTypeCategory.objects.filter(is_active=True).order_by('sort_order', 'name')
    
    # Filter by category if specified
    category_filter = request.GET.get('category')
    if category_filter:
        activity_types = activity_types.filter(category_id=category_filter)
    
    # Search functionality
    search_query = request.GET.get('search', '').strip()
    if search_query:
        activity_types = activity_types.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    context = {
        'activity_types': activity_types,
        'categories': categories,
        'selected_category': category_filter,
        'search_query': search_query,
        'page_title': 'Activity Types'
    }
    return render(request, 'maintenance/enhanced_activity_type_list.html', context)


@login_required
def enhanced_add_activity_type(request):
    """Enhanced add activity type with template support."""
    # Check if category is pre-selected
    category_id = request.GET.get('category')
    initial_data = {}
    
    if category_id:
        try:
            category = ActivityTypeCategory.objects.get(id=category_id)
            initial_data['category'] = category
        except ActivityTypeCategory.DoesNotExist:
            pass
    
    if request.method == 'POST':
        form = EnhancedMaintenanceActivityTypeForm(request.POST)
        if form.is_valid():
            activity_type = form.save(commit=False)
            activity_type.created_by = request.user
            activity_type.save()
            form.save_m2m()  # Save many-to-many relationships
            messages.success(request, f'Activity type "{activity_type.name}" created successfully!')
            
            # Redirect back to category if specified
            if category_id:
                return redirect('maintenance:category_activity_types', category_id=category_id)
            return redirect('maintenance:enhanced_activity_type_list')
    else:
        form = EnhancedMaintenanceActivityTypeForm(initial=initial_data)
    
    context = {
        'form': form,
        'page_title': 'Add Activity Type',
        'selected_category_id': category_id
    }
    return render(request, 'maintenance/enhanced_add_activity_type.html', context)


@login_required
def enhanced_edit_activity_type(request, activity_type_id):
    """Enhanced edit activity type."""
    activity_type = get_object_or_404(MaintenanceActivityType, id=activity_type_id)
    
    if request.method == 'POST':
        form = EnhancedMaintenanceActivityTypeForm(request.POST, instance=activity_type)
        if form.is_valid():
            activity_type = form.save(commit=False)
            activity_type.updated_by = request.user
            activity_type.save()
            form.save_m2m()  # Save many-to-many relationships
            messages.success(request, f'Activity type "{activity_type.name}" updated successfully!')
            return redirect('maintenance:enhanced_activity_type_list')
    else:
        form = EnhancedMaintenanceActivityTypeForm(instance=activity_type)
    
    context = {
        'form': form,
        'activity_type': activity_type,
        'page_title': 'Edit Activity Type'
    }
    return render(request, 'maintenance/enhanced_edit_activity_type.html', context)


@login_required
def category_activity_types(request, category_id):
    """Manage activity types within a specific category."""
    category = get_object_or_404(ActivityTypeCategory, id=category_id)
    
    # Get activity types for this category
    activity_types = MaintenanceActivityType.objects.filter(
        category=category,
        is_active=True
    ).prefetch_related('applicable_equipment_categories').order_by('name')
    
    # Search functionality
    search_query = request.GET.get('search', '').strip()
    if search_query:
        activity_types = activity_types.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    context = {
        'category': category,
        'activity_types': activity_types,
        'search_query': search_query,
        'page_title': f'Activity Types - {category.name}'
    }
    return render(request, 'maintenance/category_activity_types.html', context)


@login_required
@require_http_methods(["GET"])
def get_activity_type_templates(request):
    """Get activity type templates for a specific equipment category."""
    equipment_category_id = request.GET.get('equipment_category_id')
    
    if not equipment_category_id:
        return JsonResponse({'templates': []})
    
    templates = ActivityTypeTemplate.objects.filter(
        equipment_category_id=equipment_category_id,
        is_active=True
    ).select_related('category').order_by('sort_order', 'name')
    
    template_data = []
    for template in templates:
        template_data.append({
            'id': template.id,
            'name': template.name,
            'category_id': template.category.id,
            'category_name': template.category.name,
            'description': template.description,
            'estimated_duration_hours': template.estimated_duration_hours,
            'frequency_days': template.frequency_days,
            'is_mandatory': template.is_mandatory,
            'default_tools_required': template.default_tools_required,
            'default_parts_required': template.default_parts_required,
            'default_safety_notes': template.default_safety_notes,
            'checklist_template': template.checklist_template,
        })
    
    return JsonResponse({'templates': template_data})


@login_required
@require_http_methods(["GET"])
def get_template_details(request, template_id):
    """Get details of a specific template."""
    template = get_object_or_404(ActivityTypeTemplate, id=template_id)
    
    template_data = {
        'id': template.id,
        'name': template.name,
        'category_id': template.category.id,
        'category_name': template.category.name,
        'description': template.description,
        'estimated_duration_hours': template.estimated_duration_hours,
        'frequency_days': template.frequency_days,
        'is_mandatory': template.is_mandatory,
        'default_tools_required': template.default_tools_required,
        'default_parts_required': template.default_parts_required,
        'default_safety_notes': template.default_safety_notes,
        'checklist_template': template.checklist_template,
    }
    
    return JsonResponse(template_data)


@login_required
@require_http_methods(["GET"])
def get_activity_type_suggestions(request):
    """Get activity type suggestions based on equipment selection."""
    equipment_id = request.GET.get('equipment_id')
    
    if not equipment_id:
        return JsonResponse({'suggestions': []})
    
    try:
        equipment = Equipment.objects.get(id=equipment_id)
        
        # Get activity types applicable to this equipment's category
        activity_types = MaintenanceActivityType.objects.filter(
            applicable_equipment_categories=equipment.category,
            is_active=True
        ).select_related('category')
        
        suggestions = []
        for activity_type in activity_types:
            suggestions.append({
                'id': activity_type.id,
                'name': activity_type.name,
                'category_name': activity_type.category.name,
                'description': activity_type.description,
                'estimated_duration_hours': activity_type.estimated_duration_hours,
                'frequency_days': activity_type.frequency_days,
                'tools_required': activity_type.tools_required,
                'parts_required': activity_type.parts_required,
                'safety_notes': activity_type.safety_notes,
            })
        
        return JsonResponse({
            'suggestions': suggestions,
            'equipment_category': equipment.category.name if equipment.category else None
        })
    
    except Equipment.DoesNotExist:
        return JsonResponse({'suggestions': []})


@login_required
@require_http_methods(["POST"])
def create_activity_type_from_template(request):
    """Create a new activity type from a template."""
    template_id = request.POST.get('template_id')
    custom_name = request.POST.get('custom_name', '')
    
    if not template_id:
        return JsonResponse({'success': False, 'error': 'Template ID is required'})
    
    try:
        template = ActivityTypeTemplate.objects.get(id=template_id)
        
        # Generate a unique name if not provided
        if not custom_name:
            custom_name = f"{template.name} - {template.equipment_category.name}"
        
        # Check if activity type with this name already exists
        if MaintenanceActivityType.objects.filter(name=custom_name).exists():
            return JsonResponse({
                'success': False, 
                'error': f'Activity type with name "{custom_name}" already exists'
            })
        
        # Create new activity type from template
        activity_type = MaintenanceActivityType.objects.create(
            name=custom_name,
            category=template.category,
            template=template,
            description=template.description,
            estimated_duration_hours=template.estimated_duration_hours,
            frequency_days=template.frequency_days,
            is_mandatory=template.is_mandatory,
            tools_required=template.default_tools_required,
            parts_required=template.default_parts_required,
            safety_notes=template.default_safety_notes,
            created_by=request.user
        )
        
        # Add equipment category association
        activity_type.applicable_equipment_categories.add(template.equipment_category)
        
        return JsonResponse({
            'success': True,
            'activity_type_id': activity_type.id,
            'message': f'Activity type "{activity_type.name}" created successfully!'
        })
        
    except ActivityTypeTemplate.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Template not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


__all__ = ["activity_type_list", "add_activity_type", "edit_activity_type", "activity_type_categories", "add_activity_type_category", "edit_activity_type_category", "activity_type_templates", "add_activity_type_template", "edit_activity_type_template", "enhanced_activity_type_list", "enhanced_add_activity_type", "enhanced_edit_activity_type", "category_activity_types", "get_activity_type_templates", "get_template_details", "get_activity_type_suggestions", "create_activity_type_from_template"]
