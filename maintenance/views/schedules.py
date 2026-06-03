"""schedules views (split from the original monolithic views.py)."""
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
from core.rbac import permission_required


@login_required
def schedule_list(request):
    """List maintenance schedules."""
    try:
        schedules = MaintenanceSchedule.objects.select_related(
            'equipment', 'activity_type'
        ).filter(is_active=True)
        
        context = {'schedules': schedules}
        return render(request, 'maintenance/schedule_list.html', context)
        
    except Exception as e:
        logger.error(f"Database error in schedule_list: {str(e)}")
        
        # Try alternative query without select_related
        try:
            schedules = MaintenanceSchedule.objects.filter(is_active=True)
            context = {
                'schedules': schedules,
                'database_error': True,
                'error_message': 'Database schema issue detected. Some functionality may be limited.'
            }
            return render(request, 'maintenance/schedule_list.html', context)
            
        except Exception as fallback_error:
            logger.error(f"Fallback query also failed: {str(fallback_error)}")
            messages.error(request, 'Database connection issue. Please contact support.')
            return redirect('maintenance:maintenance_list')


@permission_required('maintenance.create')
def add_schedule(request):
    """Add new maintenance schedule."""
    if request.method == 'POST':
        form = MaintenanceScheduleForm(request.POST, request=request)
        if form.is_valid():
            schedule = form.save(commit=False)
            schedule.created_by = request.user
            # The add template doesn't render the is_active checkbox, so it would
            # otherwise post as False (BooleanField) and the new schedule would be
            # hidden from schedule_list (which filters is_active=True). New
            # schedules are active by default.
            schedule.is_active = True
            schedule.save()

            messages.success(request, f'Maintenance schedule created successfully!')
            return redirect('maintenance:schedule_detail', schedule_id=schedule.id)
    else:
        form = MaintenanceScheduleForm(request=request)
    
    context = {'form': form}
    return render(request, 'maintenance/add_schedule.html', context)


@login_required
def schedule_detail(request, schedule_id):
    """Display maintenance schedule details."""
    schedule = get_object_or_404(
        MaintenanceSchedule.objects.select_related('equipment', 'activity_type'),
        id=schedule_id
    )
    
    # Get recent activities for this schedule
    recent_activities = MaintenanceActivity.objects.filter(
        equipment=schedule.equipment,
        activity_type=schedule.activity_type
    ).order_by('-scheduled_start')[:10]
    
    context = {
        'schedule': schedule,
        'recent_activities': recent_activities,
    }
    
    return render(request, 'maintenance/schedule_detail.html', context)


@permission_required('maintenance.edit')
def edit_schedule(request, schedule_id):
    """Edit maintenance schedule."""
    schedule = get_object_or_404(MaintenanceSchedule, id=schedule_id)
    
    if request.method == 'POST':
        # Capture the pre-edit frequency to detect a manual periodicity change (#82).
        old_frequency = schedule.frequency
        old_frequency_days = schedule.frequency_days
        form = MaintenanceScheduleForm(request.POST, instance=schedule, request=request)
        if form.is_valid():
            schedule = form.save(commit=False)
            schedule.updated_by = request.user
            frequency_changed = (
                schedule.frequency != old_frequency
                or schedule.frequency_days != old_frequency_days
            )
            if frequency_changed:
                # Mark as manually overridden so the activity-type signal won't revert it.
                schedule.frequency_overridden = True
            schedule.save()

            if frequency_changed:
                # Re-lay future occurrences on the new cadence: delete not-yet-started
                # future activities (never started/completed) and regenerate.
                today = timezone.now().date()
                MaintenanceActivity.objects.filter(
                    equipment=schedule.equipment,
                    activity_type=schedule.activity_type,
                    status='scheduled',
                    scheduled_start__date__gt=today,
                ).delete()
                schedule.last_generated = None
                schedule.save(update_fields=['last_generated'])
                if schedule.auto_generate:
                    schedule.generate_next_activity()

            messages.success(request, 'Maintenance schedule updated successfully!')
            return redirect('maintenance:schedule_detail', schedule_id=schedule.id)
    else:
        form = MaintenanceScheduleForm(instance=schedule, request=request)
    
    context = {
        'form': form,
        'schedule': schedule,
    }
    
    return render(request, 'maintenance/edit_schedule.html', context)


