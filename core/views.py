"""
Views for core app.
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from equipment.models import Equipment
from maintenance.models import MaintenanceActivity
from events.models import CalendarEvent
from core.models import Location
from django.utils import timezone
from django.db.models import Q, Count
from datetime import datetime, timedelta, date


@login_required
def dashboard(request):
    """Enhanced dashboard view with location-based data layout."""
    
    # Get selected site from session or request
    selected_site_id = request.GET.get('site_id', request.session.get('selected_site_id'))
    if selected_site_id:
        request.session['selected_site_id'] = selected_site_id
    
    # Get all sites for the site selector
    sites = Location.objects.filter(is_site=True, is_active=True).order_by('name')
    selected_site = None
    if selected_site_id:
        try:
            selected_site = sites.get(id=selected_site_id)
        except Location.DoesNotExist:
            pass
    
    # Get locations to display (filtered by site if selected)
    if selected_site:
        locations = Location.objects.filter(
            Q(parent_location=selected_site) | Q(id=selected_site.id),
            is_active=True
        ).order_by('name')
    else:
        # Show all non-site locations if no specific site selected
        locations = Location.objects.filter(
            is_site=False, 
            is_active=True
        ).order_by('name')[:5]  # Limit to 5 for layout
    
    # Get urgent items (overdue or due soon)
    today = timezone.now().date()
    urgent_cutoff = today + timedelta(days=7)  # Items due within 7 days
    
    urgent_items = MaintenanceActivity.objects.filter(
        Q(scheduled_end__lte=urgent_cutoff) & Q(scheduled_end__gte=today),
        status__in=['pending', 'in_progress']
    ).select_related('equipment', 'equipment__location').order_by('scheduled_end')[:10]
    
    # Get upcoming items (due within next 30 days)
    upcoming_cutoff = today + timedelta(days=30)
    upcoming_items = MaintenanceActivity.objects.filter(
        scheduled_end__gt=urgent_cutoff,
        scheduled_end__lte=upcoming_cutoff,
        status__in=['pending', 'scheduled']
    ).select_related('equipment', 'equipment__location').order_by('scheduled_end')[:10]
    
    # Build location-based data
    location_data = []
    for location in locations:
        # Get scheduled downtimes for this location
        downtimes = MaintenanceActivity.objects.filter(
            equipment__location=location,
            status__in=['scheduled', 'in_progress'],
            scheduled_end__gte=today
        ).select_related('equipment').order_by('scheduled_start')[:5]
        
        # Get equipment in repair for this location
        equipment_in_repair = Equipment.objects.filter(
            location=location,
            status='maintenance'
        ).order_by('name')[:5]
        
        location_data.append({
            'location': location,
            'downtimes': downtimes,
            'equipment_in_repair': equipment_in_repair,
        })
    
    context = {
        'sites': sites,
        'selected_site': selected_site,
        'locations': locations,
        'location_data': location_data,
        'urgent_items': urgent_items,
        'upcoming_items': upcoming_items,
        'total_equipment': Equipment.objects.count(),
        'active_equipment': Equipment.objects.filter(is_active=True).count(),
        'pending_maintenance': MaintenanceActivity.objects.filter(
            status='pending'
        ).count(),
    }
    return render(request, 'core/dashboard.html', context)


@login_required
def profile_view(request):
    """User profile view."""
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', '')
        user.save()
        
        profile = user.userprofile
        profile.phone_number = request.POST.get('phone_number', '')
        profile.department = request.POST.get('department', '')
        profile.save()
        
        messages.success(request, 'Profile updated successfully!')
        return redirect('core:profile')
    
    return render(request, 'core/profile.html', {'user': request.user})