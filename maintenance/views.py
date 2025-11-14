"""
Views for maintenance management.
Fixed associations and improved functionality from original web2py controllers.
"""

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

from .models import (
    MaintenanceActivity, MaintenanceActivityType, 
    MaintenanceSchedule, MaintenanceChecklist,
    ActivityTypeCategory, ActivityTypeTemplate, MaintenanceReport,
    MaintenanceTimelineEntry
)
from equipment.models import Equipment
from core.models import EquipmentCategory, UserProfile
from equipment.models import Equipment, EquipmentDocument
from .forms import (
    MaintenanceActivityForm, MaintenanceScheduleForm, 
    MaintenanceActivityTypeForm, EnhancedMaintenanceActivityTypeForm,
    ActivityTypeCategoryForm, ActivityTypeTemplateForm
)
from events.models import CalendarEvent

# Import maintenance models and forms to avoid circular imports
from .models import (
    EquipmentCategorySchedule, GlobalSchedule, ScheduleOverride
)
from .forms import (
    EquipmentCategoryScheduleForm, GlobalScheduleForm, ScheduleOverrideForm
)

from django.contrib.auth.models import User

logger = logging.getLogger(__name__)





@login_required
def maintenance_list(request):
    """Main maintenance dashboard."""
    try:
        # Get upcoming maintenance
        upcoming_activities = MaintenanceActivity.objects.filter(
            scheduled_start__gte=timezone.now(),
            status__in=['scheduled', 'pending']
        ).select_related('equipment', 'activity_type').order_by('scheduled_start')[:10]
        
        # Get overdue maintenance
        overdue_activities = MaintenanceActivity.objects.filter(
            scheduled_end__lt=timezone.now(),
            status__in=['scheduled', 'pending']
        ).select_related('equipment', 'activity_type').order_by('scheduled_start')[:10]
        
        # Get in progress
        in_progress = MaintenanceActivity.objects.filter(
            status='in_progress'
        ).select_related('equipment', 'activity_type')
        
        # Statistics
        stats = {
            'total_activities': MaintenanceActivity.objects.count(),
            'pending_count': MaintenanceActivity.objects.filter(status='pending').count(),
            'overdue_count': overdue_activities.count(),
            'completed_this_month': MaintenanceActivity.objects.filter(
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
            upcoming_activities = MaintenanceActivity.objects.filter(
                scheduled_start__gte=timezone.now(),
                status__in=['scheduled', 'pending']
            ).order_by('scheduled_start')[:10]
            
            overdue_activities = MaintenanceActivity.objects.filter(
                scheduled_end__lt=timezone.now(),
                status__in=['scheduled', 'pending']
            ).order_by('scheduled_start')[:10]
            
            in_progress = MaintenanceActivity.objects.filter(
                status='in_progress'
            )
            
            stats = {
                'total_activities': MaintenanceActivity.objects.count(),
                'pending_count': MaintenanceActivity.objects.filter(status='pending').count(),
                'overdue_count': overdue_activities.count(),
                'completed_this_month': MaintenanceActivity.objects.filter(
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
        equipment_query = Equipment.objects.filter(is_active=True).select_related('location', 'location__parent_location', 'category')
        
        if selected_site_id and selected_site_id != 'all':
            try:
                selected_site = Location.objects.get(id=selected_site_id, is_site=True)
                equipment_query = equipment_query.filter(
                    Q(location_id=selected_site_id) | 
                    Q(location__parent_location_id=selected_site_id)
                )
            except Location.DoesNotExist:
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
                            activity_title = title_template.replace('{equipment}', equipment.name)
                            
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
                                
                                # Calculate frequency_days based on the frequency choice
                                if recurrence_frequency == 'custom':
                                    frequency_days = int(recurrence_frequency_days) if recurrence_frequency_days else 30
                                else:
                                    frequency_map = {
                                        'daily': 1,
                                        'weekly': 7,
                                        'monthly': 30,
                                        'quarterly': 90,
                                        'semi_annual': 180,
                                        'annual': 365,
                                    }
                                    frequency_days = frequency_map.get(recurrence_frequency, 30)
                                
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
def schedule_list(request):
    """List maintenance schedules."""
    try:
        schedules = MaintenanceSchedule.objects.select_related(
            'equipment', 'activity_type'
        ).filter(is_active=True)
        
        context = {'schedules': schedules}
        return render(request, 'maintenance/schedule_list.html', context)
        
    except Exception as e:
        logger.error(f"Database error in schedule_list: {str(e)}")
        
        # Try alternative query without select_related
        try:
            schedules = MaintenanceSchedule.objects.filter(is_active=True)
            context = {
                'schedules': schedules,
                'database_error': True,
                'error_message': 'Database schema issue detected. Some functionality may be limited.'
            }
            return render(request, 'maintenance/schedule_list.html', context)
            
        except Exception as fallback_error:
            logger.error(f"Fallback query also failed: {str(fallback_error)}")
            messages.error(request, 'Database connection issue. Please contact support.')
            return redirect('maintenance:maintenance_list')


@login_required
def add_schedule(request):
    """Add new maintenance schedule."""
    if request.method == 'POST':
        form = MaintenanceScheduleForm(request.POST, request=request)
        if form.is_valid():
            schedule = form.save(commit=False)
            schedule.created_by = request.user
            schedule.save()
            
            messages.success(request, f'Maintenance schedule created successfully!')
            return redirect('maintenance:schedule_detail', schedule_id=schedule.id)
    else:
        form = MaintenanceScheduleForm(request=request)
    
    context = {'form': form}
    return render(request, 'maintenance/add_schedule.html', context)


@login_required
def schedule_detail(request, schedule_id):
    """Display maintenance schedule details."""
    schedule = get_object_or_404(
        MaintenanceSchedule.objects.select_related('equipment', 'activity_type'),
        id=schedule_id
    )
    
    # Get recent activities for this schedule
    recent_activities = MaintenanceActivity.objects.filter(
        equipment=schedule.equipment,
        activity_type=schedule.activity_type
    ).order_by('-scheduled_start')[:10]
    
    context = {
        'schedule': schedule,
        'recent_activities': recent_activities,
    }
    
    return render(request, 'maintenance/schedule_detail.html', context)


@login_required
def edit_schedule(request, schedule_id):
    """Edit maintenance schedule."""
    schedule = get_object_or_404(MaintenanceSchedule, id=schedule_id)
    
    if request.method == 'POST':
        form = MaintenanceScheduleForm(request.POST, instance=schedule, request=request)
        if form.is_valid():
            schedule = form.save(commit=False)
            schedule.updated_by = request.user
            schedule.save()
            
            messages.success(request, 'Maintenance schedule updated successfully!')
            return redirect('maintenance:schedule_detail', schedule_id=schedule.id)
    else:
        form = MaintenanceScheduleForm(instance=schedule, request=request)
    
    context = {
        'form': form,
        'schedule': schedule,
    }
    
    return render(request, 'maintenance/edit_schedule.html', context)


@login_required
def generate_scheduled_activities(request):
    """Generate maintenance activities from schedules."""
    if request.method == 'POST':
        generated_count = 0
        schedules = MaintenanceSchedule.objects.filter(
            is_active=True,
            auto_generate=True
        )
        
        for schedule in schedules:
            activity = schedule.generate_next_activity()
            if activity:
                generated_count += 1
        
        messages.success(request, f'Generated {generated_count} new maintenance activities!')
        return redirect('maintenance:maintenance_list')
    
    # Show preview of what would be generated
    schedules_to_generate = []
    schedules = MaintenanceSchedule.objects.filter(
        is_active=True,
        auto_generate=True
    )
    
    for schedule in schedules:
        # Logic to determine if activity should be generated
        advance_date = timezone.now().date() + timedelta(days=schedule.advance_notice_days)
        # Add to preview list if needed
        schedules_to_generate.append(schedule)
    
    context = {
        'schedules_to_generate': schedules_to_generate,
    }
    
    return render(request, 'maintenance/generate_activities.html', context)


@login_required
def activity_type_list(request):
    """List maintenance activity types."""
    try:
        activity_types = MaintenanceActivityType.objects.filter(is_active=True)
        
        context = {'activity_types': activity_types}
        return render(request, 'maintenance/activity_type_list.html', context)
        
    except Exception as e:
        logger.error(f"Database error in activity_type_list: {str(e)}")
        
        # Try alternative query
        try:
            activity_types = MaintenanceActivityType.objects.all()
            
            context = {
                'activity_types': activity_types,
                'database_error': True,
                'error_message': 'Database schema issue detected. Some functionality may be limited.'
            }
            return render(request, 'maintenance/activity_type_list.html', context)
            
        except Exception as fallback_error:
            logger.error(f"Fallback query also failed: {str(fallback_error)}")
            messages.error(request, 'Database connection issue. Please contact support.')
            return redirect('maintenance:maintenance_list')


@login_required
def add_activity_type(request):
    """Add new maintenance activity type."""
    if request.method == 'POST':
        form = MaintenanceActivityTypeForm(request.POST)
        if form.is_valid():
            activity_type = form.save(commit=False)
            activity_type.created_by = request.user
            activity_type.save()
            form.save_m2m()  # Save many-to-many relationships
            
            messages.success(request, f'Activity type "{activity_type.name}" created successfully!')
            return redirect('maintenance:activity_type_list')
        else:
            # Debug: Log form errors
            print(f"Form errors: {form.errors}")
            print(f"Form data: {request.POST}")
            messages.error(request, f'Error creating activity type. Please check the form.')
    else:
        form = MaintenanceActivityTypeForm()
    
    # Debug: Log form field data
    print(f"Category choices: {list(form.fields['category'].queryset.values_list('name', flat=True))}")
    print(f"Equipment categories: {list(form.fields['applicable_equipment_categories'].queryset.values_list('name', flat=True))}")
    
    context = {'form': form}
    return render(request, 'maintenance/add_activity_type.html', context)


@login_required
def edit_activity_type(request, activity_type_id):
    """Edit maintenance activity type."""
    activity_type = get_object_or_404(MaintenanceActivityType, id=activity_type_id)
    
    if request.method == 'POST':
        form = MaintenanceActivityTypeForm(request.POST, instance=activity_type)
        if form.is_valid():
            activity_type = form.save(commit=False)
            activity_type.updated_by = request.user
            activity_type.save()
            form.save_m2m()  # Save many-to-many relationships
            
            messages.success(request, f'Activity type "{activity_type.name}" updated successfully!')
            return redirect('maintenance:activity_type_list')
        else:
            # Debug: Log form errors
            print(f"Form errors: {form.errors}")
            print(f"Form data: {request.POST}")
            messages.error(request, f'Error updating activity type. Please check the form.')
    else:
        form = MaintenanceActivityTypeForm(instance=activity_type)
    
    context = {
        'form': form,
        'activity_type': activity_type,
    }
    
    return render(request, 'maintenance/edit_activity_type.html', context)


@login_required
def import_activity_types_csv(request):
    """Import maintenance activity types from CSV."""
    if request.method == 'POST':
        if 'csv_file' not in request.FILES:
            messages.error(request, 'No file uploaded.')
            return redirect('maintenance:import_activity_types_csv')
            
        csv_file = request.FILES['csv_file']
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Please upload a CSV file.')
            return redirect('maintenance:import_activity_types_csv')

        try:
            file_data = csv_file.read().decode('utf-8')
            io_string = io.StringIO(file_data)
            reader = csv.DictReader(io_string)
            
            created_count = 0
            updated_count = 0
            
            for row in reader:
                name = row.get('name', '').strip()
                description = row.get('description', '').strip()
                estimated_duration_hours = row.get('estimated_duration_hours', '1').strip()
                frequency_days = row.get('frequency_days', '30').strip()
                is_mandatory = row.get('is_mandatory', 'false').strip().lower() in ['true', '1', 'yes']
                is_active = row.get('is_active', 'true').strip().lower() in ['true', '1', 'yes']
                
                if not name:
                    continue
                    
                # Get or create a default category if none exists
                default_category = ActivityTypeCategory.objects.filter(is_active=True).first()
                if not default_category:
                    default_category = ActivityTypeCategory.objects.create(
                        name='General',
                        description='Default category for imported activity types',
                        color='#007bff',
                        icon='fas fa-wrench',
                        is_active=True,
                        created_by=request.user
                    )
                
                activity_type, created = MaintenanceActivityType.objects.get_or_create(
                    name=name,
                    defaults={
                        'category': default_category,
                        'description': description,
                        'estimated_duration_hours': float(estimated_duration_hours) if estimated_duration_hours else 1.0,
                        'frequency_days': int(frequency_days) if frequency_days else 30,
                        'is_mandatory': is_mandatory,
                        'is_active': is_active,
                        'created_by': request.user,
                    }
                )
                
                if created:
                    created_count += 1
                else:
                    # Update existing activity type
                    activity_type.description = description
                    activity_type.estimated_duration_hours = float(estimated_duration_hours) if estimated_duration_hours else activity_type.estimated_duration_hours
                    activity_type.frequency_days = int(frequency_days) if frequency_days else activity_type.frequency_days
                    activity_type.is_mandatory = is_mandatory
                    activity_type.is_active = is_active
                    activity_type.updated_by = request.user
                    activity_type.save()
                    updated_count += 1
            
            messages.success(request, f'Successfully imported {created_count} new and updated {updated_count} existing activity types!')
            return redirect('maintenance:activity_type_list')
            
        except Exception as e:
            logger.error(f"Error processing CSV file: {str(e)}")
            messages.error(request, f'Error processing CSV file: {str(e)}')
            return redirect('maintenance:import_activity_types_csv')
    
    return render(request, 'maintenance/import_activity_types_csv.html')


@login_required
def export_activity_types_csv(request):
    """Export maintenance activity types to CSV file."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="activity_types_export.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'name', 'description', 'estimated_duration_hours', 'frequency_days', 
        'is_mandatory', 'is_active', 'created_at', 'updated_at'
    ])
    
    for activity_type in MaintenanceActivityType.objects.all():
        writer.writerow([
            activity_type.name,
            activity_type.description,
            activity_type.estimated_duration_hours,
            activity_type.frequency_days,
            activity_type.is_mandatory,
            activity_type.is_active,
            activity_type.created_at.strftime('%Y-%m-%d %H:%M:%S') if activity_type.created_at else '',
            activity_type.updated_at.strftime('%Y-%m-%d %H:%M:%S') if activity_type.updated_at else '',
        ])
    
    return response


@login_required
def export_maintenance_csv(request):
    """Export maintenance activities to CSV file."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="maintenance_activities_export.csv"'
    
    writer = csv.writer(response)
    
    # Write header
    writer.writerow([
        'Title',
        'Equipment',
        'Activity Type',
        'Status',
        'Priority',
        'Scheduled Start',
        'Scheduled End',
        'Actual Start',
        'Actual End',
        'Assigned To',
        'Required Status',
        'Tools Required',
        'Parts Required',
        'Safety Notes',
        'Completion Notes',
        'Next Due Date',
        'Description'
    ])
    
    # Get maintenance data
    activities = MaintenanceActivity.objects.select_related(
        'equipment', 'activity_type', 'assigned_to'
    ).all()
    
    # Apply filters if provided
    site_id = request.GET.get('site_id')
    status = request.GET.get('status')
    
    if site_id and site_id != 'all':
        activities = activities.filter(
            Q(equipment__location__parent_location_id=site_id) | 
            Q(equipment__location_id=site_id)
        )
    
    if status:
        activities = activities.filter(status=status)
    
    # Write data rows
    for activity in activities:
        writer.writerow([
            activity.title,
            activity.equipment.name,
            activity.activity_type.name,
            activity.status,
            activity.priority,
            activity.scheduled_start.isoformat() if activity.scheduled_start else '',
            activity.scheduled_end.isoformat() if activity.scheduled_end else '',
            activity.actual_start.isoformat() if activity.actual_start else '',
            activity.actual_end.isoformat() if activity.actual_end else '',
            activity.assigned_to.get_full_name() if activity.assigned_to else '',
            activity.required_status,
            activity.tools_required,
            activity.parts_required,
            activity.safety_notes,
            activity.completion_notes,
            activity.next_due_date.isoformat() if activity.next_due_date else '',
            activity.description
        ])
    
    return response


@login_required
@require_http_methods(["POST"])
def import_maintenance_csv(request):
    """Import maintenance activities from CSV file."""
    if 'csv_file' not in request.FILES:
        messages.error(request, 'No CSV file provided.')
        return redirect('maintenance:maintenance_list')
    
    csv_file = request.FILES['csv_file']
    
    if not csv_file.name.endswith('.csv'):
        messages.error(request, 'Please upload a CSV file.')
        return redirect('maintenance:maintenance_list')
    
    try:
        # Read CSV file
        file_data = csv_file.read().decode('utf-8')
        csv_data = csv.reader(io.StringIO(file_data))
        
        # Skip header row
        header = next(csv_data)
        
        # Import data (moved to top of file)
        from equipment.models import Equipment
        from django.contrib.auth.models import User
        from datetime import datetime
        from django.utils import timezone as django_timezone
        
        imported_count = 0
        error_count = 0
        
        for row_num, row in enumerate(csv_data, start=2):
            try:
                if len(row) < 3:  # Must have at least title, equipment, activity type
                    continue
                
                title = row[0].strip()
                equipment_name = row[1].strip()
                activity_type_name = row[2].strip()
                
                if not title or not equipment_name or not activity_type_name:
                    continue
                
                # Find equipment
                try:
                    equipment = Equipment.objects.get(name=equipment_name)
                except Equipment.DoesNotExist:
                    error_count += 1
                    continue
                
                # Get or create a default category if none exists
                default_category = ActivityTypeCategory.objects.filter(is_active=True).first()
                if not default_category:
                    default_category = ActivityTypeCategory.objects.create(
                        name='General',
                        description='Default category for imported activity types',
                        color='#007bff',
                        icon='fas fa-wrench',
                        is_active=True,
                        created_by=request.user
                    )
                
                # Find or create activity type
                activity_type, created = MaintenanceActivityType.objects.get_or_create(
                    name=activity_type_name,
                    defaults={
                        'category': default_category,
                        'description': f'Imported activity type: {activity_type_name}',
                        'estimated_duration_hours': 1,
                        'frequency_days': 365,
                        'created_by': request.user
                    }
                )
                
                # Parse data
                status = row[3].strip() if len(row) > 3 else 'scheduled'
                priority = row[4].strip() if len(row) > 4 else 'medium'
                
                # Validate status and priority
                valid_statuses = ['scheduled', 'pending', 'in_progress', 'completed', 'cancelled', 'overdue']
                valid_priorities = ['low', 'medium', 'high', 'critical']
                
                if status not in valid_statuses:
                    status = 'scheduled'
                if priority not in valid_priorities:
                    priority = 'medium'
                
                # Get user's timezone from profile (defaults to Central)
                user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
                user_timezone_str = user_profile.get_user_timezone()  # Returns 'America/Chicago' by default
                import pytz
                user_tz = pytz.timezone(user_timezone_str)
                
                # Parse dates - interpret naive datetimes as being in user's timezone
                scheduled_start = None
                scheduled_end = None
                actual_start = None
                actual_end = None
                next_due_date = None
                
                try:
                    if len(row) > 5 and row[5].strip():
                        scheduled_start = datetime.fromisoformat(row[5].strip())
                        if scheduled_start.tzinfo is None:
                            # Interpret naive datetime as being in user's timezone
                            scheduled_start = user_tz.localize(scheduled_start)
                        else:
                            # Already timezone-aware, convert to user's timezone for consistency
                            scheduled_start = scheduled_start.astimezone(user_tz)
                except ValueError:
                    pass
                
                try:
                    if len(row) > 6 and row[6].strip():
                        scheduled_end = datetime.fromisoformat(row[6].strip())
                        if scheduled_end.tzinfo is None:
                            # Interpret naive datetime as being in user's timezone
                            scheduled_end = user_tz.localize(scheduled_end)
                        else:
                            # Already timezone-aware, convert to user's timezone for consistency
                            scheduled_end = scheduled_end.astimezone(user_tz)
                except ValueError:
                    pass
                
                try:
                    if len(row) > 7 and row[7].strip():
                        actual_start = datetime.fromisoformat(row[7].strip())
                        if actual_start.tzinfo is None:
                            # Interpret naive datetime as being in user's timezone
                            actual_start = user_tz.localize(actual_start)
                        else:
                            # Already timezone-aware, convert to user's timezone for consistency
                            actual_start = actual_start.astimezone(user_tz)
                except ValueError:
                    pass
                
                try:
                    if len(row) > 8 and row[8].strip():
                        actual_end = datetime.fromisoformat(row[8].strip())
                        if actual_end.tzinfo is None:
                            # Interpret naive datetime as being in user's timezone
                            actual_end = user_tz.localize(actual_end)
                        else:
                            # Already timezone-aware, convert to user's timezone for consistency
                            actual_end = actual_end.astimezone(user_tz)
                except ValueError:
                    pass
                
                try:
                    if len(row) > 15 and row[15].strip():
                        next_due_date = datetime.fromisoformat(row[15].strip()).date()
                except ValueError:
                    pass
                
                # Find assigned user
                assigned_to = None
                if len(row) > 9 and row[9].strip():
                    assigned_name = row[9].strip()
                    # Try to find user by full name or username
                    users = User.objects.filter(
                        Q(first_name__icontains=assigned_name.split()[0]) |
                        Q(username=assigned_name)
                    )
                    if users.exists():
                        assigned_to = users.first()
                
                # Default scheduled dates if not provided (in user's timezone)
                if not scheduled_start:
                    scheduled_start = django_timezone.now().astimezone(user_tz)
                if not scheduled_end:
                    scheduled_end = scheduled_start + timedelta(hours=activity_type.estimated_duration_hours)
                
                # Create maintenance activity
                activity_data = {
                    'title': title,
                    'equipment': equipment,
                    'activity_type': activity_type,
                    'status': status,
                    'priority': priority,
                    'scheduled_start': scheduled_start,
                    'scheduled_end': scheduled_end,
                    'actual_start': actual_start,
                    'actual_end': actual_end,
                    'assigned_to': assigned_to,
                    'required_status': row[10].strip() if len(row) > 10 else '',
                    'tools_required': row[11].strip() if len(row) > 11 else '',
                    'parts_required': row[12].strip() if len(row) > 12 else '',
                    'safety_notes': row[13].strip() if len(row) > 13 else '',
                    'completion_notes': row[14].strip() if len(row) > 14 else '',
                    'next_due_date': next_due_date,
                    'description': row[16].strip() if len(row) > 16 else '',
                    'created_by': request.user
                }
                
                activity = MaintenanceActivity.objects.create(**activity_data)
                
                logger.info(f"Imported maintenance activity: {activity.title}")
                
                imported_count += 1
                
            except Exception as e:
                error_count += 1
                print(f"Error importing maintenance activity row {row_num}: {str(e)}")
                continue
        
        if imported_count > 0:
            messages.success(request, f'Successfully imported {imported_count} maintenance activities.')
        if error_count > 0:
            messages.warning(request, f'{error_count} rows had errors and were skipped.')
            
    except Exception as e:
        messages.error(request, f'Error reading CSV file: {str(e)}')
    
    return redirect('maintenance:maintenance_list')


@login_required
def export_maintenance_activities_csv(request):
    """Export all maintenance activities to CSV."""
    from equipment.models import EquipmentCategory
    from core.models import Location
    import pytz
    
    # Get user's timezone from profile (defaults to Central)
    user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
    user_timezone_str = user_profile.get_user_timezone()  # Returns 'America/Chicago' by default
    user_tz = pytz.timezone(user_timezone_str)
    
    # Get filter parameters (same as reports page)
    category_id = request.GET.get('category')
    location_id = request.GET.get('location')
    status_filter = request.GET.get('status')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # Base queryset
    activities_queryset = MaintenanceActivity.objects.select_related(
        'equipment', 'equipment__category', 'equipment__location', 'activity_type', 'assigned_to'
    ).all()
    
    # Apply filters
    if category_id:
        activities_queryset = activities_queryset.filter(equipment__category_id=category_id)
    if location_id:
        activities_queryset = activities_queryset.filter(equipment__location_id=location_id)
    if status_filter:
        activities_queryset = activities_queryset.filter(status=status_filter)
    if date_from:
        try:
            from datetime import datetime
            # Parse date string and convert to timezone-aware datetime at start of day in user's timezone
            date_from_naive = datetime.strptime(date_from, '%Y-%m-%d').date()
            date_from_dt = user_tz.localize(datetime.combine(date_from_naive, datetime.min.time()))
            # Convert to UTC for database query (Django stores datetimes in UTC)
            date_from_utc = date_from_dt.astimezone(pytz.UTC)
            activities_queryset = activities_queryset.filter(scheduled_start__gte=date_from_utc)
        except ValueError:
            pass
    if date_to:
        try:
            from datetime import datetime
            # Parse date string and convert to timezone-aware datetime at end of day in user's timezone
            date_to_naive = datetime.strptime(date_to, '%Y-%m-%d').date()
            date_to_dt = user_tz.localize(datetime.combine(date_to_naive, datetime.max.time()))
            # Convert to UTC for database query
            date_to_utc = date_to_dt.astimezone(pytz.UTC)
            activities_queryset = activities_queryset.filter(scheduled_start__lte=date_to_utc)
        except ValueError:
            pass
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="maintenance_activities_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    
    # Write header
    writer.writerow([
        'ID',
        'Title',
        'Equipment',
        'Category',
        'Location',
        'Activity Type',
        'Status',
        'Priority',
        'Scheduled Start',
        'Scheduled End',
        'Actual Start',
        'Actual End',
        'Duration (Hours)',
        'Assigned To',
        'Description',
        'Completion Notes',
        'Created At',
        'Updated At'
    ])
    
    # Write data
    for activity in activities_queryset.order_by('-scheduled_start'):
        duration = None
        if activity.actual_start and activity.actual_end:
            duration = (activity.actual_end - activity.actual_start).total_seconds() / 3600
        
        writer.writerow([
            activity.id,
            activity.title or '',
            activity.equipment.name if activity.equipment else '',
            activity.equipment.category.name if activity.equipment and activity.equipment.category else '',
            activity.equipment.location.name if activity.equipment and activity.equipment.location else '',
            activity.activity_type.name if activity.activity_type else '',
            activity.get_status_display(),
            activity.get_priority_display(),
            activity.scheduled_start.strftime('%Y-%m-%d %H:%M:%S') if activity.scheduled_start else '',
            activity.scheduled_end.strftime('%Y-%m-%d %H:%M:%S') if activity.scheduled_end else '',
            activity.actual_start.strftime('%Y-%m-%d %H:%M:%S') if activity.actual_start else '',
            activity.actual_end.strftime('%Y-%m-%d %H:%M:%S') if activity.actual_end else '',
            round(duration, 2) if duration else '',
            activity.assigned_to.get_full_name() if activity.assigned_to else '',
            (activity.description or '').replace('\n', ' ').replace('\r', ''),
            (activity.completion_notes or '').replace('\n', ' ').replace('\r', ''),
            activity.created_at.strftime('%Y-%m-%d %H:%M:%S') if activity.created_at else '',
            activity.updated_at.strftime('%Y-%m-%d %H:%M:%S') if activity.updated_at else '',
        ])
    
    return response


@login_required
def export_maintenance_schedules_csv(request):
    """Export maintenance schedules to CSV file."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="maintenance_schedules_export.csv"'
    
    writer = csv.writer(response)
    
    # Write header
    writer.writerow([
        'Equipment',
        'Activity Type',
        'Frequency',
        'Frequency Days',
        'Start Date',
        'End Date',
        'Last Generated',
        'Auto Generate',
        'Advance Notice Days',
        'Is Active'
    ])
    
    # Get schedule data
    schedules = MaintenanceSchedule.objects.select_related(
        'equipment', 'activity_type'
    ).all()
    
    # Apply site filter if provided
    site_id = request.GET.get('site_id')
    if site_id and site_id != 'all':
        schedules = schedules.filter(
            Q(equipment__location__parent_location_id=site_id) | 
            Q(equipment__location_id=site_id)
        )
    
    # Write data rows
    for schedule in schedules:
        writer.writerow([
            schedule.equipment.name,
            schedule.activity_type.name,
            schedule.frequency,
            schedule.frequency_days,
            schedule.start_date.isoformat() if schedule.start_date else '',
            schedule.end_date.isoformat() if schedule.end_date else '',
            schedule.last_generated.isoformat() if schedule.last_generated else '',
            schedule.auto_generate,
            schedule.advance_notice_days,
            schedule.is_active
        ])
    
    return response


@login_required
def maintenance_reports(request):
    """Maintenance reports and analytics with timeline and export."""
    from equipment.models import EquipmentCategory
    from core.models import Location
    import pytz
    
    # Get user's timezone from profile (defaults to Central)
    user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
    user_timezone_str = user_profile.get_user_timezone()  # Returns 'America/Chicago' by default
    user_tz = pytz.timezone(user_timezone_str)
    
    # Get filter parameters
    category_id = request.GET.get('category')
    location_id = request.GET.get('location')
    status_filter = request.GET.get('status')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # Base queryset for activities
    activities_queryset = MaintenanceActivity.objects.select_related(
        'equipment', 'equipment__category', 'equipment__location', 'activity_type', 'assigned_to'
    ).all()
    
    # Apply filters
    if category_id:
        activities_queryset = activities_queryset.filter(equipment__category_id=category_id)
    if location_id:
        activities_queryset = activities_queryset.filter(equipment__location_id=location_id)
    if status_filter:
        activities_queryset = activities_queryset.filter(status=status_filter)
    if date_from:
        try:
            from datetime import datetime
            # Parse date string and convert to timezone-aware datetime at start of day in user's timezone
            date_from_naive = datetime.strptime(date_from, '%Y-%m-%d').date()
            date_from_dt = user_tz.localize(datetime.combine(date_from_naive, datetime.min.time()))
            # Convert to UTC for database query (Django stores datetimes in UTC)
            date_from_utc = date_from_dt.astimezone(pytz.UTC)
            activities_queryset = activities_queryset.filter(scheduled_start__gte=date_from_utc)
        except ValueError:
            pass
    if date_to:
        try:
            from datetime import datetime
            # Parse date string and convert to timezone-aware datetime at end of day in user's timezone
            date_to_naive = datetime.strptime(date_to, '%Y-%m-%d').date()
            date_to_dt = user_tz.localize(datetime.combine(date_to_naive, datetime.max.time()))
            # Convert to UTC for database query
            date_to_utc = date_to_dt.astimezone(pytz.UTC)
            activities_queryset = activities_queryset.filter(scheduled_start__lte=date_to_utc)
        except ValueError:
            pass
    
    # Get all activities for timeline (sorted by scheduled_start)
    all_activities = activities_queryset.order_by('-scheduled_start')
    
    # Activity status distribution
    status_stats = activities_queryset.values('status').annotate(
        count=Count('id')
    ).order_by('status')
    
    # Equipment with most maintenance
    equipment_stats = activities_queryset.values(
        'equipment__name'
    ).annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # Monthly completion stats
    monthly_stats = activities_queryset.filter(
        status='completed',
        actual_end__gte=timezone.now() - timedelta(days=365)
    ).extra(
        {'month': 'EXTRACT(month FROM actual_end)'}
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')
    
    # Daily completion stats for timeline chart (last 90 days)
    daily_completions = {}
    completed_activities = activities_queryset.filter(
        status='completed',
        actual_end__isnull=False
    ).order_by('actual_end')
    
    # Get date range (default to last 30 days, or use filter dates)
    # Use user's timezone for date calculations
    now_in_user_tz = timezone.now().astimezone(user_tz)
    if date_from:
        try:
            from datetime import datetime
            start_date = datetime.strptime(date_from, '%Y-%m-%d').date()
        except ValueError:
            start_date = (now_in_user_tz - timedelta(days=30)).date()
    else:
        start_date = (now_in_user_tz - timedelta(days=30)).date()
    
    if date_to:
        try:
            from datetime import datetime
            end_date = datetime.strptime(date_to, '%Y-%m-%d').date()
        except ValueError:
            end_date = now_in_user_tz.date()
    else:
        end_date = now_in_user_tz.date()
    
    # Initialize all dates in range with 0
    current_date = start_date
    while current_date <= end_date:
        daily_completions[current_date.strftime('%Y-%m-%d')] = 0
        current_date += timedelta(days=1)
    
    # Count completions per day - Use database aggregation instead of Python loop
    # Convert dates to timezone-aware datetimes for database queries
    from django.db.models.functions import TruncDate
    from datetime import datetime
    start_dt = user_tz.localize(datetime.combine(start_date, datetime.min.time()))
    start_utc = start_dt.astimezone(pytz.UTC)
    end_dt = user_tz.localize(datetime.combine(end_date, datetime.max.time()))
    end_utc = end_dt.astimezone(pytz.UTC)
    
    daily_completions_queryset = completed_activities.filter(
        actual_end__gte=start_utc,
        actual_end__lte=end_utc
    ).annotate(
        date=TruncDate('actual_end')
    ).values('date').annotate(
        count=Count('id')
    ).order_by('date')
    
    for item in daily_completions_queryset:
        date_key = item['date'].strftime('%Y-%m-%d')
        daily_completions[date_key] = item['count']
    
    # Convert to JSON for chart
    import json
    daily_completions_json = json.dumps(daily_completions)
    
    # Generate maintenance trends (monthly view for all equipment)
    # Use the same date range or default to last 12 months for trends
    # Convert dates to timezone-aware datetimes for database queries
    trends_start_dt = user_tz.localize(datetime.combine(start_date, datetime.min.time()))
    trends_start_utc = trends_start_dt.astimezone(pytz.UTC)
    trends_end_dt = user_tz.localize(datetime.combine(end_date, datetime.max.time()))
    trends_end_utc = trends_end_dt.astimezone(pytz.UTC)
    
    # For trends, group by month - Use database aggregation instead of Python loop
    from django.db.models.functions import TruncMonth
    monthly_trends_queryset = activities_queryset.filter(
        scheduled_start__gte=trends_start_utc, 
        scheduled_start__lte=trends_end_utc
    ).annotate(
        month=TruncMonth('scheduled_start')
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')
    
    monthly_trends = {}
    for item in monthly_trends_queryset:
        month_key = item['month'].strftime('%Y-%m')
        monthly_trends[month_key] = item['count']
    
    # Create labels and data for trends chart
    trends_labels = []
    trends_data = []
    
    # Generate all months in range
    current_date = start_date.replace(day=1)
    while current_date <= end_date:
        month_key = current_date.strftime('%Y-%m')
        trends_labels.append(current_date.strftime('%b %Y'))
        trends_data.append(monthly_trends.get(month_key, 0))
        # Move to next month
        if current_date.month == 12:
            current_date = current_date.replace(year=current_date.year + 1, month=1)
        else:
            current_date = current_date.replace(month=current_date.month + 1)
    
    trends_json = json.dumps({
        'labels': trends_labels,
        'data': trends_data
    })
    
    # Build timeline events
    timeline_events = []
    for activity in all_activities[:100]:  # Limit to 100 most recent for performance
        timeline_events.append({
            'type': 'maintenance',
            'title': activity.title or (activity.activity_type.name if activity.activity_type else 'Maintenance'),
            'description': activity.description or '',
            'timestamp': activity.scheduled_start,
            'status': activity.status,
            'priority': activity.priority,
            'equipment': activity.equipment.name if activity.equipment else 'Unknown',
            'category': activity.equipment.category.name if activity.equipment and activity.equipment.category else 'N/A',
            'location': activity.equipment.location.name if activity.equipment and activity.equipment.location else 'N/A',
            'scheduled_end': activity.scheduled_end,
            'actual_start': activity.actual_start,
            'actual_end': activity.actual_end,
            'id': activity.id,
        })
    
    # Get filter options
    categories = EquipmentCategory.objects.filter(is_active=True).order_by('name')
    locations = Location.objects.filter(is_active=True).order_by('name')
    
    context = {
        'status_stats': status_stats,
        'equipment_stats': equipment_stats,
        'monthly_stats': monthly_stats,
        'timeline_events': timeline_events,
        'all_activities': all_activities,
        'daily_completions': daily_completions_json,
        'maintenance_trends': trends_json,
        'categories': categories,
        'locations': locations,
        'selected_category': int(category_id) if category_id else None,
        'selected_location': int(location_id) if location_id else None,
        'selected_status': status_filter,
        'date_from': date_from,
        'date_to': date_to,
    }
    
    return render(request, 'maintenance/reports.html', context)


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
        
        # Delete associated calendar events before deleting the activity
        from events.models import CalendarEvent
        associated_events = CalendarEvent.objects.filter(maintenance_activity=activity)
        events_deleted = associated_events.count()
        
        # Delete the calendar events first
        associated_events.delete()
        
        # Invalidate dashboard cache
        try:
            from core.views import invalidate_dashboard_cache
            invalidate_dashboard_cache(user_id=request.user.id)
        except Exception as cache_error:
            logger.warning(f"Could not invalidate dashboard cache: {cache_error}")
        
        # Now delete the maintenance activity
        activity.delete()
        
        if events_deleted > 0:
            messages.success(request, f'Maintenance activity "{activity_title}" and {events_deleted} associated calendar event(s) deleted successfully!')
        else:
            messages.success(request, f'Maintenance activity "{activity_title}" deleted successfully!')
        
        return redirect('maintenance:maintenance_list')
    
    context = {'activity': activity}
    return render(request, 'maintenance/delete_activity.html', context)


@login_required
def delete_schedule(request, schedule_id):
    """Delete maintenance schedule."""
    schedule = get_object_or_404(MaintenanceSchedule, id=schedule_id)
    
    if request.method == 'POST':
        schedule_name = f"{schedule.equipment.name} - {schedule.activity_type.name}"
        schedule.delete()
        messages.success(request, f'Maintenance schedule "{schedule_name}" deleted successfully!')
        return redirect('maintenance:schedules')
    
    context = {'schedule': schedule}
    return render(request, 'maintenance/delete_schedule.html', context)


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
def generate_maintenance_activities(request):
    """Alias for generate_scheduled_activities to match URL pattern."""
    return generate_scheduled_activities(request)

# Enhanced Activity Type Management Views

@login_required
def activity_type_categories(request):
    """List activity type categories."""
    categories = ActivityTypeCategory.objects.filter(is_active=True).annotate(
        activity_count=Count('activity_types')
    ).order_by('sort_order', 'name')
    
    context = {
        'categories': categories,
        'page_title': 'Activity Type Categories'
    }
    return render(request, 'maintenance/activity_type_categories.html', context)


@login_required
def add_activity_type_category(request):
    """Add new activity type category."""
    if request.method == 'POST':
        form = ActivityTypeCategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.created_by = request.user
            category.save()
            messages.success(request, f'Activity type category "{category.name}" created successfully!')
            return redirect('maintenance:activity_type_categories')
    else:
        form = ActivityTypeCategoryForm()
    
    context = {
        'form': form,
        'page_title': 'Add Activity Type Category'
    }
    return render(request, 'maintenance/add_activity_type_category.html', context)


@login_required
def edit_activity_type_category(request, category_id):
    """Edit activity type category and manage its activity types."""
    category = get_object_or_404(ActivityTypeCategory, id=category_id)
    
    # Get activity types for this category
    activity_types = MaintenanceActivityType.objects.filter(
        category=category,
        is_active=True
    ).order_by('name')
    
    if request.method == 'POST':
        form = ActivityTypeCategoryForm(request.POST, instance=category)
        if form.is_valid():
            category = form.save(commit=False)
            category.updated_by = request.user
            category.save()
            messages.success(request, f'Activity type category "{category.name}" updated successfully!')
            return redirect('maintenance:activity_type_categories')
    else:
        form = ActivityTypeCategoryForm(instance=category)
    
    context = {
        'form': form,
        'category': category,
        'activity_types': activity_types,
        'page_title': 'Edit Activity Type Category'
    }
    return render(request, 'maintenance/edit_activity_type_category.html', context)


@login_required
def activity_type_templates(request):
    """List activity type templates."""
    templates = ActivityTypeTemplate.objects.filter(is_active=True).select_related(
        'equipment_category', 'category'
    ).order_by('equipment_category__name', 'sort_order', 'name')
    
    equipment_categories = EquipmentCategory.objects.filter(is_active=True)
    
    # Filter by equipment category if specified
    category_filter = request.GET.get('category')
    if category_filter:
        templates = templates.filter(equipment_category_id=category_filter)
    
    context = {
        'templates': templates,
        'equipment_categories': equipment_categories,
        'selected_category': category_filter,
        'page_title': 'Activity Type Templates'
    }
    return render(request, 'maintenance/activity_type_templates.html', context)


@login_required
def add_activity_type_template(request):
    """Add new activity type template."""
    if request.method == 'POST':
        form = ActivityTypeTemplateForm(request.POST)
        if form.is_valid():
            template = form.save(commit=False)
            template.created_by = request.user
            template.save()
            messages.success(request, f'Activity type template "{template.name}" created successfully!')
            return redirect('maintenance:activity_type_templates')
    else:
        form = ActivityTypeTemplateForm()
    
    context = {
        'form': form,
        'page_title': 'Add Activity Type Template'
    }
    return render(request, 'maintenance/add_activity_type_template.html', context)


@login_required
def edit_activity_type_template(request, template_id):
    """Edit activity type template."""
    template = get_object_or_404(ActivityTypeTemplate, id=template_id)
    
    if request.method == 'POST':
        form = ActivityTypeTemplateForm(request.POST, instance=template)
        if form.is_valid():
            template = form.save(commit=False)
            template.updated_by = request.user
            template.save()
            messages.success(request, f'Activity type template "{template.name}" updated successfully!')
            return redirect('maintenance:activity_type_templates')
    else:
        form = ActivityTypeTemplateForm(instance=template)
    
    context = {
        'form': form,
        'template': template,
        'page_title': 'Edit Activity Type Template'
    }
    return render(request, 'maintenance/edit_activity_type_template.html', context)


@login_required
def enhanced_activity_type_list(request):
    """Enhanced activity type list with categories and filtering."""
    activity_types = MaintenanceActivityType.objects.filter(is_active=True).select_related(
        'category', 'template'
    ).prefetch_related('applicable_equipment_categories')
    
    categories = ActivityTypeCategory.objects.filter(is_active=True).order_by('sort_order', 'name')
    
    # Filter by category if specified
    category_filter = request.GET.get('category')
    if category_filter:
        activity_types = activity_types.filter(category_id=category_filter)
    
    # Search functionality
    search_query = request.GET.get('search', '').strip()
    if search_query:
        activity_types = activity_types.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    context = {
        'activity_types': activity_types,
        'categories': categories,
        'selected_category': category_filter,
        'search_query': search_query,
        'page_title': 'Activity Types'
    }
    return render(request, 'maintenance/enhanced_activity_type_list.html', context)


@login_required
def enhanced_add_activity_type(request):
    """Enhanced add activity type with template support."""
    # Check if category is pre-selected
    category_id = request.GET.get('category')
    initial_data = {}
    
    if category_id:
        try:
            category = ActivityTypeCategory.objects.get(id=category_id)
            initial_data['category'] = category
        except ActivityTypeCategory.DoesNotExist:
            pass
    
    if request.method == 'POST':
        form = EnhancedMaintenanceActivityTypeForm(request.POST)
        if form.is_valid():
            activity_type = form.save(commit=False)
            activity_type.created_by = request.user
            activity_type.save()
            form.save_m2m()  # Save many-to-many relationships
            messages.success(request, f'Activity type "{activity_type.name}" created successfully!')
            
            # Redirect back to category if specified
            if category_id:
                return redirect('maintenance:category_activity_types', category_id=category_id)
            return redirect('maintenance:enhanced_activity_type_list')
    else:
        form = EnhancedMaintenanceActivityTypeForm(initial=initial_data)
    
    context = {
        'form': form,
        'page_title': 'Add Activity Type',
        'selected_category_id': category_id
    }
    return render(request, 'maintenance/enhanced_add_activity_type.html', context)


@login_required
def enhanced_edit_activity_type(request, activity_type_id):
    """Enhanced edit activity type."""
    activity_type = get_object_or_404(MaintenanceActivityType, id=activity_type_id)
    
    if request.method == 'POST':
        form = EnhancedMaintenanceActivityTypeForm(request.POST, instance=activity_type)
        if form.is_valid():
            activity_type = form.save(commit=False)
            activity_type.updated_by = request.user
            activity_type.save()
            form.save_m2m()  # Save many-to-many relationships
            messages.success(request, f'Activity type "{activity_type.name}" updated successfully!')
            return redirect('maintenance:enhanced_activity_type_list')
    else:
        form = EnhancedMaintenanceActivityTypeForm(instance=activity_type)
    
    context = {
        'form': form,
        'activity_type': activity_type,
        'page_title': 'Edit Activity Type'
    }
    return render(request, 'maintenance/enhanced_edit_activity_type.html', context)


@login_required
def category_activity_types(request, category_id):
    """Manage activity types within a specific category."""
    category = get_object_or_404(ActivityTypeCategory, id=category_id)
    
    # Get activity types for this category
    activity_types = MaintenanceActivityType.objects.filter(
        category=category,
        is_active=True
    ).prefetch_related('applicable_equipment_categories').order_by('name')
    
    # Search functionality
    search_query = request.GET.get('search', '').strip()
    if search_query:
        activity_types = activity_types.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    context = {
        'category': category,
        'activity_types': activity_types,
        'search_query': search_query,
        'page_title': f'Activity Types - {category.name}'
    }
    return render(request, 'maintenance/category_activity_types.html', context)


# AJAX endpoints for dynamic form updates

@login_required
@require_http_methods(["GET"])
def get_activity_type_templates(request):
    """Get activity type templates for a specific equipment category."""
    equipment_category_id = request.GET.get('equipment_category_id')
    
    if not equipment_category_id:
        return JsonResponse({'templates': []})
    
    templates = ActivityTypeTemplate.objects.filter(
        equipment_category_id=equipment_category_id,
        is_active=True
    ).select_related('category').order_by('sort_order', 'name')
    
    template_data = []
    for template in templates:
        template_data.append({
            'id': template.id,
            'name': template.name,
            'category_id': template.category.id,
            'category_name': template.category.name,
            'description': template.description,
            'estimated_duration_hours': template.estimated_duration_hours,
            'frequency_days': template.frequency_days,
            'is_mandatory': template.is_mandatory,
            'default_tools_required': template.default_tools_required,
            'default_parts_required': template.default_parts_required,
            'default_safety_notes': template.default_safety_notes,
            'checklist_template': template.checklist_template,
        })
    
    return JsonResponse({'templates': template_data})


@login_required
@require_http_methods(["GET"])
def get_template_details(request, template_id):
    """Get details of a specific template."""
    template = get_object_or_404(ActivityTypeTemplate, id=template_id)
    
    template_data = {
        'id': template.id,
        'name': template.name,
        'category_id': template.category.id,
        'category_name': template.category.name,
        'description': template.description,
        'estimated_duration_hours': template.estimated_duration_hours,
        'frequency_days': template.frequency_days,
        'is_mandatory': template.is_mandatory,
        'default_tools_required': template.default_tools_required,
        'default_parts_required': template.default_parts_required,
        'default_safety_notes': template.default_safety_notes,
        'checklist_template': template.checklist_template,
    }
    
    return JsonResponse(template_data)


@login_required
@require_http_methods(["GET"])
def get_activity_type_suggestions(request):
    """Get activity type suggestions based on equipment selection."""
    equipment_id = request.GET.get('equipment_id')
    
    if not equipment_id:
        return JsonResponse({'suggestions': []})
    
    try:
        equipment = Equipment.objects.get(id=equipment_id)
        
        # Get activity types applicable to this equipment's category
        activity_types = MaintenanceActivityType.objects.filter(
            applicable_equipment_categories=equipment.category,
            is_active=True
        ).select_related('category')
        
        suggestions = []
        for activity_type in activity_types:
            suggestions.append({
                'id': activity_type.id,
                'name': activity_type.name,
                'category_name': activity_type.category.name,
                'description': activity_type.description,
                'estimated_duration_hours': activity_type.estimated_duration_hours,
                'frequency_days': activity_type.frequency_days,
                'tools_required': activity_type.tools_required,
                'parts_required': activity_type.parts_required,
                'safety_notes': activity_type.safety_notes,
            })
        
        return JsonResponse({
            'suggestions': suggestions,
            'equipment_category': equipment.category.name if equipment.category else None
        })
    
    except Equipment.DoesNotExist:
        return JsonResponse({'suggestions': []})


@login_required
@require_http_methods(["POST"])
def create_activity_type_from_template(request):
    """Create a new activity type from a template."""
    template_id = request.POST.get('template_id')
    custom_name = request.POST.get('custom_name', '')
    
    if not template_id:
        return JsonResponse({'success': False, 'error': 'Template ID is required'})
    
    try:
        template = ActivityTypeTemplate.objects.get(id=template_id)
        
        # Generate a unique name if not provided
        if not custom_name:
            custom_name = f"{template.name} - {template.equipment_category.name}"
        
        # Check if activity type with this name already exists
        if MaintenanceActivityType.objects.filter(name=custom_name).exists():
            return JsonResponse({
                'success': False, 
                'error': f'Activity type with name "{custom_name}" already exists'
            })
        
        # Create new activity type from template
        activity_type = MaintenanceActivityType.objects.create(
            name=custom_name,
            category=template.category,
            template=template,
            description=template.description,
            estimated_duration_hours=template.estimated_duration_hours,
            frequency_days=template.frequency_days,
            is_mandatory=template.is_mandatory,
            tools_required=template.default_tools_required,
            parts_required=template.default_parts_required,
            safety_notes=template.default_safety_notes,
            created_by=request.user
        )
        
        # Add equipment category association
        activity_type.applicable_equipment_categories.add(template.equipment_category)
        
        return JsonResponse({
            'success': True,
            'activity_type_id': activity_type.id,
            'message': f'Activity type "{activity_type.name}" created successfully!'
        })
        
    except ActivityTypeTemplate.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Template not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


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
        
        # Convert datetimes to UTC for API response - JavaScript will format in user's timezone
        def convert_to_utc(dt):
            if not dt:
                return None
            # If already timezone-aware, convert to UTC
            if timezone.is_aware(dt):
                return dt.astimezone(pytz.UTC)
            # If naive, assume UTC
            return timezone.make_aware(dt, pytz.UTC)
        
        # Convert to UTC before formatting (JavaScript will handle timezone conversion)
        scheduled_start_utc = convert_to_utc(activity.scheduled_start) if activity.scheduled_start else None
        scheduled_end_utc = convert_to_utc(activity.scheduled_end) if activity.scheduled_end else None
        actual_start_utc = convert_to_utc(activity.actual_start) if activity.actual_start else None
        actual_end_utc = convert_to_utc(activity.actual_end) if activity.actual_end else None
        
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
            'scheduled_start': scheduled_start_utc.isoformat() if scheduled_start_utc else None,
            'scheduled_end': scheduled_end_utc.isoformat() if scheduled_end_utc else None,
            'actual_start': actual_start_utc.isoformat() if actual_start_utc else None,
            'actual_end': actual_end_utc.isoformat() if actual_end_utc else None,
            'timezone': user_timezone_str,  # Include timezone info for JavaScript to use for formatting
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


# Maintenance Report Views
@login_required
def report_list(request):
    """List all maintenance reports with filtering."""
    try:
        queryset = MaintenanceReport.objects.select_related(
            'activity', 'activity__equipment', 'uploaded_by'
        ).all()
        
        # Filtering
        report_type = request.GET.get('report_type')
        if report_type:
            queryset = queryset.filter(report_type=report_type)
            
        activity_id = request.GET.get('activity')
        if activity_id:
            queryset = queryset.filter(activity_id=activity_id)
            
        is_processed = request.GET.get('is_processed')
        if is_processed is not None:
            queryset = queryset.filter(is_processed=is_processed == 'true')
        
        search_term = request.GET.get('search', '')
        if search_term:
            queryset = queryset.filter(
                Q(title__icontains=search_term) |
                Q(activity__title__icontains=search_term) |
                Q(technician_name__icontains=search_term) |
                Q(content__icontains=search_term)
            )
        
        # Pagination
        paginator = Paginator(queryset, 25)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'page_obj': page_obj,
            'report_types': MaintenanceReport.REPORT_TYPES,
        }
        
        return render(request, 'maintenance/report_list.html', context)
        
    except Exception as e:
        logger.error(f"Error in report_list: {str(e)}")
        messages.error(request, 'Failed to load maintenance reports.')
        return redirect('maintenance_list')


@login_required
def report_detail(request, report_id):
    """View detailed information about a maintenance report."""
    try:
        report = get_object_or_404(MaintenanceReport, id=report_id)
        
        context = {
            'report': report,
            'issues': report.extract_issues(),
            'parts_replaced': report.extract_parts_replaced(),
            'measurements': report.extract_measurements(),
        }
        
        return render(request, 'maintenance/report_detail.html', context)
        
    except Exception as e:
        logger.error(f"Error in report_detail: {str(e)}")
        messages.error(request, 'Failed to load report details.')
        return redirect('report_list')


@login_required
@require_http_methods(["POST"])
def upload_report(request):
    """Upload a new maintenance report."""
    try:
        activity_id = request.POST.get('activity_id')
        title = request.POST.get('title')
        report_type = request.POST.get('report_type', 'completion')
        content = request.POST.get('content', '')
        document = request.FILES.get('document')
        
        if not activity_id or not title:
            return JsonResponse({'error': 'Activity ID and title are required'}, status=400)
        
        activity = get_object_or_404(MaintenanceActivity, id=activity_id)
        
        report = MaintenanceReport.objects.create(
            activity=activity,
            title=title,
            report_type=report_type,
            content=content,
            document=document,
            uploaded_by=request.user,
            created_by=request.user,
            updated_by=request.user
        )
        
        # Auto-process the report if content is provided
        if content:
            try:
                # Basic text analysis
                analyzed_data = analyze_report_content(content)
                report.analyzed_data = analyzed_data
                report.is_processed = True
                report.save()
            except Exception as e:
                logger.error(f"Error processing report {report.id}: {str(e)}")
                report.processing_errors = str(e)
                report.save()
        
        return JsonResponse({
            'success': True,
            'report_id': report.id,
            'message': 'Report uploaded successfully'
        })
        
    except Exception as e:
        logger.error(f"Error uploading report: {str(e)}")
        return JsonResponse({'error': 'Failed to upload report'}, status=500)


@login_required
@require_http_methods(["POST"])
def analyze_report(request, report_id):
    """Analyze a maintenance report to extract structured data."""
    try:
        report = get_object_or_404(MaintenanceReport, id=report_id)
        
        if not report.content:
            return JsonResponse({'error': 'No content to analyze'}, status=400)
        
        # Analyze the content
        analyzed_data = analyze_report_content(report.content)
        
        # Update the report
        report.analyzed_data = analyzed_data
        report.is_processed = True
        report.processing_errors = ''
        report.save()
        
        return JsonResponse({
            'success': True,
            'analyzed_data': analyzed_data,
            'message': 'Report analyzed successfully'
        })
        
    except Exception as e:
        logger.error(f"Error analyzing report: {str(e)}")
        return JsonResponse({'error': 'Failed to analyze report'}, status=500)


def analyze_report_content(content):
    """Analyze report content to extract structured data."""
    analyzed_data = {
        'issues': [],
        'parts_replaced': [],
        'measurements': [],
        'dates': [],
        'technicians': [],
        'work_hours': None,
    }
    import re
    # Convert to lowercase for case-insensitive matching
    content_lower = content.lower()

    # --- Enhanced: Extract issues from 'Issues found:' sections and bullet points ---
    # Find 'issues found:' or 'issues:' section
    issues_section = re.search(r'(issues found:|issues:)([\s\S]+?)(\n\s*\n|$)', content, re.IGNORECASE)
    if issues_section:
        issues_block = issues_section.group(2)
        # Extract bullet points or lines
        for line in issues_block.splitlines():
            line = line.strip('-•* ').strip()
            if not line:
                continue
            # Only consider lines that are not empty and not a section header
            severity = 'medium'  # Default severity
            lcline = line.lower()
            if any(word in lcline for word in ['critical', 'severe', 'emergency']):
                severity = 'critical'
            elif any(word in lcline for word in ['major', 'serious']):
                severity = 'high'
            elif any(word in lcline for word in ['minor', 'small']):
                severity = 'low'
            analyzed_data['issues'].append({
                'text': line,
                'severity': severity,
                'position': content.find(line)
            })

    # --- Existing: Extract issues (basic pattern matching) ---
    issue_patterns = [
        r'issue[s]?\s*:?  *([^.\n]+)',
        r'problem[s]?\s*:?  *([^.\n]+)',
        r'fault[s]?\s*:?  *([^.\n]+)',
        r'error[s]?\s*:?  *([^.\n]+)',
        r'failure[s]?\s*:?  *([^.\n]+)',
    ]
    for pattern in issue_patterns:
        matches = re.finditer(pattern, content_lower)
        for match in matches:
            issue_text = match.group(1).strip()
            severity = 'medium'  # Default severity
            if any(word in issue_text for word in ['critical', 'severe', 'emergency']):
                severity = 'critical'
            elif any(word in issue_text for word in ['major', 'serious']):
                severity = 'high'
            elif any(word in issue_text for word in ['minor', 'small']):
                severity = 'low'
            analyzed_data['issues'].append({
                'text': issue_text,
                'severity': severity,
                'position': match.start()
            })

    # --- Existing: Extract parts replaced ---
    parts_patterns = [
        r'replaced\s+([^.\n]+)',
        r'changed\s+([^.\n]+)',
        r'installed\s+new\s+([^.\n]+)',
        r'part[s]?\s*:?\s*([^.\n]+)',
    ]
    for pattern in parts_patterns:
        matches = re.finditer(pattern, content_lower)
        for match in matches:
            part_text = match.group(1).strip()
            analyzed_data['parts_replaced'].append({
                'part': part_text,
                'position': match.start()
            })

    # --- Existing: Extract measurements ---
    measurement_patterns = [
        r'(\d+(?:\.\d+)?)\s*(?:psi|bar|pa|kpa|mpa|°c|°f|volts?|v|amps?|a|watts?|w|rpm|hz|khz|mhz)',
        r'temperature\s*:?\s*(\d+(?:\.\d+)?)\s*(?:°c|°f)',
        r'pressure\s*:?\s*(\d+(?:\.\d+)?)\s*(?:psi|bar|pa|kpa|mpa)',
    ]
    for pattern in measurement_patterns:
        matches = re.finditer(pattern, content_lower)
        for match in matches:
            value = match.group(1)
            unit = match.group(0).replace(value, '').strip()
            analyzed_data['measurements'].append({
                'value': float(value),
                'unit': unit,
                'position': match.start()
            })

    # --- Existing: Extract dates ---
    date_patterns = [
        r'\d{1,2}/\d{1,2}/\d{2,4}',
        r'\d{4}-\d{2}-\d{2}',
        r'\d{1,2}-\d{1,2}-\d{2,4}',
    ]
    for pattern in date_patterns:
        matches = re.finditer(pattern, content)
        for match in matches:
            analyzed_data['dates'].append({
                'date': match.group(0),
                'position': match.start()
            })

    # --- Existing: Extract work hours ---
    hours_patterns = [
        r'(\d+(?:\.\d+)?)\s*hours?',
        r'(\d+(?:\.\d+)?)\s*hrs?',
        r'worked\s+(\d+(?:\.\d+)?)\s*hours?',
    ]
    for pattern in hours_patterns:
        match = re.search(pattern, content_lower)
        if match:
            analyzed_data['work_hours'] = float(match.group(1))
            break

    return analyzed_data


@login_required
@require_http_methods(["GET"])
def get_reports_for_equipment(request, equipment_id):
    """Get all reports for a specific equipment."""
    try:
        reports = MaintenanceReport.objects.filter(
            activity__equipment_id=equipment_id
        ).select_related('activity', 'uploaded_by').order_by('-created_at')
        
        data = {
            'reports': [
                {
                    'id': report.id,
                    'title': report.title,
                    'report_type': report.get_report_type_display(),
                    'created_at': report.created_at.isoformat(),
                    'uploaded_by': report.uploaded_by.username if report.uploaded_by else None,
                    'is_processed': report.is_processed,
                    'has_critical_issues': report.has_critical_issues(),
                    'priority_score': report.get_priority_score(),
                }
                for report in reports
            ]
        }
        
        return JsonResponse(data)
        
    except Exception as e:
        logger.error(f"Error getting reports for equipment: {str(e)}")
        return JsonResponse({'error': 'Failed to get reports'}, status=500)

# Add these new views at the end of the file

@login_required
def schedules_view(request):
    """Combined view for both global and category schedules."""
    try:
        # Get category schedules
        category_schedules = EquipmentCategorySchedule.objects.select_related(
            'equipment_category', 'activity_type', 'activity_type__category'
        ).order_by('equipment_category__name', 'activity_type__name')
        
        # Get global schedules
        global_schedules = GlobalSchedule.objects.select_related(
            'activity_type', 'activity_type__category'
        ).order_by('name')
        
        context = {
            'category_schedules': category_schedules,
            'global_schedules': global_schedules,
        }
        return render(request, 'maintenance/schedules.html', context)
        
    except Exception as e:
        logger.error(f"Database error in schedules_view: {str(e)}")
        context = {
            'category_schedules': [],
            'global_schedules': [],
            'database_error': True,
            'error_message': 'Database schema issue detected. Some functionality may be limited.'
        }
        return render(request, 'maintenance/schedules.html', context)

@login_required
def category_schedule_list(request):
    """List equipment category schedules."""
    try:
        schedules = EquipmentCategorySchedule.objects.select_related(
            'equipment_category', 'activity_type', 'activity_type__category'
        ).order_by('equipment_category__name', 'activity_type__name')
        
        context = {
            'schedules': schedules,
        }
        return render(request, 'maintenance/category_schedule_list.html', context)
        
    except Exception as e:
        logger.error(f"Database error in category_schedule_list: {str(e)}")
        context = {
            'schedules': [],
            'database_error': True,
            'error_message': 'Database schema issue detected. Some functionality may be limited.'
        }
        return render(request, 'maintenance/category_schedule_list.html', context)


@login_required
def add_category_schedule(request):
    """Add new equipment category schedule."""
    if request.method == 'POST':
        form = EquipmentCategoryScheduleForm(request.POST)
        if form.is_valid():
            schedule = form.save(commit=False)
            schedule.created_by = request.user
            schedule.save()
            
            messages.success(request, 'Category schedule created successfully!')
            return redirect('maintenance:category_schedule_list')
    else:
        form = EquipmentCategoryScheduleForm()
    
    context = {
        'form': form,
        'title': 'Add Category Schedule'
    }
    return render(request, 'maintenance/category_schedule_form.html', context)


@login_required
def edit_category_schedule(request, schedule_id):
    """Edit equipment category schedule."""
    schedule = get_object_or_404(EquipmentCategorySchedule, id=schedule_id)
    
    if request.method == 'POST':
        form = EquipmentCategoryScheduleForm(request.POST, instance=schedule)
        if form.is_valid():
            schedule = form.save(commit=False)
            schedule.updated_by = request.user
            schedule.save()
            
            messages.success(request, 'Category schedule updated successfully!')
            return redirect('maintenance:category_schedule_list')
    else:
        form = EquipmentCategoryScheduleForm(instance=schedule)
    
    context = {
        'form': form,
        'schedule': schedule,
        'title': 'Edit Category Schedule'
    }
    return render(request, 'maintenance/category_schedule_form.html', context)


@login_required
def category_schedule_detail(request, schedule_id):
    """View equipment category schedule details."""
    schedule = get_object_or_404(EquipmentCategorySchedule, id=schedule_id)
    
    # Get equipment that uses this category
    equipment_list = Equipment.objects.filter(
        category=schedule.equipment_category,
        is_active=True
    ).order_by('name')
    
    # Get recent activities for this schedule
    recent_activities = MaintenanceActivity.objects.filter(
        equipment__category=schedule.equipment_category,
        activity_type=schedule.activity_type
    ).order_by('-scheduled_start')[:10]
    
    context = {
        'schedule': schedule,
        'equipment_list': equipment_list,
        'recent_activities': recent_activities,
    }
    
    return render(request, 'maintenance/category_schedule_detail.html', context)


@login_required
def global_schedule_list(request):
    """List global schedules."""
    try:
        schedules = GlobalSchedule.objects.select_related(
            'activity_type', 'activity_type__category'
        ).order_by('name')
        
        context = {
            'schedules': schedules,
        }
        return render(request, 'maintenance/global_schedule_list.html', context)
        
    except Exception as e:
        logger.error(f"Database error in global_schedule_list: {str(e)}")
        context = {
            'schedules': [],
            'database_error': True,
            'error_message': 'Database schema issue detected. Some functionality may be limited.'
        }
        return render(request, 'maintenance/global_schedule_list.html', context)


@login_required
def add_global_schedule(request):
    """Add new global schedule."""
    if request.method == 'POST':
        form = GlobalScheduleForm(request.POST)
        if form.is_valid():
            schedule = form.save(commit=False)
            schedule.created_by = request.user
            schedule.save()
            
            messages.success(request, 'Global schedule created successfully!')
            return redirect('maintenance:global_schedule_list')
    else:
        form = GlobalScheduleForm()
    
    context = {
        'form': form,
        'title': 'Add Global Schedule'
    }
    return render(request, 'maintenance/global_schedule_form.html', context)


@login_required
def edit_global_schedule(request, schedule_id):
    """Edit global schedule."""
    schedule = get_object_or_404(GlobalSchedule, id=schedule_id)
    
    if request.method == 'POST':
        form = GlobalScheduleForm(request.POST, instance=schedule)
        if form.is_valid():
            schedule = form.save(commit=False)
            schedule.updated_by = request.user
            schedule.save()
            
            messages.success(request, 'Global schedule updated successfully!')
            return redirect('maintenance:global_schedule_list')
    else:
        form = GlobalScheduleForm(instance=schedule)
    
    context = {
        'form': form,
        'schedule': schedule,
        'title': 'Edit Global Schedule'
    }
    return render(request, 'maintenance/global_schedule_form.html', context)


@login_required
def global_schedule_detail(request, schedule_id):
    """View global schedule details."""
    schedule = get_object_or_404(GlobalSchedule, id=schedule_id)
    
    # Get all equipment that could be affected by this global schedule
    equipment_list = Equipment.objects.filter(is_active=True).order_by('name')
    
    # Get recent activities for this schedule
    recent_activities = MaintenanceActivity.objects.filter(
        activity_type=schedule.activity_type
    ).order_by('-scheduled_start')[:10]
    
    context = {
        'schedule': schedule,
        'equipment_list': equipment_list,
        'recent_activities': recent_activities,
    }
    
    return render(request, 'maintenance/global_schedule_detail.html', context)


@login_required
def schedule_override_list(request):
    """List schedule overrides."""
    try:
        overrides = ScheduleOverride.objects.select_related(
            'equipment', 'equipment__category', 'activity_type', 'activity_type__category'
        ).order_by('equipment__name', 'activity_type__name')
        
        context = {
            'overrides': overrides,
        }
        return render(request, 'maintenance/schedule_override_list.html', context)
        
    except Exception as e:
        logger.error(f"Database error in schedule_override_list: {str(e)}")
        context = {
            'overrides': [],
            'database_error': True,
            'error_message': 'Database schema issue detected. Some functionality may be limited.'
        }
        return render(request, 'maintenance/schedule_override_list.html', context)


@login_required
def add_schedule_override(request):
    """Add new schedule override."""
    if request.method == 'POST':
        form = ScheduleOverrideForm(request.POST, request=request)
        if form.is_valid():
            override = form.save(commit=False)
            override.created_by = request.user
            override.save()
            
            messages.success(request, 'Schedule override created successfully!')
            return redirect('maintenance:schedule_override_list')
    else:
        form = ScheduleOverrideForm(request=request)
    
    context = {
        'form': form,
        'title': 'Add Schedule Override'
    }
    return render(request, 'maintenance/schedule_override_form.html', context)


@login_required
def edit_schedule_override(request, override_id):
    """Edit schedule override."""
    override = get_object_or_404(ScheduleOverride, id=override_id)
    
    if request.method == 'POST':
        form = ScheduleOverrideForm(request.POST, instance=override, request=request)
        if form.is_valid():
            override = form.save(commit=False)
            override.updated_by = request.user
            override.save()
            
            messages.success(request, 'Schedule override updated successfully!')
            return redirect('maintenance:schedule_override_list')
    else:
        form = ScheduleOverrideForm(instance=override, request=request)
    
    context = {
        'form': form,
        'override': override,
        'title': 'Edit Schedule Override'
    }
    return render(request, 'maintenance/schedule_override_form.html', context)


@login_required
def schedule_override_detail(request, override_id):
    """View schedule override details."""
    override = get_object_or_404(ScheduleOverride, id=override_id)
    
    # Get the effective schedule for comparison
    effective_schedule = override.equipment.get_effective_schedule(override.activity_type)
    
    # Get recent activities for this override
    recent_activities = MaintenanceActivity.objects.filter(
        equipment=override.equipment,
        activity_type=override.activity_type
    ).order_by('-scheduled_start')[:10]
    
    context = {
        'override': override,
        'effective_schedule': effective_schedule,
        'recent_activities': recent_activities,
    }
    
    return render(request, 'maintenance/schedule_override_detail.html', context)


@login_required
def apply_schedules_to_equipment(request, equipment_id):
    """Apply category and global schedules to specific equipment."""
    equipment = get_object_or_404(Equipment, id=equipment_id)
    
    if request.method == 'POST':
        try:
            equipment.apply_category_schedules(request.user)
            messages.success(request, f'Schedules applied to {equipment.name} successfully!')
        except Exception as e:
            logger.error(f"Error applying schedules to equipment {equipment.id}: {str(e)}")
            messages.error(request, f'Error applying schedules: {str(e)}')
        
        return redirect('equipment:equipment_detail', equipment_id=equipment.id)
    
    # Show preview of what would be applied
    category_schedules = EquipmentCategorySchedule.objects.filter(
        equipment_category=equipment.category,
        is_active=True
    ) if equipment.category else []
    
    global_schedules = GlobalSchedule.objects.filter(is_active=True)
    
    existing_overrides = ScheduleOverride.objects.filter(equipment=equipment)
    
    context = {
        'equipment': equipment,
        'category_schedules': category_schedules,
        'global_schedules': global_schedules,
        'existing_overrides': existing_overrides,
    }
    
    return render(request, 'maintenance/apply_schedules_preview.html', context)

# Add this debug view at the end of the file

@login_required
def debug_equipment_filtering(request):
    """Debug view to help troubleshoot equipment filtering issues."""
    from core.models import Location
    from equipment.models import Equipment
    from django.db.models import Q
    
    # Get current site selection
    selected_site_id = request.GET.get('site_id')
    if selected_site_id is None:
        selected_site_id = request.session.get('selected_site_id')
    
    # Get all equipment
    all_equipment = Equipment.objects.filter(is_active=True).select_related('category', 'location')
    
    # Get site info
    selected_site = None
    is_all_sites = False
    
    if selected_site_id:
        if selected_site_id == 'all':
            # Handle "All Sites" selection
            is_all_sites = True
        else:
            try:
                selected_site = Location.objects.get(id=selected_site_id, is_site=True)
            except (Location.DoesNotExist, ValueError):
                pass
    else:
        # No site selected, treat as "All Sites"
        is_all_sites = True
    
    # Filter equipment by site
    filtered_equipment = all_equipment
    if selected_site:
        filtered_equipment = all_equipment.filter(
            Q(location__parent_location=selected_site) | Q(location=selected_site)
        )
    
    # Get all sites
    all_sites = Location.objects.filter(is_site=True)
    
    context = {
        'all_equipment': all_equipment,
        'filtered_equipment': filtered_equipment,
        'selected_site': selected_site,
        'all_sites': all_sites,
        'selected_site_id': selected_site_id,
        'total_equipment': all_equipment.count(),
        'filtered_count': filtered_equipment.count(),
    }
    
    return render(request, 'maintenance/debug_equipment_filtering.html', context)


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
        
        # Handle equipment - ensure it's not empty string
        if 'equipment' in processed_data and processed_data['equipment'] == '':
            processed_data['equipment'] = None
        
        # Create form with the processed data
        form = MaintenanceActivityForm(processed_data, request=request)
        
        if form.is_valid():
            # Save the activity
            activity = form.save(commit=False)
            activity.created_by = request.user
            activity.save()
            
            # Return success response
            return JsonResponse({
                'success': True,
                'message': f'Maintenance activity "{activity.title}" created successfully!',
                'activity_id': activity.id
            })
        else:
            # Return validation errors
            logger.error(f"Form validation failed: {form.errors}")
            return JsonResponse({
                'success': False,
                'error': 'Validation failed',
                'errors': form.errors
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
def add_timeline_entry(request, activity_id):
    """Add a new timeline entry to a maintenance activity."""
    activity = get_object_or_404(MaintenanceActivity, id=activity_id)
    
    if request.method == 'POST':
        entry_type = request.POST.get('entry_type')
        title = request.POST.get('title')
        description = request.POST.get('description')
        
        if entry_type and title and description:
            try:
                # Create the timeline entry
                timeline_entry = MaintenanceTimelineEntry.objects.create(
                    activity=activity,
                    entry_type=entry_type,
                    title=title,
                    description=description,
                    created_by=request.user
                )
                
                messages.success(request, 'Timeline entry added successfully!')
                
                # Redirect back to the activity detail page
                return redirect('maintenance:activity_detail', activity_id=activity_id)
                
            except Exception as e:
                logger.error(f"Error creating timeline entry: {str(e)}")
                messages.error(request, f'Error creating timeline entry: {str(e)}')
        else:
            messages.error(request, 'Please fill in all required fields.')
    
    # If GET request or validation failed, redirect back to activity detail
    return redirect('maintenance:activity_detail', activity_id=activity_id)


@login_required
@user_passes_test(lambda u: u.is_staff)
def edit_timeline_entry(request, activity_id, entry_id):
    """Edit a timeline entry (admin only)."""
    activity = get_object_or_404(MaintenanceActivity, id=activity_id)
    timeline_entry = get_object_or_404(MaintenanceTimelineEntry, id=entry_id, activity=activity)
    
    if request.method == 'POST':
        entry_type = request.POST.get('entry_type')
        title = request.POST.get('title')
        description = request.POST.get('description')
        
        if entry_type and title and description:
            try:
                timeline_entry.entry_type = entry_type
                timeline_entry.title = title
                timeline_entry.description = description
                # updated_by is handled by TimeStampedModel if it exists
                if hasattr(timeline_entry, 'updated_by'):
                    timeline_entry.updated_by = request.user
                timeline_entry.save()
                
                messages.success(request, 'Timeline entry updated successfully!')
                return redirect('maintenance:activity_detail', activity_id=activity_id)
                
            except Exception as e:
                logger.error(f"Error updating timeline entry: {str(e)}")
                messages.error(request, f'Error updating timeline entry: {str(e)}')
        else:
            messages.error(request, 'Please fill in all required fields.')
    
    # If GET request or validation failed, redirect back to activity detail
    return redirect('maintenance:activity_detail', activity_id=activity_id)


@login_required
@user_passes_test(lambda u: u.is_staff)
@require_http_methods(["POST"])
def delete_timeline_entry(request, activity_id, entry_id):
    """Delete a timeline entry (admin only)."""
    activity = get_object_or_404(MaintenanceActivity, id=activity_id)
    timeline_entry = get_object_or_404(MaintenanceTimelineEntry, id=entry_id, activity=activity)
    
    try:
        timeline_entry.delete()
        messages.success(request, 'Timeline entry deleted successfully!')
    except Exception as e:
        logger.error(f"Error deleting timeline entry: {str(e)}")
        messages.error(request, f'Error deleting timeline entry: {str(e)}')
    
    return redirect('maintenance:activity_detail', activity_id=activity_id)

@receiver(post_save, sender=MaintenanceReport)
def maintenance_report_post_save(sender, instance, created, **kwargs):
    """Create timeline entry when maintenance report is uploaded."""
    if created:
        MaintenanceTimelineEntry.objects.create(
            activity=instance.maintenance_activity,
            entry_type='report_uploaded',
            title=f'{instance.get_report_type_display()} Uploaded',
            description=f'Report "{instance.title}" was uploaded by {instance.created_by.get_full_name() or instance.created_by.username}',
            created_by=instance.created_by
        )


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
def delete_report(request, report_id):
    """Delete a maintenance report (admin/staff only)."""
    # Check if user is staff or superuser
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, 'You do not have permission to delete reports.')
        return redirect('maintenance:maintenance_list')
    
    report = get_object_or_404(MaintenanceReport, id=report_id)
    activity = report.maintenance_activity
    
    if request.method == 'POST':
        report_title = report.title
        report.delete()
        messages.success(request, f'Report "{report_title}" deleted successfully!')
        return redirect('maintenance:activity_detail', activity_id=activity.id)
    
    context = {
        'report': report,
        'activity': activity,
    }
    return render(request, 'maintenance/delete_report.html', context)


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
            
            if new_status == 'in_progress' or new_status == 'completed':
                # Use custom start time if provided, otherwise use current time or existing value
                if actual_start_str:
                    try:
                        from django.utils.dateparse import parse_datetime
                        activity.actual_start = parse_datetime(actual_start_str)
                        if not activity.actual_start:
                            # Try parsing as local datetime
                            from datetime import datetime
                            activity.actual_start = datetime.strptime(actual_start_str, '%Y-%m-%dT%H:%M')
                            activity.actual_start = timezone.make_aware(activity.actual_start)
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
                        from django.utils.dateparse import parse_datetime
                        activity.actual_end = parse_datetime(actual_end_str)
                        if not activity.actual_end:
                            # Try parsing as local datetime
                            from datetime import datetime
                            activity.actual_end = datetime.strptime(actual_end_str, '%Y-%m-%dT%H:%M')
                            activity.actual_end = timezone.make_aware(activity.actual_end)
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