@permission_required('maintenance.create')
def generate_scheduled_activities(request):
    """Generate maintenance activities from schedules."""
    if request.method == 'POST':
        generated_count = 0
        schedules = MaintenanceSchedule.objects.filter(
            is_active=True,
            auto_generate=True
        )
        
        for schedule in schedules:
            activity = schedule.generate_next_activity()
            if activity:
                generated_count += 1
        
        messages.success(request, f'Generated {generated_count} new maintenance activities!')
        return redirect('maintenance:maintenance_list')
    
    # Show preview of what would be generated
    schedules_to_generate = []
    schedules = MaintenanceSchedule.objects.filter(
        is_active=True,
        auto_generate=True
    )
    
    for schedule in schedules:
        # Logic to determine if activity should be generated
        advance_date = timezone.now().date() + timedelta(days=schedule.advance_notice_days)
        # Add to preview list if needed
        schedules_to_generate.append(schedule)
    
    context = {
        'schedules_to_generate': schedules_to_generate,
    }
    
    return render(request, 'maintenance/generate_activities.html', context)


@permission_required('maintenance.delete')
def delete_schedule(request, schedule_id):
    """Delete maintenance schedule."""
    schedule = get_object_or_404(MaintenanceSchedule, id=schedule_id)
    
    if request.method == 'POST':
        schedule_name = f"{schedule.equipment.name} - {schedule.activity_type.name}"
        schedule.delete()
        messages.success(request, f'Maintenance schedule "{schedule_name}" deleted successfully!')
        return redirect('maintenance:schedule_list')
    
    context = {'schedule': schedule}
    return render(request, 'maintenance/delete_schedule.html', context)


@login_required
def generate_maintenance_activities(request):
    """Alias for generate_scheduled_activities to match URL pattern."""
    return generate_scheduled_activities(request)


@login_required
def schedules_view(request):
    """Combined view for both global and category schedules."""
    try:
        # Get category schedules
        category_schedules = EquipmentCategorySchedule.objects.select_related(
            'equipment_category', 'activity_type', 'activity_type__category'
        ).order_by('equipment_category__name', 'activity_type__name')
        
        # Get global schedules
        global_schedules = GlobalSchedule.objects.select_related(
            'activity_type', 'activity_type__category'
        ).order_by('name')
        
        context = {
            'category_schedules': category_schedules,
            'global_schedules': global_schedules,
        }
        return render(request, 'maintenance/schedules.html', context)
        
    except Exception as e:
        logger.error(f"Database error in schedules_view: {str(e)}")
        context = {
            'category_schedules': [],
            'global_schedules': [],
            'database_error': True,
            'error_message': 'Database schema issue detected. Some functionality may be limited.'
        }
        return render(request, 'maintenance/schedules.html', context)


@login_required
def category_schedule_list(request):
    """List equipment category schedules."""
    try:
        schedules = EquipmentCategorySchedule.objects.select_related(
            'equipment_category', 'activity_type', 'activity_type__category'
        ).order_by('equipment_category__name', 'activity_type__name')
        
        context = {
            'schedules': schedules,
        }
        return render(request, 'maintenance/category_schedule_list.html', context)
        
    except Exception as e:
        logger.error(f"Database error in category_schedule_list: {str(e)}")
        context = {
            'schedules': [],
            'database_error': True,
            'error_message': 'Database schema issue detected. Some functionality may be limited.'
        }
        return render(request, 'maintenance/category_schedule_list.html', context)


@permission_required('maintenance.manage_all')
def add_category_schedule(request):
    """Add new equipment category schedule."""
    if request.method == 'POST':
        form = EquipmentCategoryScheduleForm(request.POST)
        if form.is_valid():
            schedule = form.save(commit=False)
            schedule.created_by = request.user
            schedule.save()
            
            messages.success(request, 'Category schedule created successfully!')
            return redirect('maintenance:category_schedule_list')
    else:
        form = EquipmentCategoryScheduleForm()
    
    context = {
        'form': form,
        'title': 'Add Category Schedule'
    }
    return render(request, 'maintenance/category_schedule_form.html', context)


