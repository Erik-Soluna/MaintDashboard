"""activities views (split from the original monolithic views.py)."""
import logging
import csv
import io
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg
from django.utils import timezone
from datetime import timedelta, datetime
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import render_to_string
import json
from django.db.models.signals import post_save
from django.dispatch import receiver
from ..models import (
    MaintenanceActivity, MaintenanceActivityType, 
    MaintenanceSchedule, MaintenanceChecklist,
    ActivityTypeCategory, ActivityTypeTemplate, MaintenanceReport,
    MaintenanceTimelineEntry
)
from equipment.models import Equipment
from core.models import EquipmentCategory, UserProfile
from equipment.models import Equipment, EquipmentDocument
from ..forms import (
    MaintenanceActivityForm, MaintenanceScheduleForm, 
    MaintenanceActivityTypeForm, EnhancedMaintenanceActivityTypeForm,
    ActivityTypeCategoryForm, ActivityTypeTemplateForm
)
from events.models import CalendarEvent
from ..models import (
    EquipmentCategorySchedule, GlobalSchedule, ScheduleOverride
)
from ..forms import (
    EquipmentCategoryScheduleForm, GlobalScheduleForm, ScheduleOverrideForm
)
from django.contrib.auth.models import User
from core.models import Location
from core.utils import get_all_descendant_location_ids  # noqa: F401
from .helpers import *  # noqa: F401,F403 (shared helpers + globals)


