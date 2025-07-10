"""
URL configuration for maintenance app.
"""

from django.urls import path
from . import views

app_name = 'maintenance'

urlpatterns = [
    # Maintenance activities
    path('', views.maintenance_list, name='maintenance_list'),
    path('activities/', views.activity_list, name='activity_list'),
    path('activities/add/', views.add_activity, name='add_activity'),
    path('activities/<int:activity_id>/', views.activity_detail, name='activity_detail'),
    path('activities/<int:activity_id>/edit/', views.edit_activity, name='edit_activity'),
    path('activities/<int:activity_id>/complete/', views.complete_activity, name='complete_activity'),
    
    # Maintenance schedules
    path('schedules/', views.schedule_list, name='schedule_list'),
    path('schedules/add/', views.add_schedule, name='add_schedule'),
    path('schedules/<int:schedule_id>/', views.schedule_detail, name='schedule_detail'),
    path('schedules/<int:schedule_id>/edit/', views.edit_schedule, name='edit_schedule'),
    path('schedules/generate/', views.generate_scheduled_activities, name='generate_scheduled_activities'),
    
    # Activity types
    path('types/', views.activity_type_list, name='activity_type_list'),
    path('types/add/', views.add_activity_type, name='add_activity_type'),
    path('types/<int:activity_type_id>/edit/', views.edit_activity_type, name='edit_activity_type'),
    path('types/import/csv/', views.import_activity_types_csv, name='import_activity_types_csv'),
    path('types/export/csv/', views.export_activity_types_csv, name='export_activity_types_csv'),
    
    # Reports
    path('reports/', views.maintenance_reports, name='maintenance_reports'),
    path('reports/overdue/', views.overdue_maintenance, name='overdue_maintenance'),
]