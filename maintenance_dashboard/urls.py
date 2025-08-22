"""maintenance_dashboard URL Configuration"""

from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from core.views import dashboard
from version import get_git_version
from django.http import JsonResponse
import os

def version_info(request):
    """Display comprehensive version and deployment information."""
    try:
        version_data = get_git_version()
        # Add deployment context
        version_data.update({
            'deployment_info': {
                'debug_mode': settings.DEBUG,
                'timezone': str(settings.TIME_ZONE),
                'database_engine': settings.DATABASES['default']['ENGINE'] if 'default' in settings.DATABASES else 'unknown',
                'static_files_root': str(settings.STATIC_ROOT) if hasattr(settings, 'STATIC_ROOT') else 'not_set',
                'media_files_root': str(settings.MEDIA_ROOT) if hasattr(settings, 'MEDIA_ROOT') else 'not_set',
                'environment': os.environ.get('ENVIRONMENT', 'development'),
                'docker_container': os.environ.get('HOSTNAME', 'unknown'),
            }
        })
        return JsonResponse(version_data)
    except Exception as e:
        return JsonResponse({
            'error': 'Failed to get version information',
            'details': str(e)
        }, status=500)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', dashboard, name='dashboard'),
    path('equipment/', include('equipment.urls')),
    path('maintenance/', include('maintenance.urls')),
    path('events/', include('events.urls')),
    path('core/', include('core.urls')),
    path('version/', version_info, name='version'),
    # Authentication URLs
    path('auth/login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('auth/logout/', auth_views.LogoutView.as_view(), name='logout'),
    # Password reset URLs
    path('auth/password-reset/', auth_views.PasswordResetView.as_view(template_name='registration/password_reset_form.html'), name='password_reset'),
    path('auth/password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'), name='password_reset_done'),
    path('auth/reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'), name='password_reset_confirm'),
    path('auth/reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), name='password_reset_complete'),
]

# Serve favicon.ico and robots.txt at root level
def favicon_view(request):
    return serve(request, 'images/favicon.ico', document_root=os.path.join(settings.BASE_DIR, 'static'))

def robots_txt_view(request):
    return serve(request, 'robots.txt', document_root=os.path.join(settings.BASE_DIR, 'static'))

urlpatterns += [
    path('favicon.ico', favicon_view),
    path('robots.txt', robots_txt_view),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)