@login_required
def maintenance_list(request):
    """Main maintenance dashboard."""
    try:
        # Get selected site from request, session, or user default
        from core.models import Location, UserProfile
        selected_site_id = request.GET.get('site_id')
        if selected_site_id is None:
            selected_site_id = request.session.get('selected_site_id')
        
        selected_site = None
        is_all_sites = False
        
        if selected_site_id:
            if selected_site_id == 'all':
                # Clear site selection (All Sites)
                request.session['selected_site_id'] = 'all'
                is_all_sites = True
            else:
                try:
                    selected_site = Location.objects.get(id=selected_site_id, is_site=True)
                    request.session['selected_site_id'] = selected_site_id
                    is_all_sites = False
                except (Location.DoesNotExist, ValueError):
                    pass
        else:
            # Check user default site
            try:
                user_profile = UserProfile.objects.get(user=request.user)
                if user_profile.default_site:
                    selected_site = user_profile.default_site
                    selected_site_id = str(selected_site.id)
                    request.session['selected_site_id'] = selected_site_id
                    is_all_sites = False
                else:
                    is_all_sites = True
            except UserProfile.DoesNotExist:
                is_all_sites = True
        
        # Build base queryset
        base_queryset = MaintenanceActivity.objects.select_related('equipment', 'equipment__location', 'activity_type')
        
        # Apply site filtering if a site is selected
        if selected_site and not is_all_sites:
            # Use recursive location filtering to get all descendant locations
            location_ids = get_all_descendant_location_ids(selected_site, include_inactive=True)
            base_queryset = base_queryset.filter(equipment__location_id__in=location_ids)
        
        # Get upcoming maintenance
        upcoming_activities = base_queryset.filter(
            scheduled_start__gte=timezone.now(),
            status__in=['scheduled', 'pending']
        ).order_by('scheduled_start')[:10]
        
        # Get overdue maintenance
        overdue_activities = base_queryset.filter(
            scheduled_end__lt=timezone.now(),
            status__in=['scheduled', 'pending']
        ).order_by('scheduled_start')[:10]
        
        # Get in progress
        in_progress = base_queryset.filter(
            status='in_progress'
        )
        
        # Statistics - apply site filter if needed
        stats_queryset = MaintenanceActivity.objects.all()
        if selected_site and not is_all_sites:
            location_ids = get_all_descendant_location_ids(selected_site, include_inactive=True)
            stats_queryset = stats_queryset.filter(equipment__location_id__in=location_ids)
        
        stats = {
            'total_activities': stats_queryset.count(),
            'pending_count': stats_queryset.filter(status='pending').count(),
            'overdue_count': overdue_activities.count(),
            'completed_this_month': stats_queryset.filter(
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
        
    except Exception as e:
        logger.error(f"Database error in maintenance_list: {str(e)}")
        
        # Try alternative query without select_related
        try:
            # Get selected site from request, session, or user default
            from core.models import Location, UserProfile
            selected_site_id = request.GET.get('site_id')
            if selected_site_id is None:
                selected_site_id = request.session.get('selected_site_id')
            
            selected_site = None
            is_all_sites = False
            
            if selected_site_id:
                if selected_site_id == 'all':
                    is_all_sites = True
                else:
                    try:
                        selected_site = Location.objects.get(id=selected_site_id, is_site=True)
                        is_all_sites = False
                    except (Location.DoesNotExist, ValueError):
                        pass
            else:
                try:
                    user_profile = UserProfile.objects.get(user=request.user)
                    if user_profile.default_site:
                        selected_site = user_profile.default_site
                        is_all_sites = False
                    else:
                        is_all_sites = True
                except UserProfile.DoesNotExist:
                    is_all_sites = True
            
            # Build base queryset
            base_queryset = MaintenanceActivity.objects.all()
            
            # Apply site filtering if a site is selected
            if selected_site and not is_all_sites:
                location_ids = get_all_descendant_location_ids(selected_site, include_inactive=True)
                base_queryset = base_queryset.filter(equipment__location_id__in=location_ids)
            
            upcoming_activities = base_queryset.filter(
                scheduled_start__gte=timezone.now(),
                status__in=['scheduled', 'pending']
            ).order_by('scheduled_start')[:10]
            
            overdue_activities = base_queryset.filter(
                scheduled_end__lt=timezone.now(),
                status__in=['scheduled', 'pending']
            ).order_by('scheduled_start')[:10]
            
            in_progress = base_queryset.filter(
                status='in_progress'
            )
            
            # Statistics - apply site filter if needed
            stats_queryset = MaintenanceActivity.objects.all()
            if selected_site and not is_all_sites:
                location_ids = get_all_descendant_location_ids(selected_site, include_inactive=True)
                stats_queryset = stats_queryset.filter(equipment__location_id__in=location_ids)
            
            stats = {
                'total_activities': stats_queryset.count(),
                'pending_count': stats_queryset.filter(status='pending').count(),
                'overdue_count': overdue_activities.count(),
                'completed_this_month': stats_queryset.filter(
                    status='completed',
                    actual_end__gte=timezone.now().replace(day=1)
                ).count(),
            }
            
            context = {
                'upcoming_activities': upcoming_activities,
                'overdue_activities': overdue_activities,
                'in_progress': in_progress,
                'stats': stats,
                'database_error': True,
                'error_message': 'Database schema issue detected. Some functionality may be limited.'
            }
            
            return render(request, 'maintenance/maintenance_list.html', context)
            
        except Exception as fallback_error:
            logger.error(f"Fallback query also failed: {str(fallback_error)}")
            messages.error(request, 'Database connection issue. Please contact support.')
            return redirect('/')


@login_required
def activity_list(request):
    """List all maintenance activities with filtering."""
    try:
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
        
    except Exception as e:
        logger.error(f"Database error in activity_list: {str(e)}")
        
        # Try alternative query without select_related
        try:
            queryset = MaintenanceActivity.objects.all()
            
            # Apply basic filtering
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
                    Q(title__icontains=search_term)
                )
            
            # Pagination
            paginator = Paginator(queryset, 25)
            page_number = request.GET.get('page')
            page_obj = paginator.get_page(page_number)
            
            context = {
                'page_obj': page_obj,
                'search_term': search_term,
                'statuses': MaintenanceActivity.STATUS_CHOICES,
                'equipment_list': [],
                'activity_types': [],
                'selected_status': status,
                'selected_equipment': equipment_id,
                'selected_activity_type': activity_type_id,
                'database_error': True,
                'error_message': 'Database schema issue detected. Some functionality may be limited.'
            }
            
            return render(request, 'maintenance/activity_list.html', context)
            
        except Exception as fallback_error:
            logger.error(f"Fallback query also failed: {str(fallback_error)}")
            messages.error(request, 'Database connection issue. Please contact support.')
            return redirect('maintenance:maintenance_list')


@login_required
def bulk_add_activity(request):
    """Bulk create maintenance activities for multiple equipment items."""
    from django.db import connection, transaction
    from django.utils import timezone
    from equipment.models import Equipment
    from core.models import Location
    from datetime import datetime
    import pytz
    
    try:
        connection.ensure_connection()
        
        # Get user's timezone from profile (defaults to Central)
        user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
        user_timezone_str = user_profile.get_user_timezone()  # Returns 'America/Chicago' by default
        user_tz = pytz.timezone(user_timezone_str)
        
        # Get site filtering
        selected_site_id = request.GET.get('site_id')
        if selected_site_id is None:
            selected_site_id = request.session.get('selected_site_id')
        
        selected_site = None
        is_all_sites = False
        
        # Build equipment queryset with site filtering
        # IMPORTANT: Don't filter by location here - we'll handle that separately
        # to ensure we catch equipment with NULL locations or inactive location hierarchies
        equipment_query = Equipment.objects.filter(is_active=True).select_related('location', 'location__parent_location', 'category')
        
        if selected_site_id and selected_site_id != 'all':
            try:
                selected_site = Location.objects.get(id=selected_site_id, is_site=True)
                # Get all descendant location IDs (handles nested locations at any depth)
                # Include inactive locations to catch equipment that might be in inactive location hierarchies
                location_ids = get_all_descendant_location_ids(selected_site, include_inactive=True)
                
                # Log for debugging
                logger.info(f"Bulk add activity - Site: {selected_site.name} (ID: {selected_site_id}), Found {len(location_ids)} location IDs")
                
                # Filter equipment by location IDs (includes all nested locations)
                equipment_query = equipment_query.filter(location_id__in=location_ids)
                
                # Log equipment count for debugging
                equipment_count = equipment_query.count()
                total_equipment_count = Equipment.objects.filter(is_active=True).count()
                logger.info(f"Bulk add activity - Filtered equipment count: {equipment_count} out of {total_equipment_count} total active equipment")
            except Location.DoesNotExist:
                logger.warning(f"Bulk add activity - Site ID {selected_site_id} not found")
                pass
        else:
            is_all_sites = True
        
        if request.method == 'POST':
            # Get form data
            equipment_ids = request.POST.getlist('equipment_ids')
            activity_type_id = request.POST.get('activity_type')
            title_template = request.POST.get('title')
            description = request.POST.get('description', '')
            priority = request.POST.get('priority', 'medium')
            status = request.POST.get('status', 'scheduled')
            scheduled_start = request.POST.get('scheduled_start')
            scheduled_end = request.POST.get('scheduled_end')
            assigned_to_id = request.POST.get('assigned_to')
            
            # Recurring fields
            make_recurring = request.POST.get('make_recurring') == 'on'
            recurrence_frequency = request.POST.get('recurrence_frequency', '')
            recurrence_frequency_days = request.POST.get('recurrence_frequency_days')
            recurrence_end_date = request.POST.get('recurrence_end_date')
            recurrence_advance_notice_days = request.POST.get('recurrence_advance_notice_days', 7)
            
            # Validation
            if not equipment_ids:
                messages.error(request, 'Please select at least one equipment item.')
            elif not activity_type_id:
                messages.error(request, 'Please select an activity type.')
            elif not title_template:
                messages.error(request, 'Please provide a title.')
            else:
                try:
                    activity_type = MaintenanceActivityType.objects.get(id=activity_type_id)
                    assigned_to = User.objects.get(id=assigned_to_id) if assigned_to_id else None
                    
                    # Convert date strings to timezone-aware datetime objects in user's timezone
                    scheduled_start_dt = None
                    scheduled_end_dt = None
                    if scheduled_start:
                        # Parse as naive datetime, then localize to user's timezone
                        naive_dt = datetime.strptime(scheduled_start, '%Y-%m-%dT%H:%M')
                        scheduled_start_dt = user_tz.localize(naive_dt)
                    if scheduled_end:
                        # Parse as naive datetime, then localize to user's timezone
                        naive_dt = datetime.strptime(scheduled_end, '%Y-%m-%dT%H:%M')
                        scheduled_end_dt = user_tz.localize(naive_dt)
                    
                    created_activities = []
                    created_schedules = []
                    
                    # Create activities in a transaction
                    with transaction.atomic():
                        for equipment_id in equipment_ids:
                            equipment = Equipment.objects.get(id=equipment_id, is_active=True)
                            
                            # Replace {equipment} placeholder in title
                            # Use the proper title generation function that supports all variables
                            from maintenance.utils import generate_activity_title
                            activity_title = generate_activity_title(
                                template=title_template,
                                activity_type=activity_type,
                                equipment=equipment,
                                scheduled_start=scheduled_start_dt,
                                priority=priority,
                                status=status
                            )
                            
                            activity = MaintenanceActivity.objects.create(
                                equipment=equipment,
                                activity_type=activity_type,
                                title=activity_title,
                                description=description,
                                priority=priority,
                                status=status,
                                scheduled_start=scheduled_start_dt,
                                scheduled_end=scheduled_end_dt,
                                assigned_to=assigned_to,
                                tools_required=activity_type.tools_required,
                                parts_required=activity_type.parts_required,
                                safety_notes=activity_type.safety_notes,
                                created_by=request.user,
                                updated_by=request.user,
                            )
                            created_activities.append(activity)
                            
                            # Handle recurring schedule creation
                            if make_recurring and recurrence_frequency:
                                from maintenance.models import MaintenanceSchedule
                                
                                # Calculate frequency_days for the stored schedule field
                                from maintenance.scheduling import frequency_to_days
                                _custom_days = int(recurrence_frequency_days) if recurrence_frequency_days else None
                                frequency_days = frequency_to_days(recurrence_frequency, _custom_days)
                                
                                # Parse end date if provided
                                recurrence_end_date_obj = None
                                if recurrence_end_date:
                                    from datetime import datetime
                                    recurrence_end_date_obj = datetime.strptime(recurrence_end_date, '%Y-%m-%d').date()
                                
                                # Create the maintenance schedule
                                schedule = MaintenanceSchedule.objects.create(
                                    equipment=equipment,
                                    activity_type=activity_type,
                                    frequency=recurrence_frequency,
                                    frequency_days=frequency_days,
                                    start_date=scheduled_start_dt.date() if scheduled_start_dt else timezone.now().date(),
                                    end_date=recurrence_end_date_obj,
                                    advance_notice_days=int(recurrence_advance_notice_days),
                                    auto_generate=True,
                                    is_active=True,
                                )
                                created_schedules.append(schedule)
                    
                    # Success message
                    if created_schedules:
                        messages.success(request, f'Successfully created {len(created_activities)} maintenance activities and {len(created_schedules)} recurring schedules!')
                    else:
                        messages.success(request, f'Successfully created {len(created_activities)} maintenance activities!')
                    return redirect('maintenance:maintenance_list')
                    
                except Exception as e:
                    logger.error(f"Error creating bulk activities: {str(e)}")
                    messages.error(request, f'Error creating activities: {str(e)}')
        
        # GET request - show form
        equipment_list = equipment_query.order_by('name')
        activity_types = MaintenanceActivityType.objects.filter(is_active=True).select_related('category').order_by('category__sort_order', 'name')
        users = User.objects.filter(is_active=True).order_by('username')
        
        # Group equipment by category for easier selection
        from collections import defaultdict
        equipment_by_category = defaultdict(list)
        for equipment in equipment_list:
            category_name = equipment.category.name if equipment.category else 'Uncategorized'
            equipment_by_category[category_name].append(equipment)
        
        context = {
            'equipment_list': equipment_list,
            'equipment_by_category': dict(equipment_by_category),
            'activity_types': activity_types,
            'users': users,
            'selected_site': selected_site,
            'selected_site_id': selected_site_id,
            'is_all_sites': is_all_sites,
        }
        return render(request, 'maintenance/bulk_add_activity.html', context)
        
    except Exception as e:
        logger.error(f"Error in bulk_add_activity: {str(e)}")
        messages.error(request, f'Error loading bulk creation form: {str(e)}')
        return redirect('maintenance:maintenance_list')


@login_required
def activity_detail(request, activity_id):
    """Display detailed maintenance activity information with comprehensive timeline."""
    activity = get_object_or_404(
        MaintenanceActivity.objects.select_related(
            'equipment', 'equipment__category', 'equipment__location',
            'activity_type', 'activity_type__category', 'assigned_to'
        ),
        id=activity_id
    )
    
    # Get timeline entries and create a comprehensive chronological timeline
    timeline_entries = activity.timeline_entries.all().order_by('-created_at')
    
    # Create a comprehensive timeline with all events
    timeline_events = []
    
    # Add activity creation event
    timeline_events.append({
        'type': 'activity_created',
        'title': 'Activity Created',
        'description': f'Created by {activity.created_by.get_full_name() or activity.created_by.username}',
        'timestamp': activity.created_at,
        'created_by': activity.created_by,
        'icon': 'fa-plus',
        'color': 'primary'
    })
    
    # Add timeline entries
    for entry in timeline_entries:
        timeline_events.append({
            'type': 'timeline_entry',
            'entry_id': entry.id,  # Include ID for edit/delete
            'entry_type': entry.entry_type,
            'title': entry.title,
            'description': entry.description,
            'timestamp': entry.created_at,
            'created_by': entry.created_by,
            'icon': entry.entry_type,
            'color': entry.entry_type
        })
    
    # Add status change events if they exist
    if activity.actual_start:
        timeline_events.append({
            'type': 'status_change',
            'title': 'Activity Started',
            'description': f'Maintenance activity started at {activity.actual_start.strftime("%Y-%m-%d %H:%M")}',
            'timestamp': activity.actual_start,
            'created_by': None,
            'icon': 'fa-play',
            'color': 'warning'
        })
    
    if activity.actual_end:
        timeline_events.append({
            'type': 'status_change',
            'title': 'Activity Completed',
            'description': f'Maintenance activity completed at {activity.actual_end.strftime("%Y-%m-%d %H:%M")}',
            'timestamp': activity.actual_end,
            'created_by': None,
            'icon': 'fa-check',
            'color': 'success'
        })
    
    # Sort all timeline events by timestamp (newest first)
    timeline_events.sort(key=lambda x: x['timestamp'], reverse=True)
    
    # Get all related documents
    all_documents = activity.get_all_documents()
    
    # Get maintenance reports for this activity
    maintenance_reports = activity.reports.all().order_by('-created_at')
    
    # Get equipment documents that might be relevant
    equipment_documents = activity.equipment.documents.all().order_by('-created_at')[:10]
    
    # Get related maintenance activities for this equipment
    related_activities = MaintenanceActivity.objects.filter(
        equipment=activity.equipment
    ).exclude(id=activity.id).order_by('-scheduled_start')[:5]
    
    # Get equipment maintenance history
    equipment_history = MaintenanceActivity.objects.filter(
        equipment=activity.equipment,
        status='completed'
    ).order_by('-actual_end')[:10]
    
    # Calculate maintenance statistics
    total_maintenance_time = 0
    completed_activities = MaintenanceActivity.objects.filter(
        equipment=activity.equipment,
        status='completed',
        actual_start__isnull=False,
        actual_end__isnull=False
    )
    
    for completed_activity in completed_activities:
        if completed_activity.actual_start and completed_activity.actual_end:
            duration = completed_activity.actual_end - completed_activity.actual_start
            total_maintenance_time += duration.total_seconds() / 3600  # Convert to hours
    
    # Get next scheduled maintenance
    next_maintenance = MaintenanceActivity.objects.filter(
        equipment=activity.equipment,
        status='scheduled',
        scheduled_start__gt=activity.scheduled_start
    ).order_by('scheduled_start').first()
    
    # Get maintenance schedule for this activity type
    maintenance_schedule = MaintenanceSchedule.objects.filter(
        equipment=activity.equipment,
        activity_type=activity.activity_type,
        is_active=True
    ).first()
    
    context = {
        'activity': activity,
        'timeline_entries': timeline_entries,
        'timeline_events': timeline_events,
        'all_documents': all_documents,
        'maintenance_reports': maintenance_reports,
        'equipment_documents': equipment_documents,
        'related_activities': related_activities,
        'equipment_history': equipment_history,
        'total_maintenance_time': round(total_maintenance_time, 2),
        'next_maintenance': next_maintenance,
        'maintenance_schedule': maintenance_schedule,
        'page_title': f'Maintenance Activity: {activity.title}',
    }
    
    return render(request, 'maintenance/activity_detail.html', context)


@login_required
def add_activity(request):
    """Add new maintenance activity with improved database connection handling."""
    from django.db import connection
    from equipment.models import Equipment
    from core.models import Location
    
    try:
        # Ensure database connection is healthy
        connection.ensure_connection()
        
        # Debug: Check if there are any equipment records
        total_equipment_count = Equipment.objects.filter(is_active=True).count()
        logger.info(f"Total active equipment count: {total_equipment_count}")
        
        # Check site filtering
        selected_site_id = request.GET.get('site_id')
        if selected_site_id is None:
            selected_site_id = request.session.get('selected_site_id')
        
        selected_site = None
        is_all_sites = False
        
        if selected_site_id:
            if selected_site_id == 'all':
                # Handle "All Sites" selection
                is_all_sites = True
                logger.info("Selected site: All Sites")
            else:
                try:
                    selected_site = Location.objects.get(id=selected_site_id, is_site=True)
                    logger.info(f"Selected site: {selected_site.name}")
                except (Location.DoesNotExist, ValueError):
                    logger.warning(f"Invalid site ID: {selected_site_id}")
        else:
            # No site selected, treat as "All Sites"
            is_all_sites = True
            logger.info("Selected site: All Sites (default)")
        
        if request.method == 'POST':
            form = MaintenanceActivityForm(request.POST, request=request)
            if form.is_valid():
                activity = form.save(commit=False)
                activity.created_by = request.user
                activity.save()
                
                messages.success(request, f'Maintenance activity "{activity.title}" created successfully!')
                
                return redirect('maintenance:activity_detail', activity_id=activity.id)
        else:
            # Get initial data from GET parameters
            initial_data = {}
            equipment_id = request.GET.get('equipment')
            if equipment_id:
                try:
                    equipment = Equipment.objects.get(id=equipment_id, is_active=True)
                    # Use equipment.id instead of equipment object for ModelChoiceField
                    initial_data['equipment'] = equipment.id
                    logger.info(f"Pre-populating equipment: {equipment.name} (ID: {equipment.id})")
                except (Equipment.DoesNotExist, ValueError):
                    logger.warning(f"Invalid equipment ID in GET parameter: {equipment_id}")
            
            form = MaintenanceActivityForm(initial=initial_data, request=request, equipment_id=equipment_id)
        
        # Debug: Check equipment queryset in form with better error handling
        try:
            equipment_queryset = form.fields['equipment'].queryset
            filtered_equipment_count = equipment_queryset.count()
            logger.info(f"Filtered equipment queryset count: {filtered_equipment_count}")
            
            # Get first 10 equipment safely
            equipment_list = list(equipment_queryset[:10])
        except Exception as e:
            logger.error(f"Error getting equipment queryset: {str(e)}")
            filtered_equipment_count = 0
            equipment_list = []
        
        context = {
            'form': form,
            'equipment_count': filtered_equipment_count,
            'total_equipment_count': total_equipment_count,
            'selected_site': selected_site,
            'selected_site_id': selected_site_id,
            'is_all_sites': is_all_sites,
            'equipment_list': equipment_list,
        }
        return render(request, 'maintenance/add_activity.html', context)
        
    except Exception as e:
        logger.error(f"Database connection error in add_activity: {str(e)}")
        
        # Try to reconnect
        try:
            connection.close()
            connection.connect()
            logger.info("Database reconnected successfully")
            
            # Retry with simple form
            if request.method == 'POST':
                messages.error(request, 'Database connection issue. Please try again.')
                return redirect('maintenance:add_activity')
            else:
                form = MaintenanceActivityForm(request=request)
                context = {
                    'form': form,
                    'equipment_count': 0,
                    'total_equipment_count': 0,
                    'selected_site': None,
                    'equipment_list': [],
                    'connection_error': True,
                }
                return render(request, 'maintenance/add_activity.html', context)
                
        except Exception as reconnect_error:
            logger.error(f"Failed to reconnect to database: {str(reconnect_error)}")
            messages.error(request, 'Database connection issue. Please contact support.')
            return redirect('maintenance:maintenance_list')


@login_required
def edit_activity(request, activity_id):
    """Edit maintenance activity."""
    activity = get_object_or_404(MaintenanceActivity, id=activity_id)
    
    if request.method == 'POST':
        form = MaintenanceActivityForm(request.POST, instance=activity, request=request)
        if form.is_valid():
            activity = form.save(commit=False)
            activity.updated_by = request.user
            activity.save()
            
            messages.success(request, f'Maintenance activity "{activity.title}" updated successfully!')
            
            return redirect('maintenance:activity_detail', activity_id=activity.id)
    else:
        form = MaintenanceActivityForm(instance=activity, request=request)
    
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
def overdue_maintenance(request):
    """List overdue maintenance activities."""
    overdue_activities = MaintenanceActivity.objects.filter(
        scheduled_end__lt=timezone.now(),
        status__in=['scheduled', 'pending', 'in_progress']
    ).select_related('equipment', 'activity_type', 'assigned_to').order_by('scheduled_end')
    
    context = {'overdue_activities': overdue_activities}
    return render(request, 'maintenance/overdue_maintenance.html', context)


@login_required
def delete_activity(request, activity_id):
    """Delete maintenance activity and associated calendar events."""
    activity = get_object_or_404(MaintenanceActivity, id=activity_id)
    
    if request.method == 'POST':
        activity_title = activity.title
        
        # Count associated calendar events before deletion (signal will handle deletion)
        from events.models import CalendarEvent
        events_deleted = CalendarEvent.objects.filter(maintenance_activity=activity).count()
        
        # Delete the maintenance activity (signal will handle calendar event deletion and cache invalidation)
        activity.delete()
        
        # Invalidate dashboard cache for current user only (signal invalidates all, but this is more targeted)
        try:
            from core.views import invalidate_dashboard_cache
            invalidate_dashboard_cache(user_id=request.user.id)
        except Exception as cache_error:
            logger.warning(f"Could not invalidate dashboard cache: {cache_error}")
        
        # Check if this is an AJAX request
        if request.headers.get('Content-Type') == 'application/json' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Return JSON response for AJAX requests
            return JsonResponse({
                'success': True,
                'message': f'Maintenance activity "{activity_title}" deleted successfully!',
                'events_deleted': events_deleted
            })
        else:
            # Return redirect for regular form submissions
            if events_deleted > 0:
                messages.success(request, f'Maintenance activity "{activity_title}" and {events_deleted} associated calendar event(s) deleted successfully!')
            else:
                messages.success(request, f'Maintenance activity "{activity_title}" deleted successfully!')
            return redirect('maintenance:maintenance_list')
    
    context = {'activity': activity}
    return render(request, 'maintenance/delete_activity.html', context)


@login_required
def get_activities_data(request):
    """AJAX endpoint to get maintenance activities data."""
    activities = MaintenanceActivity.objects.select_related(
        'equipment', 'activity_type', 'assigned_to'
    ).all()
    
    # Apply filters
    status = request.GET.get('status')
    if status:
        activities = activities.filter(status=status)
        
    equipment_id = request.GET.get('equipment_id')
    if equipment_id:
        activities = activities.filter(equipment_id=equipment_id)
    
    # Convert to list of dictionaries
    data = []
    for activity in activities:
        data.append({
            'id': activity.id,
            'title': activity.title,
            'equipment': activity.equipment.name,
            'activity_type': activity.activity_type.name,
            'status': activity.status,
            'priority': activity.priority,
            'scheduled_start': activity.scheduled_start.isoformat() if activity.scheduled_start else None,
            'scheduled_end': activity.scheduled_end.isoformat() if activity.scheduled_end else None,
            'assigned_to': activity.assigned_to.get_full_name() if activity.assigned_to else None,
        })
    
    return JsonResponse({'activities': data})


@login_required
@require_http_methods(["GET"])
def fetch_activities(request):
    """API endpoint: Return maintenance activities in FullCalendar JSON format (optimized for large datasets)."""
    try:
        from datetime import datetime, timedelta
        
        # Filters
        equipment_id = request.GET.get('equipment')
        status = request.GET.get('status')
        site_id = request.GET.get('site_id')
        start = request.GET.get('start')  # ISO date string
        end = request.GET.get('end')      # ISO date string

        # Start with optimized query using only() to fetch only needed fields
        queryset = MaintenanceActivity.objects.select_related('equipment', 'equipment__location', 'activity_type', 'assigned_to').only(
            'id', 'title', 'status', 'priority', 'scheduled_start', 'scheduled_end',
            'equipment__name', 'equipment__location__name', 
            'activity_type__name', 'assigned_to__first_name', 'assigned_to__last_name'
        )
        
        if equipment_id:
            queryset = queryset.filter(equipment_id=equipment_id)
        if status:
            queryset = queryset.filter(status=status)
        if site_id and site_id != 'all':
            # Filter by equipment's site or parent location
            queryset = queryset.filter(
                Q(equipment__location__parent_location_id=site_id) |
                Q(equipment__location_id=site_id)
            )
        
        # PERFORMANCE FIX: Apply date filtering to catch overlapping events
        if start and end:
            # Parse dates
            try:
                start_date = datetime.fromisoformat(start.replace('Z', '+00:00'))
                end_date = datetime.fromisoformat(end.replace('Z', '+00:00'))
                
                # Filter for activities that overlap with the calendar view range
                # Include activities that:
                # 1. Start within the range, OR
                # 2. End within the range, OR  
                # 3. Start before and end after the range (spanning the entire period)
                queryset = queryset.filter(
                    Q(scheduled_start__gte=start_date, scheduled_start__lte=end_date) |
                    Q(scheduled_end__gte=start_date, scheduled_end__lte=end_date) |
                    Q(scheduled_start__lte=start_date, scheduled_end__gte=end_date)
                )
            except (ValueError, AttributeError) as date_error:
                logger.warning(f"Date parsing error in fetch_activities: {date_error}")
                # If date parsing fails, add a reasonable fallback filter
                # Show activities within ±3 months of today
                from django.utils import timezone as tz
                fallback_start = tz.now() - timedelta(days=90)
                fallback_end = tz.now() + timedelta(days=90)
                queryset = queryset.filter(
                    scheduled_start__gte=fallback_start,
                    scheduled_start__lte=fallback_end
                )
        else:
            # No date range specified - use a reasonable default to avoid loading everything
            # Show activities within ±2 months of today
            from django.utils import timezone as tz
            default_start = tz.now() - timedelta(days=60)
            default_end = tz.now() + timedelta(days=60)
            queryset = queryset.filter(
                scheduled_start__gte=default_start,
                scheduled_start__lte=default_end
            )

        # PERFORMANCE FIX: Add a hard limit as a safety net (max 500 activities)
        # Order by scheduled_start to show most relevant activities first
        activities = queryset.order_by('scheduled_start')[:500]
        
        # Build results using list comprehension for speed
        results = [
            {
                'id': activity.id,
                'title': activity.title,
                'start': activity.scheduled_start.isoformat(),
                'end': activity.scheduled_end.isoformat() if activity.scheduled_end else None,
                'allDay': False,
                'status': activity.status,
                'priority': activity.priority,
                'equipment': activity.equipment.name if activity.equipment else None,
                'location': activity.equipment.location.name if activity.equipment and activity.equipment.location else None,
                'activity_type': activity.activity_type.name if activity.activity_type else None,
                'assigned_to': activity.assigned_to.get_full_name() if activity.assigned_to else None,
                'is_completed': activity.status == 'completed',
                'backgroundColor': '#4299e1' if activity.status == 'scheduled' else '#dc3545' if activity.status == 'overdue' else '#28a745' if activity.status == 'completed' else '#ffc107',
                'borderColor': '#2d3748',
                'textColor': '#fff',
            }
            for activity in activities
        ]
        
        logger.info(f"fetch_activities returned {len(results)} activities (date range: {start} to {end})")
        return JsonResponse(results, safe=False)
    except Exception as e:
        logger.error(f"Error in fetch_activities: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def get_activity_details(request, activity_id):
    """Get detailed information about a maintenance activity for AJAX requests."""
    try:
        from core.models import UserProfile
        import pytz
        
        # Get user's timezone from profile (defaults to Central)
        user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
        user_timezone_str = user_profile.get_user_timezone()  # Returns 'America/Chicago' by default
        user_tz = pytz.timezone(user_timezone_str)
        
        activity = get_object_or_404(MaintenanceActivity, id=activity_id)
        
        # Get related data
        checklist_items = activity.checklist_items.all().order_by('order')
        timeline_entries = activity.timeline_entries.all().order_by('-created_at')[:10]
        reports = activity.reports.all().order_by('-created_at')
        
        # Get activity's timezone (or fallback to user's timezone)
        activity_timezone_str = activity.timezone or user_timezone_str
        activity_tz = pytz.timezone(activity_timezone_str)
        
        # Convert datetimes to the activity's timezone for display
        # This ensures the time shown matches what was entered and is consistent with the calendar view
        def convert_to_activity_tz(dt):
            if not dt:
                return None
            # If already timezone-aware, convert to activity's timezone
            if timezone.is_aware(dt):
                return dt.astimezone(activity_tz)
            # If naive, assume UTC and convert to activity's timezone
            return timezone.make_aware(dt, pytz.UTC).astimezone(activity_tz)
        
        # Send times in the activity's timezone for consistent display
        # This matches the calendar API which also sends times in the activity's timezone
        scheduled_start_local = convert_to_activity_tz(activity.scheduled_start)
        scheduled_end_local = convert_to_activity_tz(activity.scheduled_end)
        actual_start_local = convert_to_activity_tz(activity.actual_start)
        actual_end_local = convert_to_activity_tz(activity.actual_end)
        
        data = {
            'id': activity.id,
            'title': activity.title,
            'description': activity.description,
            'status': activity.get_status_display(),
            'priority': activity.get_priority_display(),
            'equipment': {
                'id': activity.equipment.id,
                'name': activity.equipment.name,
                'category': activity.equipment.category.name if activity.equipment.category else None,
            },
            'activity_type': {
                'id': activity.activity_type.id,
                'name': activity.activity_type.name,
                'category': activity.activity_type.category.name,
            },
            'scheduled_start': scheduled_start_local.isoformat() if scheduled_start_local else None,
            'scheduled_end': scheduled_end_local.isoformat() if scheduled_end_local else None,
            'actual_start': actual_start_local.isoformat() if actual_start_local else None,
            'actual_end': actual_end_local.isoformat() if actual_end_local else None,
            'timezone': activity.timezone or user_timezone_str,  # Use activity's timezone, fallback to user's timezone
            'timezone_display_name': activity.get_timezone_display_name(),  # Human-readable timezone name from DB
            'assigned_to': activity.assigned_to.username if activity.assigned_to else None,
            'completion_notes': activity.completion_notes,
            'checklist_items': [
                {
                    'id': item.id,
                    'text': item.item_text,
                    'is_completed': item.is_completed,
                    'completed_by': item.completed_by.username if item.completed_by else None,
                    'completed_at': item.completed_at.isoformat() if item.completed_at else None,
                    'notes': item.notes,
                }
                for item in checklist_items
            ],
            'timeline_entries': [
                {
                    'id': entry.id,
                    'entry_type': entry.get_entry_type_display(),
                    'title': entry.title,
                    'description': entry.description,
                    'created_at': entry.created_at.isoformat(),
                    'created_by': entry.created_by.username if entry.created_by else None,
                }
                for entry in timeline_entries
            ],
            'reports': [
                {
                    'id': report.id,
                    'title': report.title,
                    'report_type': report.get_report_type_display(),
                    'created_at': report.created_at.isoformat(),
                    'is_processed': report.is_processed,
                    'has_critical_issues': report.has_critical_issues(),
                }
                for report in reports
            ],
        }
        
        return JsonResponse(data)
        
    except Exception as e:
        logger.error(f"Error getting activity details: {str(e)}")
        return JsonResponse({'error': 'Failed to get activity details'}, status=500)


@login_required
@require_http_methods(["POST"])
def create_activity_api(request):
    """API endpoint for creating maintenance activities via AJAX."""
    try:
        # Parse JSON data from request
        data = json.loads(request.body)
        
        # Process the data to match form expectations
        processed_data = data.copy()
        
        # Handle activity_type - remove 'activity_' prefix if present
        if 'activity_type' in processed_data and processed_data['activity_type']:
            activity_type_value = processed_data['activity_type']
            if isinstance(activity_type_value, str) and activity_type_value.startswith('activity_'):
                processed_data['activity_type'] = activity_type_value.replace('activity_', '')
        
        # Handle assigned_to - if it's a string, try to find the user
        if 'assigned_to' in processed_data and processed_data['assigned_to']:
            assigned_to_value = processed_data['assigned_to']
            if isinstance(assigned_to_value, str) and assigned_to_value.strip():
                # Try to find user by username, first_name, or last_name
                try:
                    user = User.objects.filter(
                        Q(username__icontains=assigned_to_value) |
                        Q(first_name__icontains=assigned_to_value) |
                        Q(last_name__icontains=assigned_to_value)
                    ).first()
                    if user:
                        processed_data['assigned_to'] = user.id
                    else:
                        # If no user found, set to None
                        processed_data['assigned_to'] = None
                except Exception:
                    processed_data['assigned_to'] = None
            else:
                processed_data['assigned_to'] = None
        else:
            processed_data['assigned_to'] = None
        
        # Handle equipment - support both single equipment and multiple equipment_ids
        equipment_ids = processed_data.get('equipment_ids', [])
        single_equipment = processed_data.get('equipment')
        
        # If equipment_ids is provided, use it; otherwise fall back to single equipment
        if equipment_ids:
            if isinstance(equipment_ids, str):
                # Handle comma-separated string
                equipment_ids = [int(id.strip()) for id in equipment_ids.split(',') if id.strip()]
            elif not isinstance(equipment_ids, list):
                equipment_ids = [equipment_ids]
        elif single_equipment:
            # Single equipment ID
            equipment_ids = [single_equipment]
        else:
            # No equipment provided
            return JsonResponse({
                'success': False,
                'error': 'At least 1 equipment is required to create a Maintenance activity.'
            }, status=400)
        
        # Validate equipment IDs exist
        from equipment.models import Equipment
        valid_equipment = Equipment.objects.filter(id__in=equipment_ids, is_active=True)
        if valid_equipment.count() != len(equipment_ids):
            return JsonResponse({
                'success': False,
                'error': 'One or more equipment IDs are invalid or inactive.'
            }, status=400)
        
        # Handle deenergization_required field (per WORK-001)
        deenergization_required = processed_data.get('deenergization_required', False)
        if isinstance(deenergization_required, str):
            deenergization_required = deenergization_required.lower() in ('true', '1', 'yes')
        processed_data['deenergization_required'] = deenergization_required
        
        # Create one activity per equipment
        created_activities = []
        errors = []
        
        for equipment_id in equipment_ids:
            # Create a copy of processed_data for each equipment
            equipment_data = processed_data.copy()
            equipment_data['equipment'] = equipment_id
            equipment_data.pop('equipment_ids', None)  # Remove equipment_ids from form data
            
            # Create form with the processed data
            form = MaintenanceActivityForm(equipment_data, request=request)
            
            if form.is_valid():
                # Save the activity
                activity = form.save(commit=False)
                activity.created_by = request.user
                activity.save()
                created_activities.append({
                    'id': activity.id,
                    'title': activity.title,
                    'equipment': activity.equipment.name
                })
            else:
                errors.append({
                    'equipment_id': equipment_id,
                    'errors': form.errors
                })
        
        if created_activities:
            # Return success response
            message = f'Created {len(created_activities)} maintenance activity(ies) successfully!'
            if errors:
                message += f' {len(errors)} failed.'
            
            return JsonResponse({
                'success': True,
                'message': message,
                'activities': created_activities,
                'errors': errors if errors else None
            })
        else:
            # All failed
            logger.error(f"All activities failed to create: {errors}")
            return JsonResponse({
                'success': False,
                'error': 'Failed to create maintenance activities',
                'errors': errors
            }, status=400)
            
    except json.JSONDecodeError:
        logger.error("Invalid JSON data received")
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f"Error creating maintenance activity via API: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Server error: {str(e)}'
        }, status=500)


