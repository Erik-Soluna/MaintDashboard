from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from django.core.paginator import Paginator
from datetime import datetime, timedelta
import json

from .models import CalendarEvent, EventComment, EventAttachment
from equipment.models import Equipment
from core.models import Location

def index(request):
    return HttpResponse("Events index view")

@login_required
def calendar_view(request):
    """Display calendar view of events with filtering capabilities."""
    # Get filter parameters
    selected_site_id = request.GET.get('site_id', request.session.get('selected_site_id'))
    event_type = request.GET.get('event_type', '')
    equipment_filter = request.GET.get('equipment', '')
    
    # Get all sites for the site selector
    sites = Location.objects.filter(is_site=True, is_active=True).order_by('name')
    selected_site = None
    if selected_site_id:
        try:
            selected_site = sites.get(id=selected_site_id)
            request.session['selected_site_id'] = selected_site_id
        except Location.DoesNotExist:
            pass
    
    # Get events (will be filtered via AJAX) - test if we have any events
    events = CalendarEvent.objects.select_related('equipment', 'equipment__location').all()
    events_count = events.count()
    
    # Get equipment for filtering
    equipment_list = Equipment.objects.filter(is_active=True).order_by('name')
    if selected_site:
        equipment_list = equipment_list.filter(
            Q(location__parent_location=selected_site) | Q(location=selected_site)
        )
    
    # Add debug info
    print(f"Calendar view: Found {events_count} events total")
    print(f"Calendar view: Found {equipment_list.count()} equipment items")
    
    context = {
        'sites': sites,
        'selected_site': selected_site,
        'equipment_list': equipment_list,
        'event_types': CalendarEvent.EVENT_TYPES,
        'selected_event_type': event_type,
        'selected_equipment': equipment_filter,
        'events_count': events_count,  # Add for debugging
    }
    return render(request, 'events/calendar.html', context)


@login_required
def test_events_api(request):
    """Test endpoint to check if events API is working."""
    try:
        events = CalendarEvent.objects.select_related('equipment', 'equipment__location').all()
        events_data = []
        
        for event in events[:10]:  # Limit to first 10 for testing
            events_data.append({
                'id': event.id,
                'title': event.title,
                'event_date': str(event.event_date),
                'equipment': event.equipment.name if event.equipment else 'No equipment',
                'event_type': event.event_type,
            })
        
        return JsonResponse({
            'success': True,
            'count': events.count(),
            'events': events_data,
            'user': request.user.username,
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
        })


