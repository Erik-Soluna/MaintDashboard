# Maintenance Equipment Loading Fix

## Issue
When adding maintenance activity on `/maintenance/add/`, equipment does not load in the dropdown.

## Root Cause Analysis
The issue was caused by site filtering logic that was applied inconsistently across the application:

1. **Equipment list views** filter equipment by selected site
2. **Maintenance forms** did not respect site filtering
3. When a specific site was selected, maintenance forms would show no equipment because they weren't filtering by the same site

## Solution Implemented

### 1. Updated Maintenance Forms (`maintenance/forms.py`)
- **MaintenanceActivityForm**: Added site filtering logic to respect selected site
- **MaintenanceScheduleForm**: Added site filtering logic to respect selected site
- Both forms now accept a `request` parameter to access session data for site filtering

```python
def __init__(self, *args, **kwargs):
    # Extract request from kwargs to access session data
    self.request = kwargs.pop('request', None)
    super().__init__(*args, **kwargs)
    
    # Filter active options
    equipment_queryset = Equipment.objects.filter(is_active=True)
    
    # Apply site filtering if a site is selected
    if self.request and hasattr(self.request, 'session'):
        from core.models import Location
        from django.db.models import Q
        
        selected_site_id = self.request.GET.get('site_id')
        if selected_site_id is None:
            selected_site_id = self.request.session.get('selected_site_id')
        
        if selected_site_id:
            try:
                selected_site = Location.objects.get(id=selected_site_id, is_site=True)
                equipment_queryset = equipment_queryset.filter(
                    Q(location__parent_location=selected_site) | Q(location=selected_site)
                )
            except Location.DoesNotExist:
                pass
    
    self.fields['equipment'].queryset = equipment_queryset
```

### 2. Updated Maintenance Views (`maintenance/views.py`)
- **add_activity**: Pass request to form for site filtering
- **edit_activity**: Pass request to form for site filtering  
- **add_schedule**: Pass request to form for site filtering
- **edit_schedule**: Pass request to form for site filtering

```python
# Before
form = MaintenanceActivityForm()

# After  
form = MaintenanceActivityForm(request=request)
```

### 3. Enhanced User Experience (`templates/maintenance/add_activity.html`)
- Added helpful warning when no equipment is available for selected site
- Shows equipment count and filtering status
- Provides "Show All Equipment" button to clear site filter
- Displays debug information during development

### 4. Added Debugging and Logging
- Added logging to track equipment counts and filtering
- Added template debugging to show total vs filtered equipment counts
- Added context variables to help identify issues

## Benefits
✅ **Equipment now loads properly** in maintenance forms  
✅ **Consistent site filtering** across all equipment selection  
✅ **Clear user feedback** when no equipment is available  
✅ **Easy option to show all equipment** if needed  
✅ **Maintains user's site selection** throughout the workflow  

## Testing Scenarios
1. **With site selected**: Shows only equipment for that site
2. **No site selected**: Shows all equipment
3. **No equipment for site**: Shows helpful warning with options
4. **No equipment at all**: Prompts to add equipment

## Files Modified
- `maintenance/forms.py` - Added site filtering to forms
- `maintenance/views.py` - Updated to pass request to forms
- `templates/maintenance/add_activity.html` - Enhanced user experience

This fix ensures that maintenance activities can be created successfully while maintaining consistent site filtering behavior across the application.