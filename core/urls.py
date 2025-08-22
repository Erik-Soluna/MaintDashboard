"""
URL configuration for core app.
"""

from django.urls import path
from . import views
from version import get_git_version
from django.http import JsonResponse

app_name = 'core'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile, name='profile'),
    path('settings/', views.settings_view, name='settings'),
    path('user-management/', views.user_management, name='user_management'),
    path('roles-permissions/', views.roles_permissions_management, name='roles_permissions_management'),
    path('system-health/', views.system_health, name='system_health'),
    path('debug/', views.debug, name='debug'),
    path('webhook-settings/', views.webhook_settings, name='webhook_settings'),
    path('docker-logs/', views.docker_logs_view, name='docker_logs'),
    path('version/', views.version_view, name='version'),
    path('version/html/', views.version_html_view, name='version_html'),
    path('map/', views.map_view, name='map_view'),
    path('locations/settings/', views.locations_settings, name='locations_settings'),
    path('equipment-items/settings/', views.equipment_items_settings, name='equipment_items_settings'),
    
    # Debug and utility URLs
    path('health/comprehensive/', views.comprehensive_health_check, name='comprehensive_health_check'),
    path('health/run/', views.run_health_check, name='run_health_check'),
    path('health/api/', views.comprehensive_health_check, name='health_check_api'),  # Alias for template compatibility
    path('health/clear-logs/', views.clear_health_logs, name='clear_health_logs'),
    path('debug/playwright/', views.playwright_debug_api, name='playwright_debug_api'),
    path('debug/clear-database/', views.clear_database, name='clear_database'),
    path('debug/populate-demo/', views.populate_demo_data, name='populate_demo_data'),
    path('debug/generate-pods/', views.generate_pods, name='generate_pods'),
    path('docker/containers/', views.get_docker_containers_api, name='get_docker_containers'),
    path('docker/logs/', views.get_docker_logs_api, name='get_docker_logs'),
    path('docker/aggregated-logs/', views.get_aggregated_logs_api, name='get_aggregated_logs'),
    path('docker/system-logs/', views.get_system_logs_api, name='get_system_logs'),
    path('locations/bulk-edit/', views.bulk_edit_locations, name='bulk_edit_locations'),
    
    # Customer management URLs
    path('customers/settings/', views.customers_settings, name='customers_settings'),
    path('customers/add/', views.add_customer, name='add_customer'),
    path('customers/<int:customer_id>/edit/', views.edit_customer, name='edit_customer'),
    path('customers/<int:customer_id>/delete/', views.delete_customer, name='delete_customer'),
    
    # Other utility URLs
    path('bulk-locations/', views.bulk_locations_view, name='bulk_locations'),
    path('api-explorer/', views.api_explorer, name='api_explorer'),
]