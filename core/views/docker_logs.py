"""docker_logs views (split from the original monolithic views.py)."""
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
@user_passes_test(is_staff_or_superuser)
def docker_logs_view(request):
    """View for displaying Docker logs - toggle controlled."""
    from core.services.docker_logs_service import DockerLogsService
    
    service = DockerLogsService()
    if not service.can_access(request.user):
        return redirect('core:dashboard')
    
    context = {
        'docker_logs_enabled': service.is_enabled(),
        'docker_logs_debug_only': service.is_debug_only(),
    }
    return render(request, 'core/docker_logs.html', context)


@login_required
@user_passes_test(is_staff_or_superuser)
@require_http_methods(["GET"])
def get_docker_logs_api(request):
    """API endpoint to fetch Docker logs using service layer."""
    from core.services.docker_logs_service import DockerLogsService
    
    service = DockerLogsService()
    
    # Check access permissions
    if not service.can_access(request.user):
        return JsonResponse({
            'error': 'Access denied'
        }, status=403)
    
    # Get parameters
    container_name = request.GET.get('container', '')
    lines = int(request.GET.get('lines', 100))
    follow = request.GET.get('follow', 'false').lower() == 'true'
    
    # Get logs using service
    result = service.get_logs(request.user, container_name, lines, follow)
    
    # Return appropriate response
    if result['success']:
        return JsonResponse(result)
    else:
        return JsonResponse(result, status=500)


@login_required
@user_passes_test(is_staff_or_superuser)
@require_http_methods(["GET"])
def get_docker_containers_api(request):
    """API endpoint to get list of running Docker containers using service layer."""
    from core.services.docker_logs_service import DockerLogsService
    
    service = DockerLogsService()
    
    # Check access permissions
    if not service.can_access(request.user):
        return JsonResponse({
            'error': 'Access denied'
        }, status=403)
    
    # Get containers using service
    result = service.get_containers(request.user)
    
    # Return appropriate response
    if result['success']:
        return JsonResponse(result)
    else:
        return JsonResponse(result, status=500)


@login_required
@user_passes_test(is_staff_or_superuser)
@require_http_methods(["GET"])
def get_aggregated_logs_api(request):
    """API endpoint to get aggregated logs from multiple containers."""
    from core.services.log_streaming_service import LogStreamingService
    
    # Get parameters
    containers = request.GET.get('containers', '').split(',') if request.GET.get('containers') else None
    lines = int(request.GET.get('lines', 100))
    
    # Validate lines parameter
    if lines > 1000:
        lines = 1000
    
    try:
        streaming_service = LogStreamingService()
        logs_content = streaming_service.get_aggregated_logs(containers, lines)
        
        return JsonResponse({
            'success': True,
            'logs': logs_content,
            'containers': containers or [],
            'lines_returned': len(logs_content.splitlines())
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error getting aggregated logs: {str(e)}'
        }, status=500)


@login_required
@user_passes_test(is_staff_or_superuser)
@require_http_methods(["GET"])
def get_system_logs_api(request):
    """API endpoint to get system logs."""
    from core.services.log_streaming_service import LogStreamingService
    
    # Get parameters
    lines = int(request.GET.get('lines', 100))
    
    # Validate lines parameter
    if lines > 1000:
        lines = 1000
    
    try:
        streaming_service = LogStreamingService()
        logs_content = streaming_service.get_system_logs(lines)
        
        return JsonResponse({
            'success': True,
            'logs': logs_content,
            'lines_returned': len(logs_content.splitlines())
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error getting system logs: {str(e)}'
        }, status=500)


@login_required
@user_passes_test(is_staff_or_superuser)
@require_http_methods(["POST"])
def start_log_stream_api(request):
    """API endpoint to start a real-time log stream."""
    from core.services.log_streaming_service import LogStreamingService
    import json
    
    try:
        data = json.loads(request.body)
        containers = data.get('containers', [])
        
        streaming_service = LogStreamingService()
        stream_id = streaming_service.start_log_stream(request.user, containers)
        
        return JsonResponse({
            'success': True,
            'stream_id': stream_id,
            'message': 'Log stream started successfully'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error starting log stream: {str(e)}'
        }, status=500)


@login_required
@user_passes_test(is_staff_or_superuser)
@require_http_methods(["POST"])
def stop_log_stream_api(request):
    """API endpoint to stop a log stream."""
    from core.services.log_streaming_service import LogStreamingService
    import json
    
    try:
        data = json.loads(request.body)
        stream_id = data.get('stream_id')
        
        if not stream_id:
            return JsonResponse({
                'success': False,
                'error': 'Stream ID is required'
            }, status=400)
        
        streaming_service = LogStreamingService()
        streaming_service.stop_log_stream(stream_id)
        
        return JsonResponse({
            'success': True,
            'message': 'Log stream stopped successfully'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error stopping log stream: {str(e)}'
        }, status=500)


__all__ = ["docker_logs_view", "get_docker_logs_api", "get_docker_containers_api", "get_aggregated_logs_api", "get_system_logs_api", "start_log_stream_api", "stop_log_stream_api"]
