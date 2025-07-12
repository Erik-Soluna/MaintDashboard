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
    path('activities/<int:activity_id>/', views.activity_detail, name='activity_detail'),
    path('activities/<int:activity_id>/edit/', views.edit_activity, name='edit_activity'),
    path('activities/<int:activity_id>/complete/', views.complete_activity, name='complete_activity'),
    path('activities/<int:activity_id>/delete/', views.delete_activity, name='delete_activity'),
    
    # Schedules
    path('schedules/', views.schedule_list, name='schedule_list'),
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
]