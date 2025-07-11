# Fixes Implemented - Maintenance Dashboard

## Issues Fixed

### 1. FieldError with 'end_datetime'
**Issue**: `FieldError: Cannot resolve keyword 'end_datetime' into field`
**Fix**: Updated `equipment/models.py` line 157-159 to use `actual_end` instead of `end_datetime`:
```python
# Before: .order_by('-end_datetime').first()
# After: .order_by('-actual_end').first()
```

### 2. UserProfile Missing Error
**Issue**: `RelatedObjectDoesNotExist: User has no userprofile`
**Fix**: Added proper UserProfile creation in multiple views:
- `core/views.py` - `profile_view()`, `dashboard()`, `settings_view()`
- Used `UserProfile.objects.get_or_create(user=request.user)` pattern
- Created context processors to handle this globally

### 3. Dropdown Menu Clipping
**Issue**: Dropdown menus were being cut off and not properly positioned
**Fix**: Added comprehensive CSS in `templates/base.html`:
- Proper z-index layering (Header: 1040, Navigation: 1030, Dropdowns: 1050)
- Fixed positioning with `position: absolute` and proper top/left values
- Added theme-aware styling using CSS variables
- Improved spacing and overflow handling

### 4. Site Selection Not Working
**Issue**: Site selector was empty and didn't filter data across pages
**Fix**: Implemented complete site filtering system:
- **Context Processors**: Created `core/context_processors.py` with `site_context()` and `user_context()`
- **Settings Update**: Added context processors to `maintenance_dashboard/settings.py`
- **Template Update**: Updated site selector in `templates/base.html` to populate with actual sites
- **View Updates**: Added site filtering to:
  - `core/views.py` - `dashboard()` with maintenance activities and equipment statistics
  - `equipment/views.py` - `equipment_list()` and `manage_equipment()`
- **Global Filtering**: Site selection now persists across all pages and filters data appropriately

### 5. Missing Maintenance Template
**Issue**: `TemplateDoesNotExist: maintenance/maintenance_list.html`
**Fix**: Created comprehensive maintenance list template with:
- Statistics cards showing activity counts
- Upcoming and overdue activities tables
- In-progress activities section
- Quick action buttons
- Auto-refresh functionality

## RBAC System Implementation (Started)

### New Models Added to `core/models.py`:
1. **Permission Model**: Stores individual permissions with codenames
2. **Role Model**: Groups permissions together with many-to-many relationship
3. **Updated UserProfile**: Now uses Role foreign key instead of simple choices

### RBAC Utilities Created (`core/rbac.py`):
- Permission checking decorators
- Default permission and role initialization
- Helper functions for permission management

### Permission Structure:
- **Admin**: Full system access
- **Manager**: Equipment and maintenance management
- **Technician**: Equipment editing and maintenance completion
- **Viewer**: Read-only access

## Site Filtering Implementation

### How It Works:
1. **Context Processor**: `site_context()` provides site information to all templates
2. **Session Storage**: Selected site ID is stored in session for persistence
3. **Default Site**: Uses user's default site from profile if no explicit selection
4. **Global Filtering**: All views respect the selected site:
   - Dashboard: Filters maintenance activities and equipment statistics
   - Equipment: Filters equipment lists and management views
   - Maintenance: Will filter activities (to be implemented)

### Site Selection Priority:
1. URL parameter (`?site_id=X`)
2. Session storage (`request.session['selected_site_id']`)
3. User's default site (`user_profile.default_site`)
4. No filter (show all)

## Files Modified

### Core Files:
- `maintenance_dashboard/settings.py` - Added context processors
- `core/models.py` - Added Permission, Role models, updated UserProfile
- `core/context_processors.py` - NEW: Site and user context
- `core/rbac.py` - NEW: RBAC utilities and decorators
- `core/views.py` - Fixed UserProfile issues, added site filtering
- `core/forms.py` - NEW: Location and EquipmentCategory forms

### Templates:
- `templates/base.html` - Fixed dropdowns, updated site selector
- `templates/maintenance/maintenance_list.html` - NEW: Maintenance dashboard

### Equipment:
- `equipment/models.py` - Fixed end_datetime -> actual_end
- `equipment/views.py` - Added site filtering to equipment views

## Database Changes Required

### New Tables:
1. `core_permission` - Stores individual permissions
2. `core_role` - Stores roles
3. `core_role_permissions` - Many-to-many relationship
4. `core_userprofile` - Updated with role foreign key

### Migration Commands Needed:
```bash
python manage.py makemigrations core
python manage.py migrate
```

### Initialize RBAC Data:
```python
# In Django shell or management command
from core.rbac import assign_default_roles
assign_default_roles()
```

## Next Steps

### 1. Complete RBAC Implementation:
- Add role management views in admin or settings
- Apply permission decorators to all views
- Create role assignment interface
- Test permission restrictions

### 2. Site Filtering for All Apps:
- Add site filtering to maintenance views
- Add site filtering to events/calendar views
- Ensure all reports respect site selection

### 3. User Management Interface:
- Create user role assignment interface
- Add bulk user operations
- Implement user deactivation/activation

### 4. Testing:
- Test all dropdown menus across different browsers
- Test site selection persistence
- Test UserProfile creation for existing users
- Test RBAC permission enforcement

## Configuration Notes

### Default Sites:
- Users can set default sites in their profile
- Site selection persists across browser sessions
- "All - Soluna" option shows data from all sites

### Permission Management:
- Superusers bypass all permission checks
- System roles cannot be deleted
- Custom roles can be created with specific permission sets

### Theme Support:
- Dropdown menus now properly support dark/light themes
- Site selector respects user theme preference
- All UI components maintain consistent styling