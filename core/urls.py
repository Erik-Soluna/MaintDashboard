"""
URL configuration for core app.
"""

from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Dashboard and main views
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile, name='profile'),
    path('map/', views.map_view, name='map_view'),
    
    # Settings
    path('settings/', views.settings, name='settings'),
    path('settings/locations/', views.locations_settings, name='locations_settings'),
    path('settings/equipment-items/', views.equipment_items_settings, name='equipment_items_settings'),
    path('settings/users/', views.user_management, name='user_management'),
    
    # Location management
    path('locations/add/', views.add_location, name='add_location'),
    path('locations/<int:location_id>/edit/', views.edit_location, name='edit_location'),
    path('locations/<int:location_id>/delete/', views.delete_location, name='delete_location'),
    
    # Equipment category management
    path('categories/add/', views.add_equipment_category, name='add_equipment_category'),
    path('categories/<int:category_id>/edit/', views.edit_equipment_category, name='edit_equipment_category'),
    path('categories/<int:category_id>/delete/', views.delete_equipment_category, name='delete_equipment_category'),
    
    # API endpoints
    path('api/locations/', views.locations_api, name='locations_api'),
    path('api/locations/<int:location_id>/', views.location_detail_api, name='location_detail_api'),
    path('api/equipment-items/', views.equipment_items_api, name='equipment_items_api'),
    path('api/users/', views.users_api, name='users_api'),
    
    # CSV Import/Export
    path('sites/export/csv/', views.export_sites_csv, name='export_sites_csv'),
    path('sites/import/csv/', views.import_sites_csv, name='import_sites_csv'),
    path('locations/export/csv/', views.export_locations_csv, name='export_locations_csv'),
    path('locations/import/csv/', views.import_locations_csv, name='import_locations_csv'),
]