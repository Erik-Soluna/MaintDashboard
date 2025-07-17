"""maintenance_dashboard URL Configuration"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from django.views.static import serve
from django.http import HttpResponse
import os

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', RedirectView.as_view(pattern_name='core:dashboard', permanent=False)),
    path('auth/', include('django.contrib.auth.urls')),
    path('equipment/', include('equipment.urls')),
    path('maintenance/', include('maintenance.urls')),
    path('events/', include('events.urls')),
    path('core/', include('core.urls')),
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