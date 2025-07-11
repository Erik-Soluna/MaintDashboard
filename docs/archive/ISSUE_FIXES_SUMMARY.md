# Issue Fixes Summary

## Issues Addressed

### 1. Location Deletion Not Working

**Problem**: Locations were unable to be deleted through the UI interface.

**Root Cause**: The frontend was making AJAX DELETE requests to the API endpoint `/core/api/locations/{id}/`, but the `location_detail_api` view was only deactivating locations (`is_active = False`) instead of actually deleting them.

**Fix Applied**: 
- Modified the `location_detail_api` DELETE method in `core/views.py` to properly delete locations
- Added the same dependency checks as the original `delete_location` view:
  - Check if location has equipment assigned
  - Check if location has child locations
  - Only delete if no dependencies exist
- Return appropriate error messages with HTTP 400 status for validation failures

**File Changed**: `core/views.py` (lines 525-537)

### 2. Site Selection - Cannot Switch Back to "All"

**Problem**: When switching from "All" to a specific site in the header, it worked correctly, but switching back to "All" didn't work properly.

**Root Cause**: The template was not properly marking the "All - Soluna" option as selected when no site was chosen.

**Fix Applied**:
- Added a condition to the "All" option in the site selector to mark it as selected when `selected_site_id` is empty/null
- Changed from: `<option value="">All - Soluna</option>`
- To: `<option value="" {% if not selected_site_id %}selected{% endif %}>All - Soluna</option>`

**File Changed**: `templates/base.html` (site selector section)

### 3. CSS Dropdown Cutting Off Bottom Portion

**Problem**: Dropdown menus were cutting off their bottom portions, likely due to fixed height constraints instead of auto height.

**Root Cause**: Several dropdown and select elements had restrictive height settings and max-height values that were too small for content.

**Fixes Applied**:

1. **Select Form Controls**: Added `height: auto` and `min-height: 38px` to ensure proper sizing
   - Fixed `.form-control select` and `select.form-control` styles

2. **Site Selector**: Added `height: auto` and `min-height: 38px` to `.site-selector` class

3. **Dropdown Menus**: 
   - Increased `max-height` from `400px` to `90vh` for `.dropdown-menu`
   - Increased `max-height` from `400px` to `90vh` for `.nav-tabs-custom .dropdown-menu`
   - This allows dropdowns to use up to 90% of the viewport height instead of being limited to 400px

**File Changed**: `templates/base.html` (CSS styles section)

## Testing Recommendations

1. **Location Deletion**: 
   - Test deleting locations without dependencies (should work)
   - Test deleting locations with equipment (should show error)
   - Test deleting locations with child locations (should show error)

2. **Site Selection**:
   - Select a specific site and verify it's selected
   - Switch back to "All - Soluna" and verify it's properly selected
   - Check that URL parameters and session state are handled correctly

3. **Dropdown CSS**:
   - Test dropdowns in different viewport sizes
   - Verify dropdowns with many items don't get cut off
   - Test on Chrome (as mentioned in original issue)
   - Check navigation dropdowns, user menu dropdown, and form select dropdowns

## Notes

- All fixes maintain backward compatibility
- No database migrations required
- Changes only affect frontend behavior and API responses
- Error handling has been improved for location deletion