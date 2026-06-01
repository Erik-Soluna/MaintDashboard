"""timeline views (split from the original monolithic views.py)."""
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
def add_timeline_entry(request, activity_id):
    """Add a new timeline entry to a maintenance activity."""
    activity = get_object_or_404(MaintenanceActivity, id=activity_id)
    
    if request.method == 'POST':
        entry_type = request.POST.get('entry_type')
        title = request.POST.get('title')
        description = request.POST.get('description')
        
        if entry_type and title and description:
            try:
                # Create the timeline entry
                timeline_entry = MaintenanceTimelineEntry.objects.create(
                    activity=activity,
                    entry_type=entry_type,
                    title=title,
                    description=description,
                    created_by=request.user
                )
                
                messages.success(request, 'Timeline entry added successfully!')
                
                # Redirect back to the activity detail page
                return redirect('maintenance:activity_detail', activity_id=activity_id)
                
            except Exception as e:
                logger.error(f"Error creating timeline entry: {str(e)}")
                messages.error(request, f'Error creating timeline entry: {str(e)}')
        else:
            messages.error(request, 'Please fill in all required fields.')
    
    # If GET request or validation failed, redirect back to activity detail
    return redirect('maintenance:activity_detail', activity_id=activity_id)


@login_required
@user_passes_test(lambda u: u.is_staff)
def edit_timeline_entry(request, activity_id, entry_id):
    """Edit a timeline entry (admin only)."""
    activity = get_object_or_404(MaintenanceActivity, id=activity_id)
    timeline_entry = get_object_or_404(MaintenanceTimelineEntry, id=entry_id, activity=activity)
    
    if request.method == 'POST':
        entry_type = request.POST.get('entry_type')
        title = request.POST.get('title')
        description = request.POST.get('description')
        
        if entry_type and title and description:
            try:
                timeline_entry.entry_type = entry_type
                timeline_entry.title = title
                timeline_entry.description = description
                # updated_by is handled by TimeStampedModel if it exists
                if hasattr(timeline_entry, 'updated_by'):
                    timeline_entry.updated_by = request.user
                timeline_entry.save()
                
                messages.success(request, 'Timeline entry updated successfully!')
                return redirect('maintenance:activity_detail', activity_id=activity_id)
                
            except Exception as e:
                logger.error(f"Error updating timeline entry: {str(e)}")
                messages.error(request, f'Error updating timeline entry: {str(e)}')
        else:
            messages.error(request, 'Please fill in all required fields.')
    
    # If GET request or validation failed, redirect back to activity detail
    return redirect('maintenance:activity_detail', activity_id=activity_id)


@login_required
@user_passes_test(lambda u: u.is_staff)
@require_http_methods(["POST"])
def delete_timeline_entry(request, activity_id, entry_id):
    """Delete a timeline entry (admin only)."""
    activity = get_object_or_404(MaintenanceActivity, id=activity_id)
    timeline_entry = get_object_or_404(MaintenanceTimelineEntry, id=entry_id, activity=activity)
    
    try:
        timeline_entry.delete()
        messages.success(request, 'Timeline entry deleted successfully!')
    except Exception as e:
        logger.error(f"Error deleting timeline entry: {str(e)}")
        messages.error(request, f'Error deleting timeline entry: {str(e)}')
    
    return redirect('maintenance:activity_detail', activity_id=activity_id)


__all__ = ["add_timeline_entry", "edit_timeline_entry", "delete_timeline_entry"]