@login_required
def upload_activity_document(request, activity_id):
    """Upload a document to a maintenance activity."""
    activity = get_object_or_404(MaintenanceActivity, id=activity_id)
    
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        document_type = request.POST.get('document_type')
        file = request.FILES.get('file')
        
        if title and file and document_type:
            try:
                # Create the document
                document = EquipmentDocument.objects.create(
                    equipment=activity.equipment,
                    title=title,
                    description=description or '',
                    document_type=document_type,
                    file=file,
                    created_by=request.user
                )
                
                # Create timeline entry
                MaintenanceTimelineEntry.objects.create(
                    activity=activity,
                    entry_type='note',
                    title=f'Document Uploaded: {title}',
                    description=f'Document "{title}" was uploaded by {request.user.get_full_name() or request.user.username}',
                    created_by=request.user
                )
                
                messages.success(request, 'Document uploaded successfully!')
                return redirect('maintenance:activity_detail', activity_id=activity_id)
                
            except Exception as e:
                logger.error(f"Error uploading document: {str(e)}")
                messages.error(request, f'Error uploading document: {str(e)}')
        else:
            messages.error(request, 'Please fill in all required fields.')
    
    context = {
        'activity': activity,
        'document_types': EquipmentDocument.DOCUMENT_TYPE_CHOICES,
    }
    return render(request, 'maintenance/upload_document.html', context)


