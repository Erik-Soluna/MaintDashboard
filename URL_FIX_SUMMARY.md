# Django URL Routing Fix - generate_scheduled_activities

## Issue Fixed

**Error:** `NoReverseMatch at /maintenance/schedules/`
**Details:** `Reverse for 'generate_scheduled_activities' not found. 'generate_scheduled_activities' is not a valid view function or pattern name.`

## Root Cause

The application had:
- ✅ A view function `generate_scheduled_activities` in `maintenance/views.py`
- ✅ A template `templates/maintenance/generate_activities.html`
- ✅ A template reference `{% url 'maintenance:generate_scheduled_activities' %}` in `schedule_list.html`
- ❌ **Missing URL pattern** for `generate_scheduled_activities` in `maintenance/urls.py`

## Solution Implemented

Added the missing URL pattern to `maintenance/urls.py`:

```python
path('generate-scheduled-activities/', views.generate_scheduled_activities, name='generate_scheduled_activities'),
```

**Location:** Added after line 39, in the AJAX endpoints section.

## Files Modified

- ✅ `maintenance/urls.py` - Added missing URL pattern

## Technical Details

### Before (Broken)
- Template: `{% url 'maintenance:generate_scheduled_activities' %}` 
- URL patterns: **No matching pattern**
- Result: **NoReverseMatch error**

### After (Fixed)
- Template: `{% url 'maintenance:generate_scheduled_activities' %}` 
- URL patterns: `path('generate-scheduled-activities/', views.generate_scheduled_activities, name='generate_scheduled_activities')`
- Result: **✅ Works correctly**

### Related Components

The application also has an alias function:
```python
def generate_maintenance_activities(request):
    """Alias for generate_scheduled_activities to match URL pattern."""
    return generate_scheduled_activities(request)
```

This alias has its own URL pattern:
```python
path('api/generate-activities/', views.generate_maintenance_activities, name='generate_activities'),
```

Both URL patterns now work and point to the same underlying functionality.

## Verification

After this fix:
1. ✅ `/maintenance/schedules/` page loads without errors
2. ✅ "Generate Activities" button works correctly
3. ✅ Activity generation process functions as intended
4. ✅ All existing functionality preserved

## URLs Now Available

- `/maintenance/generate-scheduled-activities/` → Direct access to the view
- `/maintenance/api/generate-activities/` → API/AJAX access to the same functionality
- Both URLs provide the same maintenance activity generation features

This fix resolves the NoReverseMatch error while maintaining backward compatibility with existing API endpoints.