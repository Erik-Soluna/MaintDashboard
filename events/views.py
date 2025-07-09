from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods

# Create your views here.

def index(request):
    return HttpResponse("Events index view")

def calendar_view(request):
    """Display calendar view of events"""
    return render(request, 'events/calendar.html')

def event_list(request):
    """Display list of events"""
    return render(request, 'events/event_list.html')

def add_event(request):
    """Add a new event"""
    if request.method == 'POST':
        # Handle event creation
        return JsonResponse({'status': 'success'})
    return render(request, 'events/add_event.html')

def event_detail(request, event_id):
    """Display event details"""
    return render(request, 'events/event_detail.html', {'event_id': event_id})

def edit_event(request, event_id):
    """Edit an existing event"""
    if request.method == 'POST':
        # Handle event update
        return JsonResponse({'status': 'success'})
    return render(request, 'events/edit_event.html', {'event_id': event_id})

def complete_event(request, event_id):
    """Mark an event as complete"""
    if request.method == 'POST':
        # Handle event completion
        return JsonResponse({'status': 'success'})
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@require_http_methods(["GET"])
def fetch_events(request):
    """API endpoint to fetch events"""
    # Return events as JSON for calendar/AJAX requests
    events = []  # Replace with actual event data
    return JsonResponse({'events': events})

@require_http_methods(["GET"])
def get_event(request, event_id):
    """API endpoint to get a specific event"""
    # Return specific event as JSON
    return JsonResponse({'event_id': event_id, 'status': 'placeholder'})

def equipment_events(request, equipment_id):
    """Display events for specific equipment"""
    return render(request, 'events/equipment_events.html', {'equipment_id': equipment_id})