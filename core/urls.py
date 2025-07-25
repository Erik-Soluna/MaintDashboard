"""
URL configuration for core app.
"""

from django.urls import path
from . import views
from .views import health_check, simple_health_check, api_explorer, clear_health_logs, playwright_slideshow

app_name = 'core'

urlpatterns = [
    # Dashboard and main views
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile, name='profile'),
    path('map/', views.map_view, name='map_view'),
    
    # Monitoring and health checks
    path('monitoring/', views.monitoring_dashboard, name='monitoring_dashboard'),
    path('health-check/', views.health_check_api, name='health_check_api'),
    path('health-check/run/', views.run_health_check, name='run_health_check'),
    path('health-check/comprehensive/', views.comprehensive_health_check, name='comprehensive_health_check'),
    path('api/endpoint-metrics/', views.endpoint_metrics_api, name='endpoint_metrics_api'),
    path('api/toggle-monitoring/', views.toggle_monitoring, name='toggle_monitoring'),
    
    # Settings
    path('settings/', views.settings, name='settings'),
    path('settings/locations/', views.locations_settings, name='locations_settings'),
    path('settings/equipment-items/', views.equipment_items_settings, name='equipment_items_settings'),
    path('settings/equipment-categories/', views.equipment_categories_settings, name='equipment_categories_settings'),
    path('settings/customers/', views.customers_settings, name='customers_settings'),
    path('settings/users/', views.user_management, name='user_management'),
    path('settings/roles-permissions/', views.roles_permissions_management, name='roles_permissions_management'),
    path('settings/health/', views.system_health, name='system_health'),
    
    # Debug page
    path('debug/', views.debug, name='debug'),
    
    # Location management
    path('locations/add/', views.add_location, name='add_location'),
    path('locations/<int:location_id>/edit/', views.edit_location, name='edit_location'),
    path('locations/<int:location_id>/delete/', views.delete_location, name='delete_location'),
    
    # Equipment category management
    path('categories/add/', views.add_equipment_category, name='add_equipment_category'),
    path('categories/<int:category_id>/edit/', views.edit_equipment_category, name='edit_equipment_category'),
    path('categories/<int:category_id>/delete/', views.delete_equipment_category, name='delete_equipment_category'),
    
    # Customer management
    path('customers/add/', views.add_customer, name='add_customer'),
    path('customers/<int:customer_id>/edit/', views.edit_customer, name='edit_customer'),
    path('customers/<int:customer_id>/delete/', views.delete_customer, name='delete_customer'),
    
    # API endpoints
    path('api/locations/', views.locations_api, name='locations_api'),
    path('api/locations/<int:location_id>/', views.location_detail_api, name='location_detail_api'),
    path('api/roles/', views.roles_api, name='roles_api'),
    path('api/roles/<int:role_id>/', views.role_detail_api, name='role_detail_api'),
    path('api/equipment-items/', views.equipment_items_api, name='equipment_items_api'),
    path('api/users/', views.users_api, name='users_api'),
    
    # CSV Import/Export
    path('sites/export/csv/', views.export_sites_csv, name='export_sites_csv'),
    path('sites/import/csv/', views.import_sites_csv, name='import_sites_csv'),
    path('locations/export/csv/', views.export_locations_csv, name='export_locations_csv'),
    path('locations/import/csv/', views.import_locations_csv, name='import_locations_csv'),
    
    # POD Generation
    path('locations/generate-pods/', views.generate_pods, name='generate_pods'),
    
    # Database Management (DANGER ZONE)
    path('settings/clear-database/', views.clear_database, name='clear_database'),
    # Demo Data Population
    path('settings/populate-demo-data/', views.populate_demo_data, name='populate_demo_data'),
    
    # Database Statistics and Management
    path('settings/database-stats/', views.database_stats, name='database_stats'),
    path('settings/backup-database/', views.backup_database, name='backup_database'),
    path('settings/populate-sample-data/', views.populate_sample_data, name='populate_sample_data'),
    path('settings/reset-rbac/', views.reset_rbac, name='reset_rbac'),
    
    # Bulk Location Management
    path('settings/locations/bulk/', views.bulk_locations_view, name='bulk_locations'),
    path('api/locations/bulk-edit/', views.bulk_edit_locations, name='bulk_edit_locations'),
    path('playwright-slideshow/', playwright_slideshow, name='playwright_slideshow'),
]

urlpatterns += [
    path('health/', health_check, name='health_check'),
    path('health', health_check, name='health_check_no_slash'),  # Handle requests without trailing slash
    path('health/simple/', simple_health_check, name='simple_health_check'),
    path('health/simple', simple_health_check, name='simple_health_check_no_slash'),
    path('api/playwright-debug/', views.playwright_debug_api, name='playwright_debug_api'),
    path('api/playwright/natural-language/', views.run_natural_language_test_api, name='run_natural_language_test_api'),
    path('api/playwright/rbac-suite/', views.run_rbac_test_suite_api, name='run_rbac_test_suite_api'),
    path('api/playwright/results/', views.get_test_results_api, name='get_test_results_api'),
    path('api/playwright/screenshots/', views.get_test_screenshots_api, name='get_test_screenshots_api'),
    path('api/playwright/scenarios/', views.run_test_scenario_api, name='run_test_scenario_api'),
    path('api-explorer/', views.api_explorer, name='api_explorer'),
    path('health/clear_logs/', clear_health_logs, name='clear_health_logs'),
    path('api/test-health/', views.test_health, name='test_health'),
    path('api/test-database/', views.test_database, name='test_database'),
    path('api/test-cache/', views.test_cache, name='test_cache'),
]