@login_required
def change_activity_status(request, activity_id):
    """Change activity status without editing the entire activity."""
    activity = get_object_or_404(MaintenanceActivity, id=activity_id)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        notes = request.POST.get('notes', '')
        
        if new_status and new_status in dict(MaintenanceActivity.STATUS_CHOICES):
            old_status = activity.status
            activity.status = new_status
            activity.updated_by = request.user
            
            # Handle start/end times based on status and user input
            actual_start_str = request.POST.get('actual_start', '').strip()
            actual_end_str = request.POST.get('actual_end', '').strip()
            
            # Wall-clock times entered by the user are in the activity's timezone;
            # interpret them there and store UTC (do NOT make_aware in the server
            # zone, which previously saved e.g. "2pm Central" as "2pm UTC").
            from maintenance.utils import parse_wallclock_to_utc

            if new_status == 'in_progress' or new_status == 'completed':
                # Use custom start time if provided, otherwise use current time or existing value
                if actual_start_str:
                    try:
                        activity.actual_start = parse_wallclock_to_utc(actual_start_str, activity.timezone)
                    except (ValueError, TypeError):
                        # If parsing fails, use current time
                        if not activity.actual_start:
                            activity.actual_start = timezone.now()
                elif not activity.actual_start:
                    activity.actual_start = timezone.now()

            if new_status == 'completed':
                # Use custom end time if provided, otherwise use current time or existing value
                if actual_end_str:
                    try:
                        activity.actual_end = parse_wallclock_to_utc(actual_end_str, activity.timezone)
                    except (ValueError, TypeError):
                        # If parsing fails, use current time
                        if not activity.actual_end:
                            activity.actual_end = timezone.now()
                elif not activity.actual_end:
                    activity.actual_end = timezone.now()
                
                # Ensure start time is set if completing
                if not activity.actual_start:
                    activity.actual_start = activity.scheduled_start
            
            activity.save()
            # Note: Timeline entry is automatically created by the signal in maintenance/signals.py
            # No need to manually create it here to avoid duplicates
            
            messages.success(request, f'Activity status changed to {activity.get_status_display()}')
            return redirect('maintenance:activity_detail', activity_id=activity_id)
        else:
            messages.error(request, 'Invalid status selected.')
    
    context = {
        'activity': activity,
        'status_choices': MaintenanceActivity.STATUS_CHOICES,
    }
    return render(request, 'maintenance/change_status.html', context)


