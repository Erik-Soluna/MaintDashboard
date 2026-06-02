"""debug_data views (split from the original monolithic views.py)."""
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
@user_passes_test(lambda u: u.is_superuser)
def clear_maintenance_data(request):
    """Clear all maintenance activities and calendar events (superuser only)."""
    if request.method == 'POST':
        try:
            from django.db import transaction
            from maintenance.models import MaintenanceActivity, MaintenanceSchedule
            from events.models import CalendarEvent
            
            with transaction.atomic():
                # Count existing records
                activity_count = MaintenanceActivity.objects.count()
                event_count = CalendarEvent.objects.count()
                schedule_count = MaintenanceSchedule.objects.count()
                
                # Delete calendar events first (they reference maintenance activities)
                if event_count > 0:
                    CalendarEvent.objects.all().delete()
                
                # Delete maintenance activities
                if activity_count > 0:
                    MaintenanceActivity.objects.all().delete()
                
                # Delete maintenance schedules
                if schedule_count > 0:
                    MaintenanceSchedule.objects.all().delete()
                
                # Invalidate dashboard cache
                invalidate_dashboard_cache()
                
                messages.success(
                    request, 
                    f'Successfully cleared {activity_count} maintenance activities, '
                    f'{event_count} calendar events, and {schedule_count} maintenance schedules!'
                )
                
        except Exception as e:
            messages.error(request, f'Error clearing data: {str(e)}')
            
        return redirect('core:dashboard')
    
    # GET request - show confirmation page
    from maintenance.models import MaintenanceActivity, MaintenanceSchedule
    from events.models import CalendarEvent
    
    activity_count = MaintenanceActivity.objects.count()
    event_count = CalendarEvent.objects.count()
    schedule_count = MaintenanceSchedule.objects.count()
    
    context = {
        'activity_count': activity_count,
        'event_count': event_count,
        'schedule_count': schedule_count,
        'total_count': activity_count + event_count + schedule_count,
    }
    
    return render(request, 'core/clear_data_confirm.html', context)


@login_required
@user_passes_test(is_staff_or_superuser)
@require_http_methods(["POST"])
def generate_pdus(request):
    """Generate PDU equipment ("PDU {building}-{n}") under an MDC location.
    Wraps the create_pdus management command (always --apply from the UI)."""
    try:
        location_id = request.POST.get('location_id', '').strip()
        building_map = request.POST.get('map', '').strip()
        building = request.POST.get('building', '').strip()
        count = request.POST.get('count', '').strip()

        if not location_id:
            return JsonResponse({'success': False, 'error': 'Select a target MDC location.'}, status=400)
        if not building_map and not (building and count):
            return JsonResponse({'success': False, 'error': 'Provide a building:count map, or a building and count.'}, status=400)

        args = ['create_pdus', '--location-id', location_id, '--apply']
        if building_map:
            args += ['--map', building_map]
        else:
            args += ['--building', building, '--count', count]

        output = StringIO()
        call_command(*args, stdout=output, stderr=output, verbosity=2)
        result = output.getvalue()
        output.close()

        m = re.search(r'Created (\d+)', result)
        created_count = int(m.group(1)) if m else 0

        return JsonResponse({
            'success': True,
            'message': f'PDU generation complete! Created: {created_count} PDU(s).',
            'created_count': created_count,
            'output': result,
        })
    except Exception as e:
        import traceback
        return JsonResponse({
            'success': False,
            'error': f'Error generating PDUs: {str(e)}',
            'details': traceback.format_exc(),
        }, status=500)


