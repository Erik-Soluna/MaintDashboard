"""
Views for maintenance management.
Fixed associations and improved functionality from original web2py controllers.
"""

import logging
import csv
import io
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta, datetime

from .models import (
    MaintenanceActivity, MaintenanceActivityType, 
    MaintenanceSchedule, MaintenanceChecklist
)
from equipment.models import Equipment
from .forms import (
    MaintenanceActivityForm, MaintenanceScheduleForm, 
    MaintenanceActivityTypeForm
)

logger = logging.getLogger(__name__)


@login_required
def maintenance_list(request):
    """Main maintenance dashboard."""
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


@login_required
def activity_list(request):
    """List all maintenance activities with filtering."""
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


@login_required
def activity_detail(request, activity_id):
    """Display detailed information for maintenance activity."""
    activity = get_object_or_404(
        MaintenanceActivity.objects.select_related(
            'equipment', 'activity_type', 'assigned_to'
        ),
        id=activity_id
    )
    
    checklist_items = activity.checklist_items.all().order_by('order')
    
    context = {
        'activity': activity,
        'checklist_items': checklist_items,
    }
    
    return render(request, 'maintenance/activity_detail.html', context)


@login_required
def add_activity(request):
    """Add new maintenance activity."""
    # Debug: Check if there are any equipment records
    from equipment.models import Equipment
    from core.models import Location
    
    total_equipment_count = Equipment.objects.filter(is_active=True).count()
    logger.info(f"Total active equipment count: {total_equipment_count}")
    
    # Check site filtering
    selected_site_id = request.GET.get('site_id')
    if selected_site_id is None:
        selected_site_id = request.session.get('selected_site_id')
    
    selected_site = None
    if selected_site_id:
        try:
            selected_site = Location.objects.get(id=selected_site_id, is_site=True)
            logger.info(f"Selected site: {selected_site.name}")
        except Location.DoesNotExist:
            logger.warning(f"Invalid site ID: {selected_site_id}")
    
    if request.method == 'POST':
        form = MaintenanceActivityForm(request.POST, request=request)
        if form.is_valid():
            activity = form.save(commit=False)
            activity.created_by = request.user
            activity.save()
            
            messages.success(request, f'Maintenance activity "{activity.title}" created successfully!')
            return redirect('maintenance:activity_detail', activity_id=activity.id)
    else:
        form = MaintenanceActivityForm(request=request)
    
    # Debug: Check equipment queryset in form
    equipment_queryset = form.fields['equipment'].queryset
    filtered_equipment_count = equipment_queryset.count()
    logger.info(f"Filtered equipment queryset count: {filtered_equipment_count}")
    
    context = {
        'form': form,
        'equipment_count': filtered_equipment_count,
        'total_equipment_count': total_equipment_count,
        'selected_site': selected_site,
        'equipment_list': equipment_queryset[:10],  # First 10 filtered equipment for debugging
    }
    return render(request, 'maintenance/add_activity.html', context)


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
    schedules = MaintenanceSchedule.objects.select_related(
        'equipment', 'activity_type'
    ).filter(is_active=True)
    
    context = {'schedules': schedules}
    return render(request, 'maintenance/schedule_list.html', context)


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
    activity_types = MaintenanceActivityType.objects.filter(is_active=True)
    
    context = {'activity_types': activity_types}
    return render(request, 'maintenance/activity_type_list.html', context)


@login_required
def add_activity_type(request):
    """Add new maintenance activity type."""
    if request.method == 'POST':
        form = MaintenanceActivityTypeForm(request.POST)
        if form.is_valid():
            activity_type = form.save(commit=False)
            activity_type.created_by = request.user
            activity_type.save()
            
            messages.success(request, f'Activity type "{activity_type.name}" created successfully!')
            return redirect('maintenance:activity_type_list')
    else:
        form = MaintenanceActivityTypeForm()
    
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
            
            messages.success(request, f'Activity type "{activity_type.name}" updated successfully!')
            return redirect('maintenance:activity_type_list')
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
                    
                activity_type, created = MaintenanceActivityType.objects.get_or_create(
                    name=name,
                    defaults={
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
    
    if site_id:
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
        
        # Import data
        from .models import MaintenanceActivity, MaintenanceActivityType
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
                
                # Find or create activity type
                activity_type, created = MaintenanceActivityType.objects.get_or_create(
                    name=activity_type_name,
                    defaults={
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
                
                # Parse dates
                scheduled_start = None
                scheduled_end = None
                actual_start = None
                actual_end = None
                next_due_date = None
                
                try:
                    if len(row) > 5 and row[5].strip():
                        scheduled_start = datetime.fromisoformat(row[5].strip())
                        if scheduled_start.tzinfo is None:
                            scheduled_start = django_timezone.make_aware(scheduled_start)
                except ValueError:
                    pass
                
                try:
                    if len(row) > 6 and row[6].strip():
                        scheduled_end = datetime.fromisoformat(row[6].strip())
                        if scheduled_end.tzinfo is None:
                            scheduled_end = django_timezone.make_aware(scheduled_end)
                except ValueError:
                    pass
                
                try:
                    if len(row) > 7 and row[7].strip():
                        actual_start = datetime.fromisoformat(row[7].strip())
                        if actual_start.tzinfo is None:
                            actual_start = django_timezone.make_aware(actual_start)
                except ValueError:
                    pass
                
                try:
                    if len(row) > 8 and row[8].strip():
                        actual_end = datetime.fromisoformat(row[8].strip())
                        if actual_end.tzinfo is None:
                            actual_end = django_timezone.make_aware(actual_end)
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
                
                # Default scheduled dates if not provided
                if not scheduled_start:
                    scheduled_start = django_timezone.now()
                if not scheduled_end:
                    scheduled_end = scheduled_start + django_timezone.timedelta(hours=activity_type.estimated_duration_hours)
                
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
                
                MaintenanceActivity.objects.create(**activity_data)
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
    if site_id:
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
    """Maintenance reports and analytics."""
    # Activity status distribution
    status_stats = MaintenanceActivity.objects.values('status').annotate(
        count=Count('id')
    ).order_by('status')
    
    # Equipment with most maintenance
    equipment_stats = MaintenanceActivity.objects.values(
        'equipment__name'
    ).annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # Monthly completion stats
    monthly_stats = MaintenanceActivity.objects.filter(
        status='completed',
        actual_end__gte=timezone.now() - timedelta(days=365)
    ).extra(
        {'month': 'EXTRACT(month FROM actual_end)'}
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')
    
    context = {
        'status_stats': status_stats,
        'equipment_stats': equipment_stats,
        'monthly_stats': monthly_stats,
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
    """Delete maintenance activity."""
    activity = get_object_or_404(MaintenanceActivity, id=activity_id)
    
    if request.method == 'POST':
        activity_title = activity.title
        activity.delete()
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
        return redirect('maintenance:schedule_list')
    
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