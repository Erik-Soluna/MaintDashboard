"""
URL configuration for core app.
"""

from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    
    # Map
    path('map/', views.map_view, name='map_view'),
    
    # Settings
    path('settings/', views.settings_view, name='settings'),
    path('settings/locations/', views.locations_settings, name='locations_settings'),
    path('settings/equipment-items/', views.equipment_items_settings, name='equipment_items_settings'),
    path('settings/user-management/', views.user_management, name='user_management'),
    
    # Settings API endpoints
    path('api/locations/', views.locations_api, name='locations_api'),
    path('api/locations/<int:location_id>/', views.location_detail_api, name='location_detail_api'),
    path('api/equipment-items/', views.equipment_items_api, name='equipment_items_api'),
    path('api/users/', views.users_api, name='users_api'),
]