@login_required
@user_passes_test(is_staff_or_superuser)
@require_http_methods(["POST"])
def generate_pods(request):
    """Generate PODs for selected sites or all sites."""
    try:
        from django.core.management import call_command
        from io import StringIO
        
        # Get parameters from the form
        site_id = request.POST.get('site_id', '').strip()
        pod_count = int(request.POST.get('pod_count', 11))
        mdcs_per_pod = int(request.POST.get('mdcs_per_pod', 2))
        force = request.POST.get('force', 'false').lower() == 'true'
        
        # Capture command output
        output = StringIO()
        
        # Build command arguments
        args = ['generate_pods']
        
        if site_id:
            # Generate for specific site
            args.extend(['--site-id', site_id])
        else:
            # Generate for all sites
            args.append('--all-sites')
        
        # Add other parameters
        args.extend(['--pod-count', str(pod_count)])
        args.extend(['--mdcs-per-pod', str(mdcs_per_pod)])
        
        if force:
            args.append('--force')
        
        # Call the generate pods command
        call_command(*args, stdout=output, verbosity=2)
        
        result = output.getvalue()
        output.close()
        
        # Parse the output to extract generated count
        generated_count = 0
        
        # Look for patterns in the output
        import re
        generated_matches = re.findall(r'Generated (\d+)', result)
        
        if generated_matches:
            generated_count = sum(int(x) for x in generated_matches)
        
        # Determine target description
        if site_id:
            try:
                site = Location.objects.get(id=site_id, is_site=True)
                target_desc = f"site '{site.name}'"
            except Location.DoesNotExist:
                target_desc = "selected site"
        else:
            target_desc = "all sites"
        
        return JsonResponse({
            'success': True,
            'message': f'POD generation completed successfully for {target_desc}! Generated: {generated_count} PODs',
            'generated_count': generated_count,
            'output': result
        })
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return JsonResponse({
            'success': False,
            'error': f'Error generating PODs: {str(e)}',
            'details': error_details
        }, status=500)


@login_required
@user_passes_test(is_staff_or_superuser)
@require_http_methods(["POST"])
def generate_mdcs(request):
    """Generate MDCs for existing PODs."""
    try:
        from django.contrib.auth.models import User
        
        # Get parameters from the form
        pod_id = request.POST.get('pod_id', '').strip()
        site_id = request.POST.get('site_id', '').strip()
        mdcs_per_pod = int(request.POST.get('mdcs_per_pod', 2))
        force = request.POST.get('force', 'false').lower() == 'true'
        
        # Get or create a system user for creating locations
        system_user, _ = User.objects.get_or_create(
            username='system',
            defaults={'email': 'system@maintenance.local', 'is_staff': True}
        )
        
        # Determine which PODs to process
        if pod_id:
            # Generate for specific POD
            try:
                pod = Location.objects.get(id=pod_id, is_site=False, parent_location__is_site=False)
                pods = [pod]
            except Location.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': f'POD with ID {pod_id} not found'
                }, status=404)
        elif site_id:
            # Generate for all PODs in a specific site
            try:
                site = Location.objects.get(id=site_id, is_site=True)
                pods = Location.objects.filter(
                    parent_location=site,
                    is_site=False,
                    is_active=True
                ).order_by('name')
            except Location.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': f'Site with ID {site_id} not found'
                }, status=404)
        else:
            # Generate for all PODs (PODs are locations that are not sites and whose parent is a site)
            pods = Location.objects.filter(
                is_site=False,
                parent_location__is_site=True,
                is_active=True
            ).order_by('parent_location__name', 'name')
        
        if not pods.exists():
            return JsonResponse({
                'success': False,
                'error': 'No PODs found to generate MDCs for'
            }, status=400)
        
        total_mdcs_created = 0
        output_lines = []
        
        # Process each POD
        for pod in pods:
            site = pod.parent_location
            pod_name = pod.name
            
            # Get existing MDCs for this POD to determine starting number
            existing_mdcs = Location.objects.filter(
                parent_location=pod,
                is_site=False,
                is_active=True
            ).order_by('name')
            
            # Determine starting MDC number
            if existing_mdcs.exists():
                # Find the highest MDC number
                max_mdc_num = 0
                for mdc in existing_mdcs:
                    # Extract number from name like "MDC 1", "MDC 2", etc.
                    import re
                    match = re.search(r'MDC\s+(\d+)', mdc.name, re.IGNORECASE)
                    if match:
                        max_mdc_num = max(max_mdc_num, int(match.group(1)))
                mdc_start = max_mdc_num + 1
            else:
                # No existing MDCs, start from 1
                mdc_start = 1
            
            mdc_end = mdc_start + mdcs_per_pod - 1
            
            # Generate MDCs for this POD
            for mdc_num in range(mdc_start, mdc_end + 1):
                mdc_name = f'MDC {mdc_num}'
                
                # Check if MDC already exists
                existing_mdc = Location.objects.filter(
                    name=mdc_name,
                    parent_location=pod,
                    is_site=False
                ).first()
                
                if existing_mdc and not force:
                    output_lines.append(f'MDC already exists: {site.name} > {pod_name} > {mdc_name} - skipping')
                    continue
                
                # Create or update MDC
                mdc, created = Location.objects.get_or_create(
                    name=mdc_name,
                    parent_location=pod,
                    defaults={
                        'is_site': False,
                        'created_by': system_user,
                        'updated_by': system_user,
                        'is_active': True
                    }
                )
                
                if created:
                    output_lines.append(f'Created MDC: {site.name} > {pod_name} > {mdc_name}')
                    total_mdcs_created += 1
                elif force:
                    mdc.updated_by = system_user
                    mdc.is_active = True
                    mdc.save()
                    output_lines.append(f'Updated existing MDC: {site.name} > {pod_name} > {mdc_name}')
                    total_mdcs_created += 1
        
        # Build result message
        if pod_id:
            target_desc = f"POD '{pods[0].name}'"
        elif site_id:
            target_desc = f"site '{site.name}'"
        else:
            target_desc = "all PODs"
        
        result = '\n'.join(output_lines) if output_lines else 'No MDCs were created (all already exist)'
        
        return JsonResponse({
            'success': True,
            'message': f'MDC generation completed successfully for {target_desc}! Generated: {total_mdcs_created} MDCs',
            'generated_count': total_mdcs_created,
            'output': result
        })
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return JsonResponse({
            'success': False,
            'error': f'Error generating MDCs: {str(e)}',
            'details': error_details
        }, status=500)