@permission_required('maintenance.manage_all')
def edit_category_schedule(request, schedule_id):
    """Edit equipment category schedule."""
    schedule = get_object_or_404(EquipmentCategorySchedule, id=schedule_id)
    
    if request.method == 'POST':
        form = EquipmentCategoryScheduleForm(request.POST, instance=schedule)
        if form.is_valid():
            schedule = form.save(commit=False)
            schedule.updated_by = request.user
            schedule.save()
            
            messages.success(request, 'Category schedule updated successfully!')
            return redirect('maintenance:category_schedule_list')
    else:
        form = EquipmentCategoryScheduleForm(instance=schedule)
    
    context = {
        'form': form,
        'schedule': schedule,
        'title': 'Edit Category Schedule'
    }
    return render(request, 'maintenance/category_schedule_form.html', context)


@login_required
def category_schedule_detail(request, schedule_id):
    """View equipment category schedule details."""
    schedule = get_object_or_404(EquipmentCategorySchedule, id=schedule_id)
    
    # Get equipment that uses this category
    equipment_list = Equipment.objects.filter(
        category=schedule.equipment_category,
        is_active=True
    ).order_by('name')
    
    # Get recent activities for this schedule
    recent_activities = MaintenanceActivity.objects.filter(
        equipment__category=schedule.equipment_category,
        activity_type=schedule.activity_type
    ).order_by('-scheduled_start')[:10]
    
    context = {
        'schedule': schedule,
        'equipment_list': equipment_list,
        'recent_activities': recent_activities,
    }
    
    return render(request, 'maintenance/category_schedule_detail.html', context)


@login_required
def global_schedule_list(request):
    """List global schedules."""
    try:
        schedules = GlobalSchedule.objects.select_related(
            'activity_type', 'activity_type__category'
        ).order_by('name')
        
        context = {
            'schedules': schedules,
        }
        return render(request, 'maintenance/global_schedule_list.html', context)
        
    except Exception as e:
        logger.error(f"Database error in global_schedule_list: {str(e)}")
        context = {
            'schedules': [],
            'database_error': True,
            'error_message': 'Database schema issue detected. Some functionality may be limited.'
        }
        return render(request, 'maintenance/global_schedule_list.html', context)


@permission_required('maintenance.manage_all')
def add_global_schedule(request):
    """Add new global schedule."""
    if request.method == 'POST':
        form = GlobalScheduleForm(request.POST)
        if form.is_valid():
            schedule = form.save(commit=False)
            schedule.created_by = request.user
            schedule.save()
            
            messages.success(request, 'Global schedule created successfully!')
            return redirect('maintenance:global_schedule_list')
    else:
        form = GlobalScheduleForm()
    
    context = {
        'form': form,
        'title': 'Add Global Schedule'
    }
    return render(request, 'maintenance/global_schedule_form.html', context)


@permission_required('maintenance.manage_all')
def edit_global_schedule(request, schedule_id):
    """Edit global schedule."""
    schedule = get_object_or_404(GlobalSchedule, id=schedule_id)
    
    if request.method == 'POST':
        form = GlobalScheduleForm(request.POST, instance=schedule)
        if form.is_valid():
            schedule = form.save(commit=False)
            schedule.updated_by = request.user
            schedule.save()
            
            messages.success(request, 'Global schedule updated successfully!')
            return redirect('maintenance:global_schedule_list')
    else:
        form = GlobalScheduleForm(instance=schedule)
    
    context = {
        'form': form,
        'schedule': schedule,
        'title': 'Edit Global Schedule'
    }
    return render(request, 'maintenance/global_schedule_form.html', context)


@login_required
def global_schedule_detail(request, schedule_id):
    """View global schedule details."""
    schedule = get_object_or_404(GlobalSchedule, id=schedule_id)
    
    # Get all equipment that could be affected by this global schedule
    equipment_list = Equipment.objects.filter(is_active=True).order_by('name')
    
    # Get recent activities for this schedule
    recent_activities = MaintenanceActivity.objects.filter(
        activity_type=schedule.activity_type
    ).order_by('-scheduled_start')[:10]
    
    context = {
        'schedule': schedule,
        'equipment_list': equipment_list,
        'recent_activities': recent_activities,
    }
    
    return render(request, 'maintenance/global_schedule_detail.html', context)


