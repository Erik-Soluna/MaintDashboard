"""
URL configuration for core app.
"""

from django.urls import path
from . import views
from django.http import JsonResponse

app_name = 'core'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),  # Root path for dashboard
    path('dashboard/', views.dashboard, name='dashboard_alt'),  # Alternative dashboard path
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
    path('version/set/', views.set_version_api, name='set_version_api'),
    path('version/extract/', views.extract_version_from_url_api, name='extract_version_from_url_api'),
    path('version/form/', views.version_form_view, name='version_form'),
    path('map/', views.map_view, name='map_view'),
    path('locations/settings/', views.locations_settings, name='locations_settings'),
    path('equipment-items/settings/', views.equipment_items_settings, name='equipment_items_settings'),
    path('equipment-categories/settings/', views.equipment_categories_settings, name='equipment_categories_settings'),
    
    # Debug and utility URLs
    path('health/comprehensive/', views.comprehensive_health_check, name='comprehensive_health_check'),
    path('health/run/', views.run_health_check, name='run_health_check'),
    path('health/api/', views.comprehensive_health_check, name='health_check_api'),  # Alias for template compatibility
    path('health/', views.run_health_check, name='health_check'),  # Alias for template compatibility
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
    path('locations/<int:location_id>/delete/', views.delete_location, name='delete_location'),
    path('locations/<int:location_id>/edit/', views.edit_location, name='edit_location'),
    path('locations/add/', views.add_location, name='add_location'),
    
    # Customer management URLs
    path('customers/settings/', views.customers_settings, name='customers_settings'),
    path('customers/add/', views.add_customer, name='add_customer'),
    path('customers/<int:customer_id>/edit/', views.edit_customer, name='edit_customer'),
    path('customers/<int:customer_id>/delete/', views.delete_customer, name='delete_customer'),
    
    # API endpoints
    path('api/customers/add/', views.add_customer_ajax, name='add_customer_ajax'),
    path('api/equipment-items/', views.equipment_items_api, name='equipment_items_api'),
    path('api/users/', views.users_api, name='users_api'),
    path('api/roles/', views.roles_api, name='roles_api'),
    path('api/roles/<int:role_id>/', views.role_detail_api, name='role_detail_api'),
    path('api/endpoint-metrics/', views.endpoint_metrics_api, name='endpoint_metrics_api'),
    path('api/playwright-debug/', views.playwright_debug_api, name='playwright_debug_api'),
    path('api/playwright/natural-language/', views.run_natural_language_test_api, name='run_natural_language_test_api'),
    path('api/playwright/rbac-suite/', views.run_rbac_test_suite_api, name='run_rbac_test_suite_api'),
    path('api/playwright/results/', views.get_test_results_api, name='get_test_results_api'),
    path('api/playwright/scenarios/', views.run_test_scenario_api, name='run_test_scenario_api'),
    path('api/playwright/screenshots/', views.get_test_screenshots_api, name='get_test_screenshots_api'),
    path('api/test-health/', views.test_health, name='test_health'),
    path('api/toggle-monitoring/', views.toggle_monitoring, name='toggle_monitoring'),
    
    # Other utility URLs
    path('bulk-locations/', views.bulk_locations_view, name='bulk_locations'),
    path('api-explorer/', views.api_explorer, name='api_explorer'),
    path('locations/api/', views.locations_api, name='locations_api'),  # API endpoint for locations
    path('api/locations/<int:location_id>/', views.location_detail_api, name='location_detail_api'),  # API endpoint for individual location operations
]