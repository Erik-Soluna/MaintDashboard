"""reports views (split from the original monolithic views.py)."""
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


__all__ = ["maintenance_reports", "report_list", "report_detail", "upload_report", "analyze_report", "get_reports_for_equipment", "maintenance_report_post_save", "delete_report"]
