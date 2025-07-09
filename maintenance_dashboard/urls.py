"""maintenance_dashboard URL Configuration"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', RedirectView.as_view(pattern_name='equipment:equipment_list', permanent=False)),
    path('auth/', include('django.contrib.auth.urls')),
    path('equipment/', include('equipment.urls')),
    path('maintenance/', include('maintenance.urls')),
    path('events/', include('events.urls')),
    path('core/', include('core.urls')),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)