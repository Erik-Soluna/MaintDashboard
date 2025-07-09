"""
Views for event management.
Fixed calendar functionality from original web2py controllers.
"""

import json
import logging
from datetime import datetime, timedelta
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone

from .models import CalendarEvent, EventComment, EventAttachment
from equipment.models import Equipment
from maintenance.models import MaintenanceActivity
from .forms import CalendarEventForm

logger = logging.getLogger(__name__)


@login_required
def calendar_view(request):
    """
    Main calendar view.
    Fixed: Improved from original web2py calendar functionality.
    """
    # Get current month events for initial load
    today = timezone.now().date()
    start_of_month = today.replace(day=1)
    end_of_month = (start_of_month + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    
    events = CalendarEvent.objects.filter(
        event_date__range=[start_of_month, end_of_month]
    ).select_related('equipment', 'assigned_to')
    
    # Get maintenance activities for calendar integration
    maintenance_activities = MaintenanceActivity.objects.filter(
        scheduled_start__date__range=[start_of_month, end_of_month]
    ).select_related('equipment', 'activity_type')
    
    context = {
        'events': events,
        'maintenance_activities': maintenance_activities,
        'current_month': today.month,
        'current_year': today.year,
    }
    
    return render(request, 'events/calendar_view.html', context)


@login_required
def fetch_events(request):
    """
    AJAX endpoint to fetch events for FullCalendar.
    Replicates original web2py functionality with improvements.
    """
    start_date = request.GET.get('start')
    end_date = request.GET.get('end')
    
    if not start_date or not end_date:
        return JsonResponse({
            'status': 'error', 
            'message': 'Invalid date range'
        })
    
    try:
        # Parse dates
        start = datetime.fromisoformat(start_date.replace('Z', '+00:00')).date()
        end = datetime.fromisoformat(end_date.replace('Z', '+00:00')).date()
        
        # Fetch calendar events
        events = CalendarEvent.objects.filter(
            event_date__range=[start, end]
        ).select_related('equipment', 'assigned_to')
        
        # Fetch maintenance activities (integration with maintenance app)
        maintenance_activities = MaintenanceActivity.objects.filter(
            scheduled_start__date__range=[start, end]
        ).select_related('equipment', 'activity_type')
        
        # Convert to FullCalendar format
        calendar_events = []
        
        # Add calendar events
        for event in events:
            event_data = {
                'id': f'event_{event.id}',
                'title': event.title,
                'start': event.event_date.isoformat(),
                'allDay': event.all_day,
                'description': event.description,
                'equipment_id': event.equipment.id,
                'equipment_name': event.equipment.name,
                'event_type': event.event_type,
                'priority': event.priority,
                'backgroundColor': get_event_color(event.event_type, event.priority),
                'textColor': '#ffffff',
            }
            
            if not event.all_day and event.start_time:
                event_data['start'] = f"{event.event_date}T{event.start_time}"
                if event.end_time:
                    event_data['end'] = f"{event.event_date}T{event.end_time}"
            
            calendar_events.append(event_data)
        
        # Add maintenance activities
        for activity in maintenance_activities:
            activity_data = {
                'id': f'maintenance_{activity.id}',
                'title': f"[Maintenance] {activity.title}",
                'start': activity.scheduled_start.isoformat(),
                'end': activity.scheduled_end.isoformat(),
                'description': activity.description,
                'equipment_id': activity.equipment.id,
                'equipment_name': activity.equipment.name,
                'activity_type': activity.activity_type.name,
                'status': activity.status,
                'backgroundColor': get_maintenance_color(activity.status),
                'textColor': '#ffffff',
            }
            calendar_events.append(activity_data)
        
        logger.debug(f"Fetched {len(calendar_events)} events for calendar.")
        return JsonResponse(calendar_events, safe=False)
        
    except Exception as e:
        logger.error(f"Error fetching events: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f'Error fetching events: {str(e)}'
        })


@login_required
def get_event(request, event_id):
    """
    Get single event details (AJAX endpoint).
    Replicates original web2py functionality.
    """
    try:
        event = get_object_or_404(CalendarEvent, id=event_id)
        
        event_data = {
            'id': event.id,
            'title': event.title,
            'description': event.description,
            'event_type': event.event_type,
            'event_date': event.event_date.isoformat(),
            'start_time': event.start_time.strftime('%H:%M') if event.start_time else None,
            'end_time': event.end_time.strftime('%H:%M') if event.end_time else None,
            'all_day': event.all_day,
            'priority': event.priority,
            'equipment_id': event.equipment.id,
            'equipment_name': event.equipment.name,
            'assigned_to': event.assigned_to.username if event.assigned_to else None,
            'is_completed': event.is_completed,
            'completion_notes': event.completion_notes,
        }
        
        return JsonResponse({
            'status': 'success', 
            'event': event_data
        })
        
    except Exception as e:
        logger.error(f"Error getting event {event_id}: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f'Error getting event: {str(e)}'
        })


