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
from django.utils import timezone


@login_required
def dashboard(request):
    """Dashboard view with summary statistics."""
    context = {
        'total_equipment': Equipment.objects.count(),
        'active_equipment': Equipment.objects.filter(is_active=True).count(),
        'pending_maintenance': MaintenanceActivity.objects.filter(
            status='pending'
        ).count(),
        'upcoming_events': CalendarEvent.objects.filter(
            event_date__gte=timezone.now().date()
        ).order_by('event_date')[:5],
        'recent_equipment': Equipment.objects.order_by('-created_at')[:5],
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