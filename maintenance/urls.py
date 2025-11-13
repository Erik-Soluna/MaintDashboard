"""
URL configuration for maintenance app.
"""

from django.urls import path
from . import views

app_name = 'maintenance'

urlpatterns = [
    # Main maintenance dashboard
    path('', views.maintenance_list, name='maintenance_list'),
    
    # Activities
    path('activities/', views.activity_list, name='activity_list'),
    path('activities/add/', views.add_activity, name='add_activity'),
    path('activities/bulk-add/', views.bulk_add_activity, name='bulk_add_activity'),
    path('activities/<int:activity_id>/', views.activity_detail, name='activity_detail'),
    path('activities/<int:activity_id>/edit/', views.edit_activity, name='edit_activity'),
    path('activities/<int:activity_id>/complete/', views.complete_activity, name='complete_activity'),
    path('activities/<int:activity_id>/delete/', views.delete_activity, name='delete_activity'),
    path('activities/<int:activity_id>/timeline/add/', views.add_timeline_entry, name='add_timeline_entry'),
    path('activities/<int:activity_id>/timeline/<int:entry_id>/edit/', views.edit_timeline_entry, name='edit_timeline_entry'),
    path('activities/<int:activity_id>/timeline/<int:entry_id>/delete/', views.delete_timeline_entry, name='delete_timeline_entry'),
    path('activities/<int:activity_id>/upload-document/', views.upload_activity_document, name='upload_activity_document'),
    path('activities/<int:activity_id>/change-status/', views.change_activity_status, name='change_activity_status'),
    path('activities/<int:activity_id>/attach-related/', views.attach_related_activity, name='attach_related_activity'),
    
    # Schedules
    path('schedules/', views.schedule_list, name='schedule_list'),  # Fixed name to match template usage
    path('schedules/add/', views.add_schedule, name='add_schedule'),
    path('schedules/<int:schedule_id>/', views.schedule_detail, name='schedule_detail'),
    path('schedules/<int:schedule_id>/edit/', views.edit_schedule, name='edit_schedule'),
    path('schedules/<int:schedule_id>/delete/', views.delete_schedule, name='delete_schedule'),
    path('schedules/generate/', views.generate_scheduled_activities, name='generate_scheduled_activities'),
    
    # Legacy activity types management (for backwards compatibility)
    path('activity-types/', views.activity_type_list, name='activity_type_list'),
    path('activity-types/add/', views.add_activity_type, name='add_activity_type'),
    path('activity-types/<int:activity_type_id>/edit/', views.edit_activity_type, name='edit_activity_type'),
    path('activity-types/export/csv/', views.export_activity_types_csv, name='export_activity_types_csv'),
    path('activity-types/import/csv/', views.import_activity_types_csv, name='import_activity_types_csv'),
    
    # Enhanced activity type management
    path('enhanced-activity-types/', views.enhanced_activity_type_list, name='enhanced_activity_type_list'),
    path('enhanced-activity-types/add/', views.enhanced_add_activity_type, name='enhanced_add_activity_type'),
    path('enhanced-activity-types/<int:activity_type_id>/edit/', views.enhanced_edit_activity_type, name='enhanced_edit_activity_type'),
    
    # Activity type categories
    path('activity-type-categories/', views.activity_type_categories, name='activity_type_categories'),
    path('activity-type-categories/add/', views.add_activity_type_category, name='add_activity_type_category'),
    path('activity-type-categories/<int:category_id>/edit/', views.edit_activity_type_category, name='edit_activity_type_category'),
    path('activity-type-categories/<int:category_id>/activity-types/', views.category_activity_types, name='category_activity_types'),
    
    # Activity type templates
    path('activity-type-templates/', views.activity_type_templates, name='activity_type_templates'),
    path('activity-type-templates/add/', views.add_activity_type_template, name='add_activity_type_template'),
    path('activity-type-templates/<int:template_id>/edit/', views.edit_activity_type_template, name='edit_activity_type_template'),
    
    # AJAX endpoints
    path('ajax/get-activity-type-templates/', views.get_activity_type_templates, name='get_activity_type_templates'),
    path('ajax/get-template-details/<int:template_id>/', views.get_template_details, name='get_template_details'),
    path('ajax/get-activity-type-suggestions/', views.get_activity_type_suggestions, name='get_activity_type_suggestions'),
    path('ajax/create-activity-type-from-template/', views.create_activity_type_from_template, name='create_activity_type_from_template'),
    
    # Import/Export (existing views)
    path('activities/export/csv/', views.export_maintenance_csv, name='export_maintenance_csv'),
    path('activities/import/csv/', views.import_maintenance_csv, name='import_maintenance_csv'),
    path('schedules/export/csv/', views.export_maintenance_schedules_csv, name='export_maintenance_schedules_csv'),
    
    # Reports (existing views)
    path('reports/', views.maintenance_reports, name='maintenance_reports'),
    path('overdue/', views.overdue_maintenance, name='overdue_maintenance'),
    
    # Legacy aliases for backwards compatibility
    path('generate-activities/', views.generate_maintenance_activities, name='generate_maintenance_activities'),
    path('api/activities/', views.get_activities_data, name='get_activities_data'),
    path('api/generate-activities/', views.generate_maintenance_activities, name='generate_activities'),
    path('generate-scheduled-activities/', views.generate_scheduled_activities, name='generate_scheduled_activities'),
    path('api/fetch-activities/', views.fetch_activities, name='fetch_activities'),
    path('api/activity/<int:activity_id>/', views.get_activity_details, name='get_activity_details'),
    path('api/activities/create/', views.create_activity_api, name='create_activity_api'),
    
    # Maintenance Reports
    path('reports/list/', views.report_list, name='report_list'),
    path('reports/<int:report_id>/', views.report_detail, name='report_detail'),
    path('reports/<int:report_id>/delete/', views.delete_report, name='delete_report'),
    path('reports/upload/', views.upload_report, name='upload_report'),
    path('reports/<int:report_id>/analyze/', views.analyze_report, name='analyze_report'),
    path('api/reports/equipment/<int:equipment_id>/', views.get_reports_for_equipment, name='get_reports_for_equipment'),

    # Combined Schedules View
    # path('schedules/', views.schedules_view, name='schedules'),  # Removed duplicate
    
    # Category Schedules
    path('category-schedules/', views.category_schedule_list, name='category_schedule_list'),
    path('category-schedules/add/', views.add_category_schedule, name='add_category_schedule'),
    path('category-schedules/<int:schedule_id>/', views.category_schedule_detail, name='category_schedule_detail'),
    path('category-schedules/<int:schedule_id>/edit/', views.edit_category_schedule, name='edit_category_schedule'),
    
    # Global Schedules
    path('global-schedules/', views.global_schedule_list, name='global_schedule_list'),
    path('global-schedules/add/', views.add_global_schedule, name='add_global_schedule'),
    path('global-schedules/<int:schedule_id>/', views.global_schedule_detail, name='global_schedule_detail'),
    path('global-schedules/<int:schedule_id>/edit/', views.edit_global_schedule, name='edit_global_schedule'),
    
    # Schedule Overrides
    path('schedule-overrides/', views.schedule_override_list, name='schedule_override_list'),
    path('schedule-overrides/add/', views.add_schedule_override, name='add_schedule_override'),
    path('schedule-overrides/<int:override_id>/', views.schedule_override_detail, name='schedule_override_detail'),
    path('schedule-overrides/<int:override_id>/edit/', views.edit_schedule_override, name='edit_schedule_override'),
    
    # Apply Schedules
    path('apply-schedules/<int:equipment_id>/', views.apply_schedules_to_equipment, name='apply_schedules_to_equipment'),
    
    # Debug
    path('debug/equipment-filtering/', views.debug_equipment_filtering, name='debug_equipment_filtering'),
]