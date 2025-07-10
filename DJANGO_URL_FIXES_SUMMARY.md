# Django URL Fixes Summary

## Issues Fixed

This document summarizes the Django URL pattern and template syntax errors that were resolved.

## NoReverseMatch Errors Fixed

### 1. Missing `activity_list` URL pattern
**Error**: `Reverse for 'activity_list' not found`
**Location**: Used in maintenance templates
**Fix**: Added `path('activities/', views.activity_list, name='activity_list')` to `maintenance/urls.py`

### 2. Missing `user_management` URL pattern
**Error**: `Reverse for 'user_management' not found`
**Location**: Used in `templates/core/settings.html`
**Fix**: Added `path('settings/users/', views.user_management, name='user_management')` to `core/urls.py`

### 3. Missing `locations_api` URL pattern
**Error**: `Reverse for 'locations_api' not found`
**Location**: Used in `templates/core/locations_settings.html`
**Fix**: Added `path('api/locations/', views.locations_api, name='locations_api')` to `core/urls.py`

### 4. Missing `schedule_detail` URL pattern
**Error**: Referenced in maintenance schedule templates
**Fix**: Added `path('schedules/<int:schedule_id>/', views.schedule_detail, name='schedule_detail')` to `maintenance/urls.py`

### 5. Missing `overdue_maintenance` URL pattern
**Error**: Referenced in maintenance reports template
**Fix**: Added `path('overdue/', views.overdue_maintenance, name='overdue_maintenance')` to `maintenance/urls.py`

### 6. Missing `equipment_categories_settings` URL pattern
**Error**: Referenced in core views
**Fix**: Added `path('settings/equipment-categories/', views.equipment_categories_settings, name='equipment_categories_settings')` to `core/urls.py`

### 7. Missing activity types CSV import/export URLs
**Error**: Referenced in maintenance templates
**Fix**: Added both patterns to `maintenance/urls.py`:
- `path('activity-types/export/csv/', views.export_activity_types_csv, name='export_activity_types_csv')`
- `path('activity-types/import/csv/', views.import_activity_types_csv, name='import_activity_types_csv')`

### 8. Additional API endpoints added
**Added to `core/urls.py`**:
- `path('api/locations/<int:location_id>/', views.location_detail_api, name='location_detail_api')`
- `path('api/equipment-items/', views.equipment_items_api, name='equipment_items_api')`
- `path('api/users/', views.users_api, name='users_api')`

## Template Syntax Error Fixed

### Events Calendar Settings Template
**Error**: `Could not parse the remainder: ':'/events/webhook/google/'' from 'request.build_absolute_uri:'/events/webhook/google/''`
**Location**: `templates/events/calendar_settings.html` line 113
**Problem**: Invalid Django template syntax - cannot call methods with arguments using `:` syntax
**Fix**:
1. Updated `events/views.py` `calendar_settings` view to build webhook URL in context:
   ```python
   webhook_url = request.build_absolute_uri(reverse('events:google_calendar_webhook'))
   ```
2. Updated template to use context variable:
   ```html
   <div class="url-display" id="webhookUrl">{{ webhook_url }}</div>
   ```
3. Fixed URL name mismatch from `google_webhook` to `google_calendar_webhook`

## Parameter Name Fix

### Activity Type Edit URL
**Fix**: Updated parameter name from `<int:type_id>` to `<int:activity_type_id>` in `maintenance/urls.py` to match view function signature.

## Summary

All identified Django NoReverseMatch and TemplateSyntaxError issues have been resolved by:
- Adding missing URL patterns to appropriate apps
- Fixing template syntax errors
- Ensuring URL names match between views and templates
- Adding proper API endpoints for AJAX functionality

The Django application should now function without these URL-related errors.