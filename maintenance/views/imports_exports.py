"""imports_exports views (split from the original monolithic views.py)."""
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
            activity.get_scheduled_start_in_timezone().strftime('%Y-%m-%d %H:%M:%S') if activity.scheduled_start else '',
            activity.get_scheduled_end_in_timezone().strftime('%Y-%m-%d %H:%M:%S') if activity.scheduled_end else '',
            activity.get_actual_start_in_timezone().strftime('%Y-%m-%d %H:%M:%S') if activity.actual_start else '',
            activity.get_actual_end_in_timezone().strftime('%Y-%m-%d %H:%M:%S') if activity.actual_end else '',
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


__all__ = ["import_activity_types_csv", "export_activity_types_csv", "export_maintenance_csv", "import_maintenance_csv", "export_maintenance_activities_csv", "export_maintenance_schedules_csv"]
