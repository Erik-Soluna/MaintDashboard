"""profile_settings views (split from the original monolithic views.py)."""
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
def profile_view(request):
    """User profile view."""
    # Ensure user has a profile
    from core.models import UserProfile
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        action = request.POST.get('action', 'update_profile')
        
        if action == 'update_profile':
            user = request.user
            user.first_name = request.POST.get('first_name', '')
            user.last_name = request.POST.get('last_name', '')
            user.email = request.POST.get('email', '')
            user.save()
            
            profile = user.userprofile
            profile.phone_number = request.POST.get('phone_number', '')
            profile.department = request.POST.get('department', '')
            
            # Handle default site selection
            default_site_id = request.POST.get('default_site')
            if default_site_id:
                try:
                    profile.default_site = Location.objects.get(id=default_site_id, is_site=True)
                except Location.DoesNotExist:
                    profile.default_site = None
            else:
                profile.default_site = None
            
            # Handle default location selection
            default_location_id = request.POST.get('default_location')
            if default_location_id:
                try:
                    profile.default_location = Location.objects.get(id=default_location_id)
                except Location.DoesNotExist:
                    profile.default_location = None
            else:
                profile.default_location = None
            
            # Handle theme preference
            theme_preference = request.POST.get('theme_preference', 'dark')
            if theme_preference in ['dark', 'light']:
                profile.theme_preference = theme_preference
            
            # Handle timezone preference
            timezone = request.POST.get('timezone', 'America/Chicago')
            if timezone in [choice[0] for choice in profile.TIMEZONE_CHOICES]:
                profile.timezone = timezone
            
            # Handle notification preferences
            profile.notifications_enabled = 'notifications_enabled' in request.POST
            profile.email_notifications = 'email_notifications' in request.POST
            profile.sms_notifications = 'sms_notifications' in request.POST
            
            profile.save()
            
            messages.success(request, 'Profile updated successfully!')
            return redirect('core:profile')
            
        elif action == 'change_password':
            from django.contrib.auth import update_session_auth_hash
            from django.contrib.auth.forms import PasswordChangeForm
            
            form = PasswordChangeForm(request.user, request.POST)
            if form.is_valid():
                user = form.save()
                update_session_auth_hash(request, user)  # Important for keeping user logged in
                messages.success(request, 'Password changed successfully!')
                return redirect('core:profile')
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f'{field}: {error}')
    
    # Get data for the template
    sites = Location.objects.filter(is_site=True, is_active=True).order_by('name')
    locations = Location.objects.filter(is_active=True).order_by('name')
    
    context = {
        'user': request.user,
        'sites': sites,
        'locations': locations,
        'timezone_choices': profile.TIMEZONE_CHOICES,
    }
    return render(request, 'core/profile.html', context)


@login_required
@user_passes_test(is_staff_or_superuser)
def settings_view(request):
    # Fetch health data from the health_check view
    from django.test import RequestFactory
    from .health import health_check  # lazy import avoids a circular import with health.py
    rf = RequestFactory()
    health_response = health_check(rf.get('/core/health/'))
    health_data = health_response.content.decode('utf-8')
    import json
    health = json.loads(health_data)
    
    # Get Docker logs configuration
    from core.services.docker_logs_service import DockerLogsService
    docker_service = DockerLogsService()
    
    context = {
        'health': health,
        'docker_logs_enabled': docker_service.is_enabled(),
        'docker_logs_debug_only': docker_service.is_debug_only(),
    }
    return render(request, 'core/settings.html', context)


@login_required
def profile(request):
    """Alias for profile_view to match URL pattern."""
    return profile_view(request)


@login_required
@user_passes_test(is_staff_or_superuser)
def settings(request):
    """Alias for settings_view to match URL pattern."""
    return settings_view(request)


@login_required
@require_http_methods(["POST"])
def update_user_timezone(request):
    """API endpoint to update user's timezone preference."""
    try:
        data = json.loads(request.body)
        timezone = data.get('timezone')
        
        if not timezone:
            return JsonResponse({
                'success': False,
                'error': 'Timezone is required'
            }, status=400)
        
        # Validate timezone against allowed choices
        valid_timezones = [choice[0] for choice in UserProfile.TIMEZONE_CHOICES]
        if timezone not in valid_timezones:
            return JsonResponse({
                'success': False,
                'error': f'Invalid timezone: {timezone}'
            }, status=400)
        
        # Get or create user profile
        user_profile, created = UserProfile.objects.get_or_create(
            user=request.user,
            defaults={'timezone': timezone}
        )
        
        if not created:
            user_profile.timezone = timezone
            user_profile.save()
        
        logger.info(f"Updated timezone for user {request.user.username} to {timezone}")
        
        return JsonResponse({
            'success': True,
            'message': f'Timezone updated to {timezone}',
            'timezone': timezone
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f"Error updating user timezone: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


__all__ = ["profile_view", "settings_view", "profile", "settings", "update_user_timezone"]