@login_required
def attach_related_activity(request, activity_id):
    """Attach a related activity to the current activity."""
    activity = get_object_or_404(MaintenanceActivity, id=activity_id)
    
    if request.method == 'POST':
        related_activity_id = request.POST.get('related_activity_id')
        relationship_type = request.POST.get('relationship_type', 'related')
        
        if related_activity_id:
            try:
                related_activity = MaintenanceActivity.objects.get(id=related_activity_id)
                
                # Create a many-to-many relationship (you may need to add this field to your model)
                # For now, we'll create a timeline entry to document the relationship
                MaintenanceTimelineEntry.objects.create(
                    activity=activity,
                    entry_type='note',
                    title=f'Related Activity Attached: {related_activity.title}',
                    description=f'Activity "{related_activity.title}" was attached as a {relationship_type} activity by {request.user.get_full_name() or request.user.username}',
                    created_by=request.user
                )
                
                messages.success(request, 'Related activity attached successfully!')
                return redirect('maintenance:activity_detail', activity_id=activity_id)
                
            except MaintenanceActivity.DoesNotExist:
                messages.error(request, 'Related activity not found.')
            except Exception as e:
                logger.error(f"Error attaching related activity: {str(e)}")
                messages.error(request, f'Error attaching related activity: {str(e)}')
        else:
            messages.error(request, 'Please select a related activity.')
    
    # Get potential related activities (same equipment, different activity)
    potential_related = MaintenanceActivity.objects.filter(
        equipment=activity.equipment
    ).exclude(id=activity.id).order_by('-scheduled_start')[:20]
    
    context = {
        'activity': activity,
        'potential_related': potential_related,
    }
    return render(request, 'maintenance/attach_related.html', context)

__all__ = ["maintenance_list", "activity_list", "bulk_add_activity", "activity_detail", "add_activity", "edit_activity", "complete_activity", "overdue_maintenance", "delete_activity", "get_activities_data", "fetch_activities", "get_activity_details", "create_activity_api", "upload_activity_document", "change_activity_status", "attach_related_activity"]
