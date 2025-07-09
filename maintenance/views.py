"""
Views for maintenance management.
Fixed associations and improved functionality from original web2py controllers.
"""

import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta

from .models import (
    MaintenanceActivity, MaintenanceActivityType, 
    MaintenanceSchedule, MaintenanceChecklist
)
from equipment.models import Equipment
from .forms import (
    MaintenanceActivityForm, MaintenanceScheduleForm, 
    MaintenanceActivityTypeForm
)

logger = logging.getLogger(__name__)


@login_required
def maintenance_list(request):
    """Main maintenance dashboard."""
    # Get upcoming maintenance
    upcoming_activities = MaintenanceActivity.objects.filter(
        scheduled_start__gte=timezone.now(),
        status__in=['scheduled', 'pending']
    ).select_related('equipment', 'activity_type').order_by('scheduled_start')[:10]
    
    # Get overdue maintenance
    overdue_activities = MaintenanceActivity.objects.filter(
        scheduled_end__lt=timezone.now(),
        status__in=['scheduled', 'pending']
    ).select_related('equipment', 'activity_type').order_by('scheduled_start')[:10]
    
    # Get in progress
    in_progress = MaintenanceActivity.objects.filter(
        status='in_progress'
    ).select_related('equipment', 'activity_type')
    
    # Statistics
    stats = {
        'total_activities': MaintenanceActivity.objects.count(),
        'pending_count': MaintenanceActivity.objects.filter(status='pending').count(),
        'overdue_count': overdue_activities.count(),
        'completed_this_month': MaintenanceActivity.objects.filter(
            status='completed',
            actual_end__gte=timezone.now().replace(day=1)
        ).count(),
    }
    
    context = {
        'upcoming_activities': upcoming_activities,
        'overdue_activities': overdue_activities,
        'in_progress': in_progress,
        'stats': stats,
    }
    
    return render(request, 'maintenance/maintenance_list.html', context)


@login_required
def activity_list(request):
    """List all maintenance activities with filtering."""
    queryset = MaintenanceActivity.objects.select_related(
        'equipment', 'activity_type', 'assigned_to'
    ).all()
    
    # Filtering
    status = request.GET.get('status')
    if status:
        queryset = queryset.filter(status=status)
        
    equipment_id = request.GET.get('equipment')
    if equipment_id:
        queryset = queryset.filter(equipment_id=equipment_id)
        
    activity_type_id = request.GET.get('activity_type')
    if activity_type_id:
        queryset = queryset.filter(activity_type_id=activity_type_id)
    
    search_term = request.GET.get('search', '')
    if search_term:
        queryset = queryset.filter(
            Q(title__icontains=search_term) |
            Q(equipment__name__icontains=search_term) |
            Q(activity_type__name__icontains=search_term)
        )
    
    # Pagination
    paginator = Paginator(queryset, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_term': search_term,
        'statuses': MaintenanceActivity.STATUS_CHOICES,
        'equipment_list': Equipment.objects.filter(is_active=True),
        'activity_types': MaintenanceActivityType.objects.filter(is_active=True),
        'selected_status': status,
        'selected_equipment': equipment_id,
        'selected_activity_type': activity_type_id,
    }
    
    return render(request, 'maintenance/activity_list.html', context)


@login_required
def activity_detail(request, activity_id):
    """Display detailed information for maintenance activity."""
    activity = get_object_or_404(
        MaintenanceActivity.objects.select_related(
            'equipment', 'activity_type', 'assigned_to'
        ),
        id=activity_id
    )
    
    checklist_items = activity.checklist_items.all().order_by('order')
    
    context = {
        'activity': activity,
        'checklist_items': checklist_items,
    }
    
    return render(request, 'maintenance/activity_detail.html', context)


@login_required
def add_activity(request):
    """Add new maintenance activity."""
    if request.method == 'POST':
        form = MaintenanceActivityForm(request.POST)
        if form.is_valid():
            activity = form.save(commit=False)
            activity.created_by = request.user
            activity.save()
            
            messages.success(request, f'Maintenance activity "{activity.title}" created successfully!')
            return redirect('maintenance:activity_detail', activity_id=activity.id)
    else:
        form = MaintenanceActivityForm()
    
    context = {'form': form}
    return render(request, 'maintenance/add_activity.html', context)


@login_required
def edit_activity(request, activity_id):
    """Edit maintenance activity."""
    activity = get_object_or_404(MaintenanceActivity, id=activity_id)
    
    if request.method == 'POST':
        form = MaintenanceActivityForm(request.POST, instance=activity)
        if form.is_valid():
            activity = form.save(commit=False)
            activity.updated_by = request.user
            activity.save()
            
            messages.success(request, f'Maintenance activity "{activity.title}" updated successfully!')
            return redirect('maintenance:activity_detail', activity_id=activity.id)
    else:
        form = MaintenanceActivityForm(instance=activity)
    
    context = {
        'form': form,
        'activity': activity,
    }
    
    return render(request, 'maintenance/edit_activity.html', context)


