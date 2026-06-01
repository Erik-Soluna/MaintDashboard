"""equipment_settings views (split from the original monolithic views.py)."""
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
@user_passes_test(is_staff_or_superuser)
def equipment_items_settings(request):
    """Equipment items management view."""
    equipment_items = Equipment.objects.select_related('location', 'category').order_by('name')
    # Show all categories (including inactive) so admins can edit them
    categories = EquipmentCategory.objects.all().order_by('name')
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
@user_passes_test(lambda u: u.is_staff or u.has_perm('equipment.change_equipmentcategoryfield'))
def custom_fields_management(request):
    """
    User-friendly custom fields management page.
    Replaces the admin interface for managing EquipmentCategoryField.
    """
    from equipment.models import EquipmentCategoryField, EquipmentCategory
    from django.db import transaction
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'create_field':
            try:
                with transaction.atomic():
                    category_id = request.POST.get('category_id')
                    name = request.POST.get('name', '').strip()
                    label = request.POST.get('label', '').strip()
                    field_type = request.POST.get('field_type', 'text')
                    required = request.POST.get('required') == 'on'
                    help_text = request.POST.get('help_text', '').strip()
                    default_value = request.POST.get('default_value', '').strip()
                    choices = request.POST.get('choices', '').strip()
                    field_group = request.POST.get('field_group', 'General').strip()
                    sort_order = int(request.POST.get('sort_order', 0) or 0)
                    min_value = request.POST.get('min_value', '').strip() or None
                    max_value = request.POST.get('max_value', '').strip() or None
                    max_length = request.POST.get('max_length', '').strip() or None
                    
                    category = EquipmentCategory.objects.get(id=category_id)
                    
                    # Validation
                    if not name or not label:
                        messages.error(request, 'Name and label are required.')
                        return redirect('core:custom_fields_management')
                    
                    # Check for duplicate names
                    if EquipmentCategoryField.objects.filter(category=category, name=name).exists():
                        messages.error(request, f'A field with name "{name}" already exists in this category.')
                        return redirect('core:custom_fields_management')
                    
                    # Create the field
                    field = EquipmentCategoryField.objects.create(
                        category=category,
                        name=name,
                        label=label,
                        field_type=field_type,
                        required=required,
                        help_text=help_text,
                        default_value=default_value,
                        choices=choices,
                        field_group=field_group,
                        sort_order=sort_order,
                        min_value=float(min_value) if min_value else None,
                        max_value=float(max_value) if max_value else None,
                        max_length=int(max_length) if max_length else None,
                        created_by=request.user,
                        updated_by=request.user
                    )
                    
                    messages.success(request, f'Field "{label}" created successfully for category "{category.name}".')
            except Exception as e:
                messages.error(request, f'Error creating field: {str(e)}')
        
        elif action == 'update_field':
            try:
                with transaction.atomic():
                    field_id = request.POST.get('field_id')
                    field = get_object_or_404(EquipmentCategoryField, id=field_id)
                    
                    name = request.POST.get('name', '').strip()
                    label = request.POST.get('label', '').strip()
                    field_type = request.POST.get('field_type', 'text')
                    required = request.POST.get('required') == 'on'
                    help_text = request.POST.get('help_text', '').strip()
                    default_value = request.POST.get('default_value', '').strip()
                    choices = request.POST.get('choices', '').strip()
                    field_group = request.POST.get('field_group', 'General').strip()
                    sort_order = int(request.POST.get('sort_order', 0) or 0)
                    min_value = request.POST.get('min_value', '').strip() or None
                    max_value = request.POST.get('max_value', '').strip() or None
                    max_length = request.POST.get('max_length', '').strip() or None
                    is_active = request.POST.get('is_active') == 'on'
                    
                    # Validation
                    if not name or not label:
                        messages.error(request, 'Name and label are required.')
                        return redirect('core:custom_fields_management')
                    
                    # Check for duplicate names (excluding current field)
                    if EquipmentCategoryField.objects.filter(
                        category=field.category, name=name
                    ).exclude(id=field_id).exists():
                        messages.error(request, f'A field with name "{name}" already exists in this category.')
                        return redirect('core:custom_fields_management')
                    
                    # Update the field
                    field.name = name
                    field.label = label
                    field.field_type = field_type
                    field.required = required
                    field.help_text = help_text
                    field.default_value = default_value
                    field.choices = choices
                    field.field_group = field_group
                    field.sort_order = sort_order
                    field.min_value = float(min_value) if min_value else None
                    field.max_value = float(max_value) if max_value else None
                    field.max_length = int(max_length) if max_length else None
                    field.is_active = is_active
                    field.updated_by = request.user
                    field.save()
                    
                    messages.success(request, f'Field "{label}" updated successfully.')
            except Exception as e:
                messages.error(request, f'Error updating field: {str(e)}')
        
        elif action == 'delete_field':
            try:
                field_id = request.POST.get('field_id')
                field = get_object_or_404(EquipmentCategoryField, id=field_id)
                field_label = field.label
                field.delete()
                messages.success(request, f'Field "{field_label}" deleted successfully.')
            except Exception as e:
                messages.error(request, f'Error deleting field: {str(e)}')
        
        elif action == 'toggle_field':
            try:
                field_id = request.POST.get('field_id')
                field = get_object_or_404(EquipmentCategoryField, id=field_id)
                field.is_active = not field.is_active
                field.save()
                status = 'enabled' if field.is_active else 'disabled'
                messages.success(request, f'Field "{field.label}" {status}.')
            except Exception as e:
                messages.error(request, f'Error toggling field: {str(e)}')
        
        return redirect('core:custom_fields_management')
    
    # Get all categories with their custom fields
    categories = EquipmentCategory.objects.filter(is_active=True).prefetch_related(
        'custom_fields'
    ).order_by('name')
    
    # Group fields by category
    categories_with_fields = []
    for category in categories:
        fields = category.custom_fields.all().order_by('sort_order', 'label')
        categories_with_fields.append({
            'category': category,
            'fields': fields,
            'field_count': fields.count(),
            'active_field_count': fields.filter(is_active=True).count(),
        })
    
    context = {
        'categories_with_fields': categories_with_fields,
        'field_types': EquipmentCategoryField.FIELD_TYPE_CHOICES,
    }
    
    return render(request, 'core/custom_fields_management.html', context)


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
def edit_equipment_category_ajax(request, category_id):
    """AJAX endpoint for editing equipment category via modal."""
    from django.http import JsonResponse
    
    category = get_object_or_404(EquipmentCategory, id=category_id)
    
    if request.method == 'GET':
        # Return category data as JSON
        return JsonResponse({
            'id': category.id,
            'name': category.name,
            'description': category.description or '',
            'is_active': category.is_active,
        })
    
    elif request.method == 'POST':
        # Handle form submission
        form = EquipmentCategoryForm(request.POST, instance=category)
        if form.is_valid():
            category = form.save(commit=False)
            category.updated_by = request.user
            category.save()
            
            return JsonResponse({
                'status': 'success',
                'message': f'Equipment category "{category.name}" updated successfully!',
                'category': {
                    'id': category.id,
                    'name': category.name,
                    'description': category.description or '',
                    'is_active': category.is_active,
                }
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Please correct the errors below.',
                'errors': form.errors
            }, status=400)
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)


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


__all__ = ["equipment_items_settings", "equipment_conditional_fields_settings", "custom_fields_management", "category_fields_api", "equipment_items_api", "add_equipment_category", "edit_equipment_category", "edit_equipment_category_ajax", "equipment_categories_settings", "delete_equipment_category"]
