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
    path('settings/', views.settings_view, name='settings'),
    path('user-management/', views.user_management, name='user_management'),
    path('roles-permissions/', views.roles_permissions_management, name='roles_permissions_management'),
    path('system-health/', views.system_health, name='system_health'),
    path('debug/', views.debug_view, name='debug_view'),
    path('webhook-settings/', views.webhook_settings, name='webhook_settings'),
    path('docker-logs/', views.docker_logs, name='docker_logs'),
    path('version/', views.version_view, name='version'),
    path('version/html/', views.version_html_view, name='version_html'),
]