@login_required
def complete_activity(request, activity_id):
    """Mark maintenance activity as completed."""
    activity = get_object_or_404(MaintenanceActivity, id=activity_id)
    
    if request.method == 'POST':
        activity.status = 'completed'
        activity.actual_end = timezone.now()
        if not activity.actual_start:
            activity.actual_start = activity.actual_end
        activity.completion_notes = request.POST.get('completion_notes', '')
        activity.updated_by = request.user
        activity.save()
        
        messages.success(request, f'Maintenance activity "{activity.title}" marked as completed!')
        return redirect('maintenance:activity_detail', activity_id=activity.id)
    
    context = {'activity': activity}
    return render(request, 'maintenance/complete_activity.html', context)


@login_required
def schedule_list(request):
    """List maintenance schedules."""
    schedules = MaintenanceSchedule.objects.select_related(
        'equipment', 'activity_type'
    ).filter(is_active=True)
    
    context = {'schedules': schedules}
    return render(request, 'maintenance/schedule_list.html', context)


@login_required
def add_schedule(request):
    """Add new maintenance schedule."""
    if request.method == 'POST':
        form = MaintenanceScheduleForm(request.POST)
        if form.is_valid():
            schedule = form.save(commit=False)
            schedule.created_by = request.user
            schedule.save()
            
            messages.success(request, f'Maintenance schedule created successfully!')
            return redirect('maintenance:schedule_detail', schedule_id=schedule.id)
    else:
        form = MaintenanceScheduleForm()
    
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


@login_required
def edit_schedule(request, schedule_id):
    """Edit maintenance schedule."""
    schedule = get_object_or_404(MaintenanceSchedule, id=schedule_id)
    
    if request.method == 'POST':
        form = MaintenanceScheduleForm(request.POST, instance=schedule)
        if form.is_valid():
            schedule = form.save(commit=False)
            schedule.updated_by = request.user
            schedule.save()
            
            messages.success(request, 'Maintenance schedule updated successfully!')
            return redirect('maintenance:schedule_detail', schedule_id=schedule.id)
    else:
        form = MaintenanceScheduleForm(instance=schedule)
    
    context = {
        'form': form,
        'schedule': schedule,
    }
    
    return render(request, 'maintenance/edit_schedule.html', context)


@login_required
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


@login_required
def activity_type_list(request):
    """List maintenance activity types."""
    activity_types = MaintenanceActivityType.objects.filter(is_active=True)
    
    context = {'activity_types': activity_types}
    return render(request, 'maintenance/activity_type_list.html', context)


@login_required
def add_activity_type(request):
    """Add new maintenance activity type."""
    if request.method == 'POST':
        form = MaintenanceActivityTypeForm(request.POST)
        if form.is_valid():
            activity_type = form.save(commit=False)
            activity_type.created_by = request.user
            activity_type.save()
            
            messages.success(request, f'Activity type "{activity_type.name}" created successfully!')
            return redirect('maintenance:activity_type_list')
    else:
        form = MaintenanceActivityTypeForm()
    
    context = {'form': form}
    return render(request, 'maintenance/add_activity_type.html', context)


@login_required
def maintenance_reports(request):
    """Maintenance reports and analytics."""
    # Activity status distribution
    status_stats = MaintenanceActivity.objects.values('status').annotate(
        count=Count('id')
    ).order_by('status')
    
    # Equipment with most maintenance
    equipment_stats = MaintenanceActivity.objects.values(
        'equipment__name'
    ).annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # Monthly completion stats
    monthly_stats = MaintenanceActivity.objects.filter(
        status='completed',
        actual_end__gte=timezone.now() - timedelta(days=365)
    ).extra(
        {'month': 'EXTRACT(month FROM actual_end)'}
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')
    
    context = {
        'status_stats': status_stats,
        'equipment_stats': equipment_stats,
        'monthly_stats': monthly_stats,
    }
    
    return render(request, 'maintenance/reports.html', context)


@login_required
def overdue_maintenance(request):
    """List overdue maintenance activities."""
    overdue_activities = MaintenanceActivity.objects.filter(
        scheduled_end__lt=timezone.now(),
        status__in=['scheduled', 'pending', 'in_progress']
    ).select_related('equipment', 'activity_type', 'assigned_to').order_by('scheduled_end')
    
    context = {'overdue_activities': overdue_activities}
    return render(request, 'maintenance/overdue_maintenance.html', context)