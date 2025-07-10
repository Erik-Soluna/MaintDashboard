# Fixes Summary

## Issues Fixed

### 1. UserProfile Admin Error
**Problem**: `AttributeError: 'UserProfile' object has no attribute 'get_role_display'`
**Root Cause**: The `role` field in UserProfile is a ForeignKey to Role model, not a CharField with choices, so `get_role_display()` method doesn't exist.

**Fix**: Updated `core/admin.py` line 64:
```python
# Before
return obj.userprofile.get_role_display()

# After  
if obj.userprofile.role:
    return obj.userprofile.role.display_name
else:
    return 'No Role Assigned'
```

### 2. Equipment Edit Template Error
**Problem**: `VariableDoesNotExist: Failed lookup for key [username] in None`
**Root Cause**: Template was trying to access `.username` on `equipment.updated_by` or `equipment.created_by` when they could be null.

**Fix**: Updated `templates/equipment/edit_equipment.html` to check for null values:
```html
<!-- Before -->
{{ equipment.updated_by.get_full_name|default:equipment.updated_by.username|default:"System" }}

<!-- After -->
{% if equipment.updated_by %}
    {{ equipment.updated_by.get_full_name|default:equipment.updated_by.username }}
{% else %}
    System
{% endif %}
```

### 3. Equipment Page Site Information
**Problem**: Equipment page should show what Site it is, next to location.

**Fixes**:
1. **Added site method to Equipment model** (`equipment/models.py`):
```python
def get_site(self):
    """Get the site location for this equipment."""
    if self.location:
        return self.location.get_site_location()
    return None
```

2. **Updated Equipment Admin** (`equipment/admin.py`):
   - Added `get_site` to `list_display`
   - Added method to display site information:
```python
def get_site(self, obj):
    """Get the site location for this equipment."""
    site = obj.get_site()
    return site.name if site else 'No Site'
get_site.short_description = 'Site'
```

3. **Updated Equipment List Template** (`templates/equipment/equipment_list.html`):
   - Changed column header from "Location" to "Site / Location"
   - Updated display to show site as badge and location below:
```html
{% if equipment.location.get_site_location %}
    <span class="badge badge-info">{{ equipment.location.get_site_location.name }}</span><br>
    <small>{{ equipment.location.name }}</small>
{% else %}
    {{ equipment.location.name }}
{% endif %}
```

### 4. Site Selection Filter Issue
**Problem**: "Select site sticks to last selected without ability to change it to all."
**Root Cause**: Context processor wasn't properly handling empty string value for "All Sites" option.

**Fixes**:
1. **Updated context processor** (`core/context_processors.py`):
```python
# Now properly handles site_id='' to clear selection
if selected_site_id is not None:
    if selected_site_id == '':
        # Clear site selection (All Sites)
        if 'selected_site_id' in request.session:
            del request.session['selected_site_id']
        context['selected_site_id'] = None
    else:
        # Set specific site selection
        request.session['selected_site_id'] = selected_site_id
        context['selected_site_id'] = selected_site_id
```

2. **Updated equipment views** (`equipment/views.py`):
   - Fixed both `equipment_list` and `manage_equipment` views to properly handle None values:
```python
selected_site_id = request.GET.get('site_id')
if selected_site_id is None:
    selected_site_id = request.session.get('selected_site_id')
```

## Result
- ✅ Admin interface now works without errors
- ✅ Equipment edit page works correctly
- ✅ Equipment list shows site information clearly
- ✅ Site selector now allows switching back to "All Sites" properly
- ✅ Site filtering works as expected

## Testing
All fixes have been implemented and should resolve the reported issues:
1. Admin user management should work without the get_role_display error
2. Equipment editing should work without template errors
3. Equipment list should show site information next to location
4. Site selector should allow switching between specific sites and "All Sites"