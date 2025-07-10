"""
URL configuration for maintenance app.
"""

from django.urls import path
from . import views

app_name = 'maintenance'

urlpatterns = [
    # Maintenance activity management
    path('', views.maintenance_list, name='maintenance_list'),
    path('add/', views.add_activity, name='add_activity'),
    path('<int:activity_id>/', views.activity_detail, name='activity_detail'),
    path('<int:activity_id>/edit/', views.edit_activity, name='edit_activity'),
    path('<int:activity_id>/complete/', views.complete_activity, name='complete_activity'),
    path('<int:activity_id>/delete/', views.delete_activity, name='delete_activity'),
    
    # Maintenance schedules
    path('schedules/', views.schedule_list, name='schedule_list'),
    path('schedules/add/', views.add_schedule, name='add_schedule'),
    path('schedules/<int:schedule_id>/edit/', views.edit_schedule, name='edit_schedule'),
    path('schedules/<int:schedule_id>/delete/', views.delete_schedule, name='delete_schedule'),
    
    # Activity types management
    path('activity-types/', views.activity_type_list, name='activity_type_list'),
    path('activity-types/add/', views.add_activity_type, name='add_activity_type'),
    path('activity-types/<int:type_id>/edit/', views.edit_activity_type, name='edit_activity_type'),
    
    # Reports and analytics
    path('reports/', views.maintenance_reports, name='maintenance_reports'),
    
    # AJAX endpoints
    path('api/activities/', views.get_activities_data, name='get_activities_data'),
    path('api/generate-activities/', views.generate_maintenance_activities, name='generate_activities'),
    
    # CSV Import/Export
    path('activities/export/csv/', views.export_maintenance_csv, name='export_maintenance_csv'),
    path('activities/import/csv/', views.import_maintenance_csv, name='import_maintenance_csv'),
    path('schedules/export/csv/', views.export_maintenance_schedules_csv, name='export_maintenance_schedules_csv'),
]