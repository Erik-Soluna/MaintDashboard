"""
URL configuration for maintenance_dashboard project.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.http import HttpResponse
from django.views.decorators.http import require_http_methods
import os

@require_http_methods(["GET"])
def robots_txt(request):
    """Serve robots.txt to disallow all search engine crawlers."""
    robots_content = "User-agent: *\nDisallow: /\n"
    return HttpResponse(robots_content, content_type="text/plain")

urlpatterns = [
    path('admin/', admin.site.urls),
    path('robots.txt', robots_txt, name='robots_txt'),
    path('', include('core.urls')),  # Include core URLs at root level - MUST BE FIRST
    path('equipment/', include('equipment.urls')),
    path('maintenance/', include('maintenance.urls')),
    path('events/', include('events.urls')),
    # Authentication URLs
    path('auth/login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('auth/logout/', auth_views.LogoutView.as_view(), name='logout'),
    # Password reset URLs
    path('auth/password-reset/', auth_views.PasswordResetView.as_view(template_name='registration/password_reset_form.html'), name='password_reset'),
    path('auth/password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'), name='password_reset_done'),
    path('auth/reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'), name='password_reset_confirm'),
    path('auth/reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), name='password_reset_complete'),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)