@login_required
def event_list(request):
    """Display list of events with search and filtering."""
    search_query = request.GET.get('search', '')
    event_type = request.GET.get('event_type', '')
    equipment_filter = request.GET.get('equipment', '')
    status_filter = request.GET.get('status', '')
    
    # Base queryset
    events = CalendarEvent.objects.select_related('equipment', 'equipment__location', 'assigned_to').all()
    
    # Apply filters
    if search_query:
        events = events.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(equipment__name__icontains=search_query)
        )
    
    if event_type:
        events = events.filter(event_type=event_type)
    
    if equipment_filter:
        events = events.filter(equipment_id=equipment_filter)
    
    if status_filter == 'completed':
        events = events.filter(is_completed=True)
    elif status_filter == 'pending':
        events = events.filter(is_completed=False)
    elif status_filter == 'overdue':
        events = events.filter(event_date__lt=timezone.now().date(), is_completed=False)
    
    # Order by date
    events = events.order_by('-event_date', '-start_time')
    
    # Pagination
    paginator = Paginator(events, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get equipment for filtering
    equipment_list = Equipment.objects.filter(is_active=True).order_by('name')
    
    context = {
        'page_obj': page_obj,
        'equipment_list': equipment_list,
        'event_types': CalendarEvent.EVENT_TYPES,
        'search_query': search_query,
        'selected_event_type': event_type,
        'selected_equipment': equipment_filter,
        'selected_status': status_filter,
    }
    return render(request, 'events/event_list.html', context)


@login_required
def add_event(request):
    """Add a new event linked to equipment or location."""
    if request.method == 'POST':
        try:
            # Get form data
            title = request.POST.get('title')
            description = request.POST.get('description', '')
            event_type = request.POST.get('event_type')
            equipment_id = request.POST.get('equipment')
            event_date = request.POST.get('event_date')
            start_time = request.POST.get('start_time') or None
            end_time = request.POST.get('end_time') or None
            all_day = 'all_day' in request.POST
            priority = request.POST.get('priority', 'medium')
            assigned_to_id = request.POST.get('assigned_to') or None
            
            # Create the event
            event = CalendarEvent.objects.create(
                title=title,
                description=description,
                event_type=event_type,
                equipment_id=equipment_id,
                event_date=event_date,
                start_time=start_time,
                end_time=end_time,
                all_day=all_day,
                priority=priority,
                assigned_to_id=assigned_to_id,
                created_by=request.user
            )
            
            messages.success(request, f'Event "{title}" created successfully!')
            return redirect('events:event_detail', event_id=event.id)
            
        except Exception as e:
            messages.error(request, f'Error creating event: {str(e)}')
            return redirect('events:add_event')
    
    # Get equipment and users for the form
    equipment_list = Equipment.objects.filter(is_active=True).order_by('name')
    from django.contrib.auth.models import User
    users = User.objects.filter(is_active=True).order_by('first_name', 'last_name')
    
    context = {
        'equipment_list': equipment_list,
        'users': users,
        'event_types': CalendarEvent.EVENT_TYPES,
        'priority_choices': CalendarEvent.PRIORITY_CHOICES,
    }
    return render(request, 'events/add_event.html', context)


@login_required
def event_detail(request, event_id):
    """Display detailed view of an event."""
    event = get_object_or_404(CalendarEvent, id=event_id)
    comments = event.comments.all().order_by('-created_at')
    attachments = event.attachments.all()
    
    # Handle comment submission
    if request.method == 'POST' and 'add_comment' in request.POST:
        comment_text = request.POST.get('comment')
        if comment_text:
            EventComment.objects.create(
                event=event,
                comment=comment_text,
                created_by=request.user
            )
            messages.success(request, 'Comment added successfully!')
            return redirect('events:event_detail', event_id=event.id)
    
    context = {
        'event': event,
        'comments': comments,
        'attachments': attachments,
    }
    return render(request, 'events/event_detail.html', context)


@login_required
def edit_event(request, event_id):
    """Edit an existing event."""
    event = get_object_or_404(CalendarEvent, id=event_id)
    
    if request.method == 'POST':
        try:
            # Update event fields
            event.title = request.POST.get('title')
            event.description = request.POST.get('description', '')
            event.event_type = request.POST.get('event_type')
            event.equipment_id = request.POST.get('equipment')
            event.event_date = request.POST.get('event_date')
            event.start_time = request.POST.get('start_time') or None
            event.end_time = request.POST.get('end_time') or None
            event.all_day = 'all_day' in request.POST
            event.priority = request.POST.get('priority', 'medium')
            event.assigned_to_id = request.POST.get('assigned_to') or None
            event.updated_by = request.user
            event.save()
            
            messages.success(request, f'Event "{event.title}" updated successfully!')
            return redirect('events:event_detail', event_id=event.id)
            
        except Exception as e:
            messages.error(request, f'Error updating event: {str(e)}')
    
    # Get equipment and users for the form
    equipment_list = Equipment.objects.filter(is_active=True).order_by('name')
    from django.contrib.auth.models import User
    users = User.objects.filter(is_active=True).order_by('first_name', 'last_name')
    
    context = {
        'event': event,
        'equipment_list': equipment_list,
        'users': users,
        'event_types': CalendarEvent.EVENT_TYPES,
        'priority_choices': CalendarEvent.PRIORITY_CHOICES,
    }
    return render(request, 'events/edit_event.html', context)


@login_required
def complete_event(request, event_id):
    """Mark an event as complete."""
    if request.method == 'POST':
        event = get_object_or_404(CalendarEvent, id=event_id)
        event.is_completed = True
        event.completion_notes = request.POST.get('completion_notes', '')
        event.updated_by = request.user
        event.save()
        
        messages.success(request, f'Event "{event.title}" marked as completed!')
        return JsonResponse({'status': 'success', 'message': 'Event completed successfully'})
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
@require_http_methods(["GET"])
def fetch_events(request):
    """API endpoint to fetch events for calendar display."""
    try:
        start_date = request.GET.get('start')
        end_date = request.GET.get('end')
        equipment_filter = request.GET.get('equipment')
        event_type_filter = request.GET.get('event_type')
        site_id = request.GET.get('site_id')
        
        # Base queryset
        events = CalendarEvent.objects.select_related('equipment', 'equipment__location')
        
        # Date filtering
        if start_date and end_date:
            try:
                # Parse dates from FullCalendar format
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                events = events.filter(
                    event_date__gte=start_dt.date(),
                    event_date__lte=end_dt.date()
                )
            except ValueError:
                # Fallback for simple date format
                events = events.filter(
                    event_date__gte=start_date,
                    event_date__lte=end_date
                )
        
        # Site filtering
        if site_id:
            events = events.filter(
                Q(equipment__location__parent_location_id=site_id) | 
                Q(equipment__location_id=site_id)
            )
        
        # Equipment filtering
        if equipment_filter:
            events = events.filter(equipment_id=equipment_filter)
        
        # Event type filtering
        if event_type_filter:
            events = events.filter(event_type=event_type_filter)
        
        # Convert to FullCalendar format
        calendar_events = []
        for event in events:
            try:
                # Build title with equipment name if available
                title = event.title
                if event.equipment:
                    title = f"{event.title} - {event.equipment.name}"
                
                calendar_event = {
                    'id': event.id,
                    'title': title,
                    'start': str(event.event_date),
                    'allDay': event.all_day,
                    'backgroundColor': get_event_color(event.event_type, event.priority),
                    'borderColor': get_event_color(event.event_type, event.priority),
                    'textColor': '#ffffff',
                    'url': f"/events/events/{event.id}/",
                    'extendedProps': {
                        'equipment': event.equipment.name if event.equipment else 'No equipment',
                        'location': event.equipment.location.name if event.equipment and event.equipment.location else 'No location',
                        'priority': event.priority,
                        'event_type': event.event_type,
                        'assigned_to': event.assigned_to.get_full_name() if event.assigned_to else 'Unassigned',
                        'is_completed': event.is_completed,
                    }
                }
                
                # Add time information if not all day
                if not event.all_day and event.start_time:
                    calendar_event['start'] = f"{event.event_date}T{event.start_time}"
                    if event.end_time:
                        calendar_event['end'] = f"{event.event_date}T{event.end_time}"
                
                calendar_events.append(calendar_event)
            except Exception as e:
                # Log the error but continue with other events
                print(f"Error processing event {event.id}: {str(e)}")
                continue
        
        return JsonResponse(calendar_events, safe=False)
    
    except Exception as e:
        # Return detailed error for debugging
        import traceback
        print(f"Error in fetch_events: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({
            'error': str(e),
            'message': 'There was an error while fetching events',
            'debug_info': str(traceback.format_exc()) if request.user.is_superuser else None
        }, status=500)


