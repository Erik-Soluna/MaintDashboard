# GitHub Issue: Fix Portainer webhook settings save functionality

## Problem
The Portainer webhook settings page is not saving configuration properly. Users report that clicking save refreshes the page but no data is saved.

## Current Status
- Database model `PortainerConfig` has been created and migrated
- Views have been updated to use database instead of environment files
- However, the save functionality is still not working as expected

## Investigation Needed
1. Check if the form is submitting correctly
2. Verify database transactions are working
3. Debug the save process in the `webhook_settings` view
4. Check for any JavaScript issues preventing form submission
5. Verify the `PortainerConfig.get_config()` method is working properly
6. Check if there are any CSRF token issues
7. Verify the form field names match what the view expects

## Expected Behavior
- User enters Portainer URL and Stack Name
- Clicks 'Save Configuration'
- Settings are saved to database
- User sees success message with saved values
- Configuration is immediately available for testing

## Technical Details
- Model: `core.models.PortainerConfig`
- View: `core.views.webhook_settings`
- Template: `templates/core/webhook_settings.html`
- Form fields: `portainer_url`, `stack_name`, `portainer_user`, `portainer_password`, `webhook_secret`

## Debug Steps
1. Add logging to the save action in the view
2. Check if the POST data is being received correctly
3. Verify the database save operation
4. Test the `PortainerConfig.get_config()` method independently
5. Check browser developer tools for any JavaScript errors

## Priority
Medium - affects configuration management functionality

## Labels
- bug
- configuration
- portainer
- webhook

## Related Files
- `core/models.py` - PortainerConfig model
- `core/views.py` - webhook_settings view
- `templates/core/webhook_settings.html` - template
- `core/admin.py` - admin configuration 