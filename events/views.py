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
import uuid
import logging
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse

from .models import CalendarEvent, EventComment, EventAttachment
from equipment.models import Equipment
from core.models import Location

logger = logging.getLogger(__name__)


def create_maintenance_activity_for_event(event):
    """Create or update a maintenance activity for a calendar event."""
    if event.event_type != 'maintenance':
        return None
        
    try:
        from maintenance.models import MaintenanceActivity, MaintenanceActivityType
        from django.utils import timezone as django_timezone
        from datetime import datetime, time
        
        # Check if a maintenance activity already exists for this event
        existing_activity = event.maintenance_activity
        
        if existing_activity:
            # Update existing activity
            existing_activity.title = event.title.replace('Maintenance: ', '') if event.title.startswith('Maintenance: ') else event.title
            existing_activity.description = event.description
            existing_activity.scheduled_start = django_timezone.make_aware(
                datetime.combine(event.event_date, event.start_time or time(9, 0))
            )
            if event.end_time:
                existing_activity.scheduled_end = django_timezone.make_aware(
                    datetime.combine(event.event_date, event.end_time)
                )
            else:
                existing_activity.scheduled_end = existing_activity.scheduled_start + django_timezone.timedelta(hours=2)
            
            existing_activity.assigned_to = event.assigned_to
            existing_activity.priority = event.priority
            existing_activity.updated_by = event.updated_by or event.created_by
            existing_activity.save()
            logger.info(f"Updated maintenance activity for calendar event: {event.title}")
            return existing_activity
        else:
            # Get or create default activity type
            activity_type, created = MaintenanceActivityType.objects.get_or_create(
                name='General Maintenance',
                defaults={
                    'description': 'General maintenance activity created from calendar event',
                    'estimated_duration_hours': 2,
                    'frequency_days': 365,
                    'is_mandatory': False,
                    'created_by': event.created_by,
                }
            )
            
            # Create maintenance activity
            scheduled_start = django_timezone.make_aware(
                datetime.combine(event.event_date, event.start_time or time(9, 0))
            )
            
            if event.end_time:
                scheduled_end = django_timezone.make_aware(
                    datetime.combine(event.event_date, event.end_time)
                )
            else:
                scheduled_end = scheduled_start + django_timezone.timedelta(hours=activity_type.estimated_duration_hours)
            
            activity = MaintenanceActivity.objects.create(
                equipment=event.equipment,
                activity_type=activity_type,
                title=event.title.replace('Maintenance: ', '') if event.title.startswith('Maintenance: ') else event.title,
                description=event.description,
                scheduled_start=scheduled_start,
                scheduled_end=scheduled_end,
                assigned_to=event.assigned_to,
                priority=event.priority,
                status='scheduled',
                created_by=event.created_by
            )
            
            # Link the calendar event to the maintenance activity
            event.maintenance_activity = activity
            event.save()
            
            logger.info(f"Created maintenance activity for calendar event: {event.title}")
            return activity
            
    except Exception as e:
        logger.error(f"Error creating/updating maintenance activity for event {event.id}: {str(e)}")
        return None