@login_required
def event_list(request):
    """List all events with filtering."""
    queryset = CalendarEvent.objects.select_related(
        'equipment', 'assigned_to'
    ).all()
    
    # Filtering
    event_type = request.GET.get('event_type')
    if event_type:
        queryset = queryset.filter(event_type=event_type)
        
    equipment_id = request.GET.get('equipment')
    if equipment_id:
        queryset = queryset.filter(equipment_id=equipment_id)
        
    date_from = request.GET.get('date_from')
    if date_from:
        queryset = queryset.filter(event_date__gte=date_from)
        
    date_to = request.GET.get('date_to')
    if date_to:
        queryset = queryset.filter(event_date__lte=date_to)
    
    search_term = request.GET.get('search', '')
    if search_term:
        queryset = queryset.filter(
            Q(title__icontains=search_term) |
            Q(equipment__name__icontains=search_term) |
            Q(description__icontains=search_term)
        )
    
    # Pagination
    paginator = Paginator(queryset, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_term': search_term,
        'event_types': CalendarEvent.EVENT_TYPES,
        'equipment_list': Equipment.objects.filter(is_active=True),
        'selected_event_type': event_type,
        'selected_equipment': equipment_id,
        'date_from': date_from,
        'date_to': date_to,
    }
    
    return render(request, 'events/event_list.html', context)


@login_required
def event_detail(request, event_id):
    """Display event details."""
    event = get_object_or_404(
        CalendarEvent.objects.select_related('equipment', 'assigned_to'),
        id=event_id
    )
    
    comments = event.comments.all().order_by('-created_at')
    attachments = event.attachments.all()
    
    context = {
        'event': event,
        'comments': comments,
        'attachments': attachments,
    }
    
    return render(request, 'events/event_detail.html', context)


@login_required
def add_event(request):
    """Add new calendar event."""
    if request.method == 'POST':
        form = CalendarEventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.created_by = request.user
            event.save()
            
            messages.success(request, f'Event "{event.title}" created successfully!')
            return redirect('events:event_detail', event_id=event.id)
    else:
        form = CalendarEventForm()
        
        # Pre-fill equipment if provided
        equipment_id = request.GET.get('equipment_id')
        if equipment_id:
            try:
                equipment = Equipment.objects.get(id=equipment_id)
                form.initial['equipment'] = equipment
            except Equipment.DoesNotExist:
                pass
    
    context = {'form': form}
    return render(request, 'events/add_event.html', context)


@login_required
def edit_event(request, event_id):
    """Edit calendar event."""
    event = get_object_or_404(CalendarEvent, id=event_id)
    
    if request.method == 'POST':
        form = CalendarEventForm(request.POST, instance=event)
        if form.is_valid():
            event = form.save(commit=False)
            event.updated_by = request.user
            event.save()
            
            messages.success(request, f'Event "{event.title}" updated successfully!')
            return redirect('events:event_detail', event_id=event.id)
    else:
        form = CalendarEventForm(instance=event)
    
    context = {
        'form': form,
        'event': event,
    }
    
    return render(request, 'events/edit_event.html', context)


@login_required
def complete_event(request, event_id):
    """Mark event as completed."""
    event = get_object_or_404(CalendarEvent, id=event_id)
    
    if request.method == 'POST':
        event.is_completed = True
        event.completion_notes = request.POST.get('completion_notes', '')
        event.updated_by = request.user
        event.save()
        
        messages.success(request, f'Event "{event.title}" marked as completed!')
        return redirect('events:event_detail', event_id=event.id)
    
    context = {'event': event}
    return render(request, 'events/complete_event.html', context)


@login_required
def equipment_events(request, equipment_id):
    """List events for specific equipment."""
    equipment = get_object_or_404(Equipment, id=equipment_id)
    
    events = CalendarEvent.objects.filter(
        equipment=equipment
    ).order_by('-event_date')
    
    # Also get maintenance activities for this equipment
    maintenance_activities = MaintenanceActivity.objects.filter(
        equipment=equipment
    ).order_by('-scheduled_start')[:10]
    
    context = {
        'equipment': equipment,
        'events': events,
        'maintenance_activities': maintenance_activities,
    }
    
    return render(request, 'events/equipment_events.html', context)


def get_event_color(event_type, priority):
    """Get color for event based on type and priority."""
    colors = {
        'maintenance': '#007bff',  # Blue
        'inspection': '#28a745',   # Green
        'calibration': '#17a2b8',  # Teal
        'outage': '#dc3545',       # Red
        'upgrade': '#6f42c1',      # Purple
        'commissioning': '#fd7e14', # Orange
        'decommissioning': '#6c757d', # Gray
        'testing': '#20c997',      # Teal
        'other': '#6c757d',        # Gray
    }
    
    base_color = colors.get(event_type, '#6c757d')
    
    # Adjust for priority
    if priority == 'critical':
        return '#dc3545'  # Red for critical
    elif priority == 'high':
        return '#fd7e14'  # Orange for high
    
    return base_color


def get_maintenance_color(status):
    """Get color for maintenance activity based on status."""
    colors = {
        'scheduled': '#007bff',    # Blue
        'pending': '#ffc107',      # Yellow
        'in_progress': '#17a2b8',  # Teal
        'completed': '#28a745',    # Green
        'cancelled': '#6c757d',    # Gray
        'overdue': '#dc3545',      # Red
    }
    return colors.get(status, '#6c757d')