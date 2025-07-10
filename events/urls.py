"""
URL configuration for events app.
"""

from django.urls import path
from . import views

app_name = 'events'

urlpatterns = [
    # Calendar views
    path('', views.calendar_view, name='calendar_view'),
    path('calendar/', views.calendar_view, name='calendar_view'),
    
    # Event management
    path('events/', views.event_list, name='event_list'),
    path('events/add/', views.add_event, name='add_event'),
    path('events/<int:event_id>/', views.event_detail, name='event_detail'),
    path('events/<int:event_id>/edit/', views.edit_event, name='edit_event'),
    path('events/<int:event_id>/complete/', views.complete_event, name='complete_event'),
    
    # AJAX endpoints (replicate original web2py functionality)
    path('api/events/', views.fetch_events, name='fetch_events'),
    path('api/events/<int:event_id>/', views.get_event, name='get_event'),
    path('api/test-events/', views.test_events_api, name='test_events_api'),
    
    # Equipment events
    path('equipment/<int:equipment_id>/events/', views.equipment_events, name='equipment_events'),
]