def generate_ical_feed(request):
    """Generate iCal feed for calendar events."""
    from django.http import HttpResponse
    
    # Get filter parameters
    site_id = request.GET.get('site_id')
    equipment_id = request.GET.get('equipment_id')
    
    # Base queryset
    events = CalendarEvent.objects.select_related('equipment', 'equipment__location').all()
    
    # Apply filters
    if site_id:
        events = events.filter(
            Q(equipment__location__parent_location_id=site_id) | 
            Q(equipment__location_id=site_id)
        )
    
    if equipment_id:
        events = events.filter(equipment_id=equipment_id)
    
    # Generate iCal content
    ical_content = "BEGIN:VCALENDAR\r\n"
    ical_content += "VERSION:2.0\r\n"
    ical_content += "PRODID:-//SOLUNA Maintenance Dashboard//EN\r\n"
    ical_content += "CALSCALE:GREGORIAN\r\n"
    ical_content += "METHOD:PUBLISH\r\n"
    ical_content += f"X-WR-CALNAME:SOLUNA Maintenance Events\r\n"
    ical_content += f"X-WR-CALDESC:Maintenance and equipment events from SOLUNA Dashboard\r\n"
    ical_content += f"X-WR-TIMEZONE:UTC\r\n"
    
    for event in events:
        ical_content += "BEGIN:VEVENT\r\n"
        ical_content += f"UID:{event.id}@soluna-maintenance.com\r\n"
        ical_content += f"DTSTAMP:{timezone.now().strftime('%Y%m%dT%H%M%SZ')}\r\n"
        
        # Format date/time
        if event.all_day:
            ical_content += f"DTSTART;VALUE=DATE:{event.event_date.strftime('%Y%m%d')}\r\n"
        else:
            start_dt = datetime.combine(event.event_date, event.start_time or datetime.min.time())
            ical_content += f"DTSTART:{start_dt.strftime('%Y%m%dT%H%M%S')}\r\n"
            
            if event.end_time:
                end_dt = datetime.combine(event.event_date, event.end_time)
                ical_content += f"DTEND:{end_dt.strftime('%Y%m%dT%H%M%S')}\r\n"
        
        ical_content += f"SUMMARY:{event.title}\r\n"
        
        # Description with equipment info
        description = f"Equipment: {event.equipment.name}\\n"
        description += f"Location: {event.equipment.location.get_full_path() if event.equipment.location else 'Unknown'}\\n"
        description += f"Type: {event.get_event_type_display()}\\n"
        description += f"Priority: {event.get_priority_display()}\\n"
        if event.assigned_to:
            description += f"Assigned to: {event.assigned_to.get_full_name()}\\n"
        if event.description:
            description += f"\\nDescription: {event.description}"
        
        ical_content += f"DESCRIPTION:{description}\r\n"
        ical_content += f"LOCATION:{event.equipment.location.get_full_path() if event.equipment.location else ''}\r\n"
        
        # Categories based on event type
        ical_content += f"CATEGORIES:MAINTENANCE,{event.event_type.upper()}\r\n"
        
        # Priority mapping (iCal uses 1-9 scale, 1=high, 9=low)
        priority_map = {'critical': '1', 'high': '3', 'medium': '5', 'low': '7'}
        ical_content += f"PRIORITY:{priority_map.get(event.priority, '5')}\r\n"
        
        # Status
        status_map = {'pending': 'TENTATIVE', 'in_progress': 'CONFIRMED', 'completed': 'CONFIRMED'}
        ical_content += f"STATUS:CONFIRMED\r\n"
        
        # Created/Modified timestamps
        ical_content += f"CREATED:{event.created_at.strftime('%Y%m%dT%H%M%SZ')}\r\n"
        ical_content += f"LAST-MODIFIED:{event.updated_at.strftime('%Y%m%dT%H%M%SZ')}\r\n"
        
        ical_content += "END:VEVENT\r\n"
    
    ical_content += "END:VCALENDAR\r\n"
    
    response = HttpResponse(ical_content, content_type='text/calendar; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="soluna_maintenance_events.ics"'
    return response


@csrf_exempt
@require_http_methods(["POST"])
def google_calendar_webhook(request):
    """Handle Google Calendar webhook notifications."""
    try:
        # Verify webhook (basic implementation - you may want to add proper verification)
        channel_id = request.headers.get('X-Goog-Channel-ID')
        resource_id = request.headers.get('X-Goog-Resource-ID')
        resource_state = request.headers.get('X-Goog-Resource-State')
        
        # Log the webhook for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Google Calendar webhook received: {resource_state} for channel {channel_id}")
        
        # Handle different resource states
        if resource_state == 'sync':
            # Initial sync message - acknowledge
            return HttpResponse('OK', status=200)
        elif resource_state in ['exists', 'not_exists']:
            # Event created/updated/deleted
            # Here you would implement logic to sync changes back to your system
            # This is a placeholder for more complex sync logic
            pass
        
        return HttpResponse('OK', status=200)
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Google Calendar webhook error: {str(e)}")
        return HttpResponse('Error', status=500)


@login_required
def calendar_settings(request):
    """Calendar integration settings page."""
    if request.method == 'POST':
        # Handle settings updates
        # This would store user preferences for calendar integration
        messages.success(request, 'Calendar settings updated successfully!')
        return redirect('events:calendar_settings')
    
    # Generate iCal feed URLs
    ical_feed_url = request.build_absolute_uri(reverse('events:ical_feed'))
    webhook_url = request.build_absolute_uri(reverse('events:google_calendar_webhook'))
    
    context = {
        'ical_feed_url': ical_feed_url,
        'webhook_url': webhook_url,
        'google_calendar_instructions': True,
    }
    return render(request, 'events/calendar_settings.html', context)


def index(request):
    return HttpResponse("Events index view")

@login_required
def calendar_view(request):
    """Display unified calendar view of events and maintenance activities."""
    # Get filter parameters
    selected_site_id = request.GET.get('site_id', request.session.get('selected_site_id'))
    event_type = request.GET.get('event_type', '')
    equipment_filter = request.GET.get('equipment', '')
    view_mode = request.GET.get('mode', 'calendar')

    # Get all sites for the site selector
    sites = Location.objects.filter(is_site=True, is_active=True).order_by('name')
    selected_site = None
    if selected_site_id:
        try:
            selected_site = sites.get(id=selected_site_id)
            request.session['selected_site_id'] = selected_site_id
        except Location.DoesNotExist:
            pass

    # Get equipment for filtering
    equipment_list = Equipment.objects.filter(is_active=True).order_by('name')
    if selected_site:
        equipment_list = equipment_list.filter(
            Q(location__parent_location=selected_site) | Q(location=selected_site)
        )

    # Get combined event types (both calendar events and maintenance activity types)
    event_types = list(CalendarEvent.EVENT_TYPES)
    
    # Add maintenance activity types
    try:
        from maintenance.models import MaintenanceActivityType
        maintenance_types = MaintenanceActivityType.objects.all()
        for activity_type in maintenance_types:
            event_types.append((f'maintenance_{activity_type.id}', f'Maintenance: {activity_type.name}'))
    except Exception as e:
        # If maintenance app is not available, continue without it
        pass

    # Default context - unified calendar
    context = {
        'sites': sites,
        'selected_site': selected_site,
        'equipment_list': equipment_list,
        'event_types': event_types,
        'priority_choices': CalendarEvent.PRIORITY_CHOICES,
        'selected_event_type': event_type,
        'selected_equipment': equipment_filter,
        'calendar_view': 'unified',  # Always unified now
        'view_mode': view_mode,
    }

    # Get counts for both types of data
    try:
        events = CalendarEvent.objects.select_related('equipment', 'equipment__location').all()
        context['events_count'] = events.count()
    except Exception as e:
        context['events_count'] = 0
        context['events_error'] = str(e)

    try:
        from maintenance.models import MaintenanceActivity
        activities = MaintenanceActivity.objects.select_related('equipment', 'activity_type').all()
        context['maintenance_count'] = activities.count()
    except Exception as e:
        context['maintenance_count'] = 0
        context['maintenance_error'] = str(e)

    # Total count
    context['total_count'] = context.get('events_count', 0) + context.get('maintenance_count', 0)

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
            
            # Create corresponding maintenance activity if this is a maintenance event
            if event_type == 'maintenance':
                maintenance_activity = create_maintenance_activity_for_event(event)
                if maintenance_activity:
                    messages.success(request, f'Event "{title}" created successfully and linked to maintenance activity!')
                else:
                    messages.success(request, f'Event "{title}" created successfully!')
                    messages.warning(request, 'Could not create corresponding maintenance activity. Please check logs.')
            else:
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
            
            # Update corresponding maintenance activity if this is a maintenance event
            if event.event_type == 'maintenance':
                maintenance_activity = create_maintenance_activity_for_event(event)
                if maintenance_activity:
                    messages.success(request, f'Event "{event.title}" updated successfully! Maintenance activity synchronized.')
                else:
                    messages.success(request, f'Event "{event.title}" updated successfully!')
                    messages.warning(request, 'Could not synchronize maintenance activity. Please check logs.')
            else:
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


@login_required
@require_http_methods(["GET"])
def fetch_unified_events(request):
    """API endpoint to fetch both events and maintenance activities for unified calendar display."""
    try:
        start_date = request.GET.get('start')
        end_date = request.GET.get('end')
        equipment_filter = request.GET.get('equipment')
        event_type_filter = request.GET.get('event_type')
        site_id = request.GET.get('site_id')
        
        calendar_events = []
        
        # Fetch Calendar Events
        try:
            events = CalendarEvent.objects.select_related('equipment', 'equipment__location')
            
            # Date filtering
            if start_date and end_date:
                try:
                    start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                    events = events.filter(
                        event_date__gte=start_dt.date(),
                        event_date__lte=end_dt.date()
                    )
                except ValueError:
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
            if event_type_filter and not event_type_filter.startswith('maintenance_'):
                events = events.filter(event_type=event_type_filter)
            
            # Convert to FullCalendar format
            for event in events:
                try:
                    title = event.title
                    if event.equipment:
                        title = f"{event.title} - {event.equipment.name}"
                    
                    calendar_event = {
                        'id': f'event_{event.id}',
                        'title': title,
                        'start': str(event.event_date),
                        'allDay': event.all_day,
                        'backgroundColor': get_event_color(event.event_type, event.priority),
                        'borderColor': get_event_color(event.event_type, event.priority),
                        'textColor': '#ffffff',
                        'url': f"/events/events/{event.id}/",
                        'extendedProps': {
                            'type': 'event',
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
                    print(f"Error processing event {event.id}: {str(e)}")
                    continue
        except Exception as e:
            print(f"Error fetching events: {str(e)}")
        
        # Fetch Maintenance Activities
        try:
            from maintenance.models import MaintenanceActivity
            activities = MaintenanceActivity.objects.select_related('equipment', 'activity_type', 'assigned_to')
            
            # Date filtering
            if start_date and end_date:
                activities = activities.filter(
                    scheduled_start__date__gte=start_date,
                    scheduled_end__date__lte=end_date
                )
            
            # Site filtering
            if site_id:
                activities = activities.filter(
                    Q(equipment__location__parent_location_id=site_id) |
                    Q(equipment__location_id=site_id)
                )
            
            # Equipment filtering
            if equipment_filter:
                activities = activities.filter(equipment_id=equipment_filter)
            
            # Activity type filtering
            if event_type_filter and event_type_filter.startswith('maintenance_'):
                activity_type_id = event_type_filter.replace('maintenance_', '')
                activities = activities.filter(activity_type_id=activity_type_id)
            
            # Convert to FullCalendar format
            for activity in activities:
                try:
                    title = activity.title
                    if activity.equipment:
                        title = f"{activity.title} - {activity.equipment.name}"
                    
                    # Determine color based on status
                    if activity.status == 'scheduled':
                        bg_color = '#4299e1'
                    elif activity.status == 'overdue':
                        bg_color = '#dc3545'
                    elif activity.status == 'completed':
                        bg_color = '#28a745'
                    elif activity.status == 'in_progress':
                        bg_color = '#ffc107'
                    else:
                        bg_color = '#6c757d'
                    
                    calendar_event = {
                        'id': f'activity_{activity.id}',
                        'title': title,
                        'start': activity.scheduled_start.isoformat(),
                        'end': activity.scheduled_end.isoformat() if activity.scheduled_end else None,
                        'allDay': False,
                        'backgroundColor': bg_color,
                        'borderColor': '#2d3748',
                        'textColor': '#ffffff',
                        'url': f"/maintenance/activity/{activity.id}/",
                        'extendedProps': {
                            'type': 'maintenance',
                            'equipment': activity.equipment.name if activity.equipment else 'No equipment',
                            'location': activity.equipment.location.name if activity.equipment and activity.equipment.location else 'No location',
                            'priority': activity.priority,
                            'activity_type': activity.activity_type.name if activity.activity_type else 'N/A',
                            'assigned_to': activity.assigned_to.get_full_name() if activity.assigned_to else 'Unassigned',
                            'is_completed': activity.status == 'completed',
                            'status': activity.status,
                        }
                    }
                    
                    calendar_events.append(calendar_event)
                except Exception as e:
                    print(f"Error processing activity {activity.id}: {str(e)}")
                    continue
        except Exception as e:
            print(f"Error fetching maintenance activities: {str(e)}")
        
        return JsonResponse(calendar_events, safe=False)
    
    except Exception as e:
        import traceback
        print(f"Error in fetch_unified_events: {str(e)}")
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
        'assigned_to_id': event.assigned_to.id if event.assigned_to else None,
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


@login_required
@require_http_methods(["POST"])
def create_event_ajax(request):
    """AJAX endpoint to create a new event from calendar popup."""
    try:
        # Get form data
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        event_type = request.POST.get('event_type')
        equipment_id = request.POST.get('equipment')
        event_date = request.POST.get('event_date')
        start_time = request.POST.get('start_time') or None
        end_time = request.POST.get('end_time') or None
        all_day = request.POST.get('all_day') == 'on'
        priority = request.POST.get('priority', 'medium')
        assigned_to_id = request.POST.get('assigned_to') or None
        
        # Validate required fields
        if not title or not equipment_id or not event_date:
            return JsonResponse({
                'success': False,
                'error': 'Title, equipment, and event date are required.'
            })
        
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
        
        # Create corresponding maintenance activity if this is a maintenance event
        message = f'Event "{title}" created successfully!'
        if event_type == 'maintenance':
            maintenance_activity = create_maintenance_activity_for_event(event)
            if maintenance_activity:
                message = f'Event "{title}" created successfully and linked to maintenance activity!'
        
        return JsonResponse({
            'success': True,
            'message': message,
            'event_id': event.id
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error creating event: {str(e)}'
        })


@login_required
@require_http_methods(["POST"])
def update_event_ajax(request, event_id):
    """AJAX endpoint to update an existing event from calendar popup."""
    try:
        event = get_object_or_404(CalendarEvent, id=event_id)
        
        # Update event fields
        event.title = request.POST.get('title')
        event.description = request.POST.get('description', '')
        event.event_type = request.POST.get('event_type')
        event.equipment_id = request.POST.get('equipment')
        event.event_date = request.POST.get('event_date')
        event.start_time = request.POST.get('start_time') or None
        event.end_time = request.POST.get('end_time') or None
        event.all_day = request.POST.get('all_day') == 'on'
        event.priority = request.POST.get('priority', 'medium')
        event.assigned_to_id = request.POST.get('assigned_to') or None
        event.updated_by = request.user
        event.save()
        
        # Update corresponding maintenance activity if this is a maintenance event
        message = f'Event "{event.title}" updated successfully!'
        if event.event_type == 'maintenance':
            maintenance_activity = create_maintenance_activity_for_event(event)
            if maintenance_activity:
                message = f'Event "{event.title}" updated successfully! Maintenance activity synchronized.'
        
        return JsonResponse({
            'success': True,
            'message': message,
            'event_id': event.id
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error updating event: {str(e)}'
        })


@login_required
@require_http_methods(["GET"])
def get_form_data(request):
    """AJAX endpoint to get form data for event creation/editing."""
    try:
        # Get equipment and users for the form
        equipment_list = Equipment.objects.filter(is_active=True).order_by('name')
        from django.contrib.auth.models import User
        users = User.objects.filter(is_active=True).order_by('first_name', 'last_name')
        
        # Get site filter if provided
        site_id = request.GET.get('site_id')
        if site_id:
            equipment_list = equipment_list.filter(
                Q(location__parent_location_id=site_id) | Q(location_id=site_id)
            )
        
        equipment_data = []
        for equipment in equipment_list:
            equipment_data.append({
                'id': equipment.id,
                'name': equipment.name,
                'location': equipment.location.name if equipment.location else ''
            })
        
        users_data = []
        for user in users:
            users_data.append({
                'id': user.id,
                'name': user.get_full_name() or user.username
            })
        
        return JsonResponse({
            'success': True,
            'equipment': equipment_data,
            'users': users_data,
            'event_types': CalendarEvent.EVENT_TYPES,
            'priority_choices': CalendarEvent.PRIORITY_CHOICES,
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error fetching form data: {str(e)}'
        })


@login_required
def test_application_health(request):
    """Comprehensive test endpoint to check all application components."""
    try:
        results = {
            'success': True,
            'timestamp': timezone.now().isoformat(),
            'user': request.user.username,
            'components': {}
        }
        
        # Test Events
        try:
            events = CalendarEvent.objects.select_related('equipment', 'equipment__location').all()
            events_data = []
            for event in events[:5]:  # Limit to first 5 for testing
                events_data.append({
                    'id': event.id,
                    'title': event.title,
                    'event_date': str(event.event_date),
                    'equipment': event.equipment.name if event.equipment else 'No equipment',
                    'event_type': event.event_type,
                })
            
            results['components']['events'] = {
                'status': 'success',
                'count': events.count(),
                'sample_data': events_data,
                'error': None
            }
        except Exception as e:
            results['components']['events'] = {
                'status': 'error',
                'count': 0,
                'sample_data': [],
                'error': str(e)
            }
        
        # Test Maintenance Activities
        try:
            from maintenance.models import MaintenanceActivity
            activities = MaintenanceActivity.objects.select_related('equipment', 'activity_type').all()
            activities_data = []
            for activity in activities[:5]:  # Limit to first 5 for testing
                activities_data.append({
                    'id': activity.id,
                    'title': activity.title,
                    'scheduled_start': str(activity.scheduled_start),
                    'equipment': activity.equipment.name if activity.equipment else 'No equipment',
                    'status': activity.status,
                })
            
            results['components']['maintenance_activities'] = {
                'status': 'success',
                'count': activities.count(),
                'sample_data': activities_data,
                'error': None
            }
        except Exception as e:
            results['components']['maintenance_activities'] = {
                'status': 'error',
                'count': 0,
                'sample_data': [],
                'error': str(e)
            }
        
        # Test Equipment
        try:
            from equipment.models import Equipment
            equipment = Equipment.objects.select_related('location', 'category').all()
            equipment_data = []
            for eq in equipment[:5]:  # Limit to first 5 for testing
                equipment_data.append({
                    'id': eq.id,
                    'name': eq.name,
                    'location': eq.location.name if eq.location else 'No location',
                    'category': eq.category.name if eq.category else 'No category',
                })
            
            results['components']['equipment'] = {
                'status': 'success',
                'count': equipment.count(),
                'sample_data': equipment_data,
                'error': None
            }
        except Exception as e:
            results['components']['equipment'] = {
                'status': 'error',
                'count': 0,
                'sample_data': [],
                'error': str(e)
            }
        
        # Test Locations
        try:
            from core.models import Location
            locations = Location.objects.all()
            locations_data = []
            for loc in locations[:5]:  # Limit to first 5 for testing
                locations_data.append({
                    'id': loc.id,
                    'name': loc.name,
                    'is_site': loc.is_site,
                    'parent': loc.parent_location.name if loc.parent_location else 'None',
                })
            
            results['components']['locations'] = {
                'status': 'success',
                'count': locations.count(),
                'sample_data': locations_data,
                'error': None
            }
        except Exception as e:
            results['components']['locations'] = {
                'status': 'error',
                'count': 0,
                'sample_data': [],
                'error': str(e)
            }
        
        # Test Users
        try:
            from django.contrib.auth.models import User
            users = User.objects.filter(is_active=True)
            users_data = []
            for user in users[:5]:  # Limit to first 5 for testing
                users_data.append({
                    'id': user.id,
                    'username': user.username,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'is_staff': user.is_staff,
                })
            
            results['components']['users'] = {
                'status': 'success',
                'count': users.count(),
                'sample_data': users_data,
                'error': None
            }
        except Exception as e:
            results['components']['users'] = {
                'status': 'error',
                'count': 0,
                'sample_data': [],
                'error': str(e)
            }
        
        # Test Maintenance Activity Types
        try:
            from maintenance.models import MaintenanceActivityType
            activity_types = MaintenanceActivityType.objects.select_related('category').all()
            activity_types_data = []
            for at in activity_types[:5]:  # Limit to first 5 for testing
                activity_types_data.append({
                    'id': at.id,
                    'name': at.name,
                    'category': at.category.name if at.category else 'No category',
                    'frequency_days': at.frequency_days,
                })
            
            results['components']['maintenance_activity_types'] = {
                'status': 'success',
                'count': activity_types.count(),
                'sample_data': activity_types_data,
                'error': None
            }
        except Exception as e:
            results['components']['maintenance_activity_types'] = {
                'status': 'error',
                'count': 0,
                'sample_data': [],
                'error': str(e)
            }
        
        # Test Equipment Categories
        try:
            from core.models import EquipmentCategory
            equipment_categories = EquipmentCategory.objects.all()
            equipment_categories_data = []
            for ec in equipment_categories[:5]:  # Limit to first 5 for testing
                equipment_categories_data.append({
                    'id': ec.id,
                    'name': ec.name,
                    'description': ec.description,
                })
            
            results['components']['equipment_categories'] = {
                'status': 'success',
                'count': equipment_categories.count(),
                'sample_data': equipment_categories_data,
                'error': None
            }
        except Exception as e:
            results['components']['equipment_categories'] = {
                'status': 'error',
                'count': 0,
                'sample_data': [],
                'error': str(e)
            }
        
        # Test Database Connection
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                db_test = cursor.fetchone()
            
            results['components']['database'] = {
                'status': 'success',
                'connection_test': db_test[0] if db_test else None,
                'error': None
            }
        except Exception as e:
            results['components']['database'] = {
                'status': 'error',
                'connection_test': None,
                'error': str(e)
            }
        
        # Test Unified Calendar API
        try:
            # Test the unified fetch function directly
            test_request = request
            test_request.GET = request.GET.copy()
            test_request.GET['start'] = '2025-01-01'
            test_request.GET['end'] = '2025-12-31'
            
            unified_response = fetch_unified_events(test_request)
            unified_data = json.loads(unified_response.content)
            
            results['components']['unified_calendar_api'] = {
                'status': 'success',
                'response_status': unified_response.status_code,
                'events_count': len(unified_data) if isinstance(unified_data, list) else 0,
                'sample_events': unified_data[:3] if isinstance(unified_data, list) else [],
                'error': None
            }
        except Exception as e:
            results['components']['unified_calendar_api'] = {
                'status': 'error',
                'response_status': None,
                'events_count': 0,
                'sample_events': [],
                'error': str(e)
            }
        
        return JsonResponse(results)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'timestamp': timezone.now().isoformat(),
            'user': request.user.username if request.user.is_authenticated else 'anonymous'
        }, status=500)