def get_event_color(event_type, priority):
    """Get color for event based on type and priority."""
    colors = {
        'maintenance': '#dc3545',  # Red
        'inspection': '#ffc107',   # Yellow
        'calibration': '#17a2b8',  # Blue
        'outage': '#fd7e14',       # Orange
        'upgrade': '#6f42c1',      # Purple
        'commissioning': '#20c997', # Teal
        'decommissioning': '#6c757d', # Gray
        'testing': '#28a745',      # Green
        'other': '#007bff',        # Primary blue
    }
    
    base_color = colors.get(event_type, '#007bff')
    
    # Adjust opacity based on priority
    if priority == 'critical':
        return base_color
    elif priority == 'high':
        return base_color + 'DD'  # 87% opacity
    elif priority == 'medium':
        return base_color + 'BB'  # 73% opacity
    else:  # low
        return base_color + '99'  # 60% opacity


@require_http_methods(["GET"])
def get_event(request, event_id):
    """API endpoint to get a specific event."""
    event = get_object_or_404(CalendarEvent, id=event_id)
    
    event_data = {
        'id': event.id,
        'title': event.title,
        'description': event.description,
        'event_type': event.event_type,
        'equipment': {
            'id': event.equipment.id,
            'name': event.equipment.name,
            'location': event.equipment.location.name if event.equipment.location else ''
        },
        'event_date': str(event.event_date),
        'start_time': str(event.start_time) if event.start_time else None,
        'end_time': str(event.end_time) if event.end_time else None,
        'all_day': event.all_day,
        'priority': event.priority,
        'assigned_to': event.assigned_to.get_full_name() if event.assigned_to else None,
        'is_completed': event.is_completed,
        'created_at': event.created_at.isoformat(),
        'created_by': event.created_by.get_full_name() if event.created_by else ''
    }
    
    return JsonResponse(event_data)


@login_required
def equipment_events(request, equipment_id):
    """Display events for specific equipment."""
    equipment = get_object_or_404(Equipment, id=equipment_id)
    events = CalendarEvent.objects.filter(equipment=equipment).order_by('-event_date')
    
    # Pagination
    paginator = Paginator(events, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'equipment': equipment,
        'page_obj': page_obj,
        'events': events,
    }
    return render(request, 'events/equipment_events.html', context)