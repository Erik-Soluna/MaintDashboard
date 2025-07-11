# Bug Fixes Guide

This document provides solutions for common bugs and issues in the Maintenance Dashboard.

## 🔧 Recently Fixed Issues

### 1. Site Selection Bug - "All Sites" Option Not Working

**Problem**: When selecting a site in the header and then trying to go back to "All Sites", it keeps the last selected site instead of showing all items.

**Root Cause**: The JavaScript site selector wasn't properly handling the empty value for "All Sites" selection.

**Fix Applied**:
- Updated the `changeSite()` JavaScript function in `templates/base.html`
- Modified the logic to explicitly set `?site_id=` when "All Sites" is selected
- This triggers the clearing logic in the context processor

**How to Verify Fix**:
1. Select any site from the header dropdown
2. Navigate to any page (Equipment, Maintenance, etc.)
3. Notice that content is filtered to that site
4. Go back to header dropdown and select "All - Soluna"
5. Content should now show all items across all sites

### 2. Missing System Permissions in Roles Management

**Problem**: No system permissions appear in the Roles and Permissions management interface.

**Root Cause**: The RBAC (Role-Based Access Control) permissions were defined but not initialized in the database.

**Fix Applied**:
1. **Automatic Initialization**: Modified `core/apps.py` to automatically create permissions when the Django app starts up
2. **Management Command**: Created `core/management/commands/ensure_permissions.py` for manual permission initialization
3. **Permission Verification**: Added comprehensive permission checking and display

**Available Permissions by Module**:
- **Admin**: Full system access
- **Equipment**: View, create, edit, delete equipment
- **Maintenance**: View, create, edit, delete, assign, complete maintenance
- **Users**: View and manage user accounts
- **Settings**: View and manage system settings
- **Calendar**: View, create, edit, delete calendar events
- **Reports**: View and generate reports

**How to Verify Fix**:
1. Go to Settings → Roles & Permissions (or `/core/settings/roles-permissions/`)
2. You should see all system permissions organized by module
3. Permissions should be available for assignment to roles
4. Test creating/editing roles with different permission combinations

**Manual Fix (if needed)**:
If permissions still don't appear, run:
```bash
python manage.py ensure_permissions
```

Or initialize the complete RBAC system:
```bash
python manage.py init_rbac
```

## 🛠️ Other Common Issues

### Site Filter Not Persisting
**Problem**: Site selection doesn't persist between page navigation.
**Solution**: The context processor automatically handles session persistence. If issues persist, check browser cookies and session configuration.

### Permissions Not Updating After Role Changes
**Problem**: User permissions don't update immediately after role changes.
**Solution**: 
1. Log out and log back in
2. Or restart the Django server in development
3. Check that the role has `is_active=True`

### Database Connection Errors
**Problem**: Database connection errors, especially in Docker.
**Solution**: 
1. Check that the database container is running
2. Run the automated database initialization: `./fix-database-now.sh`
3. See [Database Troubleshooting Guide](../database/troubleshooting.md)

### CSS/Layout Issues
**Problem**: Dropdown text truncated or layout problems.
**Solution**: The system includes comprehensive CSS fixes for layout issues. If problems persist:
1. Clear browser cache
2. Check for JavaScript console errors
3. Verify Bootstrap and CSS files are loading correctly

## 🧪 Testing Your Fixes

### Site Selection Testing
```javascript
// Test in browser console
function testSiteSelection() {
    // Select different sites
    changeSite('1'); // Select first site
    console.log('Current URL:', window.location.href);
    
    // Select "All Sites"
    changeSite(''); // Select all sites
    console.log('Current URL:', window.location.href);
}
```

### Permissions Testing
```python
# Test in Django shell
from core.models import Permission, Role, UserProfile
from django.contrib.auth.models import User

# Check permissions exist
print("Total permissions:", Permission.objects.count())
print("Permissions by module:")
for module in Permission.objects.values_list('module', flat=True).distinct():
    count = Permission.objects.filter(module=module).count()
    print(f"  {module}: {count}")

# Test user permissions
user = User.objects.first()
profile = user.userprofile
print(f"User {user.username} permissions:")
for perm in profile.get_permissions():
    print(f"  - {perm.codename}: {perm.name}")
```

## 📞 Getting Help

If you encounter issues not covered here:

1. **Check Logs**: Look at Django logs and browser console for error messages
2. **Documentation**: Review the [comprehensive documentation](../README.md)
3. **Common Issues**: Check [Common Issues Guide](common-issues.md)
4. **Create Issue**: Report bugs in the project repository

## 🔄 Prevention

To prevent these issues in the future:

1. **Regular Updates**: Keep the application updated
2. **Database Maintenance**: Run periodic database maintenance
3. **Permission Audits**: Regularly review user roles and permissions
4. **Testing**: Test functionality after any configuration changes

---

*Last updated: [Current Date] - These fixes are included in the latest version of the Maintenance Dashboard.*