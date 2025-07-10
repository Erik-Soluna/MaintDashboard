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
    
    # Calendar integration
    path('ical/', views.generate_ical_feed, name='ical_feed'),
    path('webhook/google/', views.google_calendar_webhook, name='google_calendar_webhook'),
    path('settings/', views.calendar_settings, name='calendar_settings'),
    
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
    
    # New AJAX endpoints for popup functionality
    path('api/events/create/', views.create_event_ajax, name='create_event_ajax'),
    path('api/events/<int:event_id>/update/', views.update_event_ajax, name='update_event_ajax'),
    path('api/form-data/', views.get_form_data, name='get_form_data'),
    
    # Equipment events
    path('equipment/<int:equipment_id>/events/', views.equipment_events, name='equipment_events'),
]