@login_required
@user_passes_test(is_staff_or_superuser)
@require_http_methods(["POST"])
def populate_demo_data(request):
    """Populate the database with comprehensive demo data."""
    try:
        from django.core.management import call_command
        from io import StringIO
        
        # Get parameters from request
        clear_first = request.POST.get('clear_first', 'false').lower() == 'true'
        include_maintenance = request.POST.get('include_maintenance', 'true').lower() == 'true'
        include_events = request.POST.get('include_events', 'true').lower() == 'true'
        
        # Capture command output
        output = StringIO()
        
        # Build command arguments
        args = ['populate_comprehensive_demo_data']
        
        if clear_first:
            args.append('--reset')
        
        if include_maintenance:
            args.append('--include-maintenance')
        
        if include_events:
            args.append('--include-events')
        
        # Call the comprehensive demo data command
        call_command(*args, stdout=output, verbosity=2)
        
        result = output.getvalue()
        output.close()
        
        # Parse the output to extract counts
        created_count = 0
        deleted_count = 0
        
        # Look for patterns in the output
        import re
        created_matches = re.findall(r'Created (\d+)', result)
        deleted_matches = re.findall(r'Deleted (\d+)', result)
        
        if created_matches:
            created_count = sum(int(x) for x in created_matches)
        if deleted_matches:
            deleted_count = sum(int(x) for x in deleted_matches)
        
        return JsonResponse({
            'success': True,
            'message': f'Demo data populated successfully! Created: {created_count} items, Deleted: {deleted_count} items',
            'created_count': created_count,
            'deleted_count': deleted_count,
            'output': result
        })
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return JsonResponse({
            'success': False,
            'error': f'Error populating demo data: {str(e)}',
            'details': error_details
        }, status=500)