@login_required
def schedule_override_list(request):
    """List schedule overrides."""
    try:
        overrides = ScheduleOverride.objects.select_related(
            'equipment', 'equipment__category', 'activity_type', 'activity_type__category'
        ).order_by('equipment__name', 'activity_type__name')
        
        context = {
            'overrides': overrides,
        }
        return render(request, 'maintenance/schedule_override_list.html', context)
        
    except Exception as e:
        logger.error(f"Database error in schedule_override_list: {str(e)}")
        context = {
            'overrides': [],
            'database_error': True,
            'error_message': 'Database schema issue detected. Some functionality may be limited.'
        }
        return render(request, 'maintenance/schedule_override_list.html', context)


@permission_required('maintenance.manage_all')
def add_schedule_override(request):
    """Add new schedule override."""
    if request.method == 'POST':
        form = ScheduleOverrideForm(request.POST, request=request)
        if form.is_valid():
            override = form.save(commit=False)
            override.created_by = request.user
            # The add template doesn't render is_active; default new overrides to
            # active so they actually take effect.
            override.is_active = True
            override.save()

            messages.success(request, 'Schedule override created successfully!')
            return redirect('maintenance:schedule_override_list')
    else:
        form = ScheduleOverrideForm(request=request)
    
    context = {
        'form': form,
        'title': 'Add Schedule Override'
    }
    return render(request, 'maintenance/schedule_override_form.html', context)


@permission_required('maintenance.manage_all')
def edit_schedule_override(request, override_id):
    """Edit schedule override."""
    override = get_object_or_404(ScheduleOverride, id=override_id)
    
    if request.method == 'POST':
        form = ScheduleOverrideForm(request.POST, instance=override, request=request)
        if form.is_valid():
            override = form.save(commit=False)
            override.updated_by = request.user
            override.save()
            
            messages.success(request, 'Schedule override updated successfully!')
            return redirect('maintenance:schedule_override_list')
    else:
        form = ScheduleOverrideForm(instance=override, request=request)
    
    context = {
        'form': form,
        'override': override,
        'title': 'Edit Schedule Override'
    }
    return render(request, 'maintenance/schedule_override_form.html', context)


@login_required
def schedule_override_detail(request, override_id):
    """View schedule override details."""
    override = get_object_or_404(ScheduleOverride, id=override_id)
    
    # Get the effective schedule for comparison
    effective_schedule = override.equipment.get_effective_schedule(override.activity_type)
    
    # Get recent activities for this override
    recent_activities = MaintenanceActivity.objects.filter(
        equipment=override.equipment,
        activity_type=override.activity_type
    ).order_by('-scheduled_start')[:10]
    
    context = {
        'override': override,
        'effective_schedule': effective_schedule,
        'recent_activities': recent_activities,
    }
    
    return render(request, 'maintenance/schedule_override_detail.html', context)


@login_required
def apply_schedules_to_equipment(request, equipment_id):
    """Apply category and global schedules to specific equipment."""
    equipment = get_object_or_404(Equipment, id=equipment_id)
    
    if request.method == 'POST':
        try:
            equipment.apply_category_schedules(request.user)
            messages.success(request, f'Schedules applied to {equipment.name} successfully!')
        except Exception as e:
            logger.error(f"Error applying schedules to equipment {equipment.id}: {str(e)}")
            messages.error(request, f'Error applying schedules: {str(e)}')
        
        return redirect('equipment:equipment_detail', equipment_id=equipment.id)
    
    # Show preview of what would be applied
    category_schedules = EquipmentCategorySchedule.objects.filter(
        equipment_category=equipment.category,
        is_active=True
    ) if equipment.category else []
    
    global_schedules = GlobalSchedule.objects.filter(is_active=True)
    
    existing_overrides = ScheduleOverride.objects.filter(equipment=equipment)
    
    context = {
        'equipment': equipment,
        'category_schedules': category_schedules,
        'global_schedules': global_schedules,
        'existing_overrides': existing_overrides,
    }
    
    return render(request, 'maintenance/apply_schedules_preview.html', context)


__all__ = ["schedule_list", "add_schedule", "schedule_detail", "edit_schedule", "generate_scheduled_activities", "delete_schedule", "generate_maintenance_activities", "schedules_view", "category_schedule_list", "add_category_schedule", "edit_category_schedule", "category_schedule_detail", "global_schedule_list", "add_global_schedule", "edit_global_schedule", "global_schedule_detail", "schedule_override_list", "add_schedule_override", "edit_schedule_override", "schedule_override_detail", "apply_schedules_to_equipment"]