@login_required
@user_passes_test(is_staff_or_superuser)
@require_http_methods(["POST"])
def clear_maintenance_activities(request):
    """Clear scheduled maintenance activities without wiping entire database (web interface version)."""
    try:
        from maintenance.models import MaintenanceActivity, MaintenanceSchedule
        import json
        
        # Safety check - only allow in debug mode or for superusers
        if not request.user.is_superuser:
            return JsonResponse({
                'success': False,
                'error': 'Only superusers can clear maintenance activities'
            }, status=403)
        
        # Get parameters
        clear_all = request.POST.get('clear_all', 'false').lower() == 'true'
        clear_schedules = request.POST.get('clear_schedules', 'false').lower() == 'true'
        dry_run = request.POST.get('dry_run', 'false').lower() == 'true'
        
        results = {
            'success': True,
            'dry_run': dry_run,
            'activities_deleted': 0,
            'schedules_deleted': 0,
            'message': ''
        }
        
        # Count what would be deleted
        if clear_all:
            # Clear ALL activities
            activities_query = MaintenanceActivity.objects.all()
        else:
            # Only clear scheduled/pending activities (not completed)
            activities_query = MaintenanceActivity.objects.filter(
                status__in=['scheduled', 'pending']
            )
        
        activities_count = activities_query.count()
        results['activities_deleted'] = activities_count
        
        if clear_schedules:
            schedules_query = MaintenanceSchedule.objects.all()
            schedules_count = schedules_query.count()
            results['schedules_deleted'] = schedules_count
        
        # Perform deletion if not dry run
        if not dry_run:
            deleted_activities = activities_query.delete()
            results['activities_deleted'] = deleted_activities[0] if deleted_activities else 0
            
            if clear_schedules:
                deleted_schedules = schedules_query.delete()
                results['schedules_deleted'] = deleted_schedules[0] if deleted_schedules else 0
            
            results['message'] = f'Successfully deleted {results["activities_deleted"]} activities'
            if clear_schedules:
                results['message'] += f' and {results["schedules_deleted"]} schedules'
        else:
            results['message'] = f'Dry run: Would delete {activities_count} activities'
            if clear_schedules:
                results['message'] += f' and {schedules_count} schedules'
        
        logger.info(f"Maintenance cleanup by {request.user.username}: {results['message']}")
        return JsonResponse(results)
        
    except Exception as e:
        logger.error(f"Error clearing maintenance activities: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@user_passes_test(is_staff_or_superuser)
@csrf_exempt
@require_http_methods(["POST"])
def clear_database(request):
    """Clear the database with safety confirmations."""
    try:
        from django.core.management import call_command
        from io import StringIO
        import json
        
        # Get parameters from request
        keep_users = request.POST.get('keep_users', 'false').lower() == 'true'
        keep_admin = request.POST.get('keep_admin', 'false').lower() == 'true'
        dry_run = request.POST.get('dry_run', 'false').lower() == 'true'
        
        # Capture command output
        output = StringIO()
        
        # Build command arguments
        args = ['clear_database', '--force']  # Skip confirmation prompts
        
        if keep_users:
            args.append('--keep-users')
        if keep_admin:
            args.append('--keep-admin')
        if dry_run:
            args.append('--dry-run')
        
        # Call the management command
        call_command(*args, stdout=output, verbosity=2)
        
        # Get the output
        command_output = output.getvalue()
        output.close()
        
        return JsonResponse({
            'success': True,
            'message': 'Database clear operation completed',
            'output': command_output,
            'dry_run': dry_run
        })
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return JsonResponse({
            'success': False,
            'error': f'Error clearing database: {str(e)}',
            'details': error_details
        }, status=500)


__all__ = ["clear_maintenance_data", "generate_pods", "generate_mdcs", "generate_pdus", "populate_demo_data", "clear_maintenance_activities", "clear_database"]
