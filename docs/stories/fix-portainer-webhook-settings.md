# Story: Fix Portainer Webhook Settings Save Functionality

## Story Information
- **Story ID**: WEBHOOK-001
- **Priority**: High
- **Estimate**: 4 hours
- **Status**: In Progress
- **Assigned To**: Development Team

## User Story
As a system administrator, I want to be able to save Portainer webhook configuration settings so that I can properly configure automated deployments and stack updates.

## Acceptance Criteria
- [ ] User can enter Portainer URL and Stack Name
- [ ] User can enter optional credentials (username, password, webhook secret)
- [ ] Settings are saved to database when "Save Configuration" is clicked
- [ ] User receives immediate visual feedback that settings were saved
- [ ] Saved settings are displayed correctly on page reload
- [ ] Settings persist across application restarts
- [ ] Error messages are shown if validation fails
- [ ] Sensitive data (passwords) are properly masked in the UI

## Current Issue Analysis

### Problem Description
The Portainer webhook settings page is not saving configuration properly. Users report that clicking save refreshes the page but no data is saved. The logs show empty values:
```
Portainer config loaded - URL: , Stack: , User: None***
```

### Root Cause
The original implementation tried to save settings to environment files, but Django loads environment variables at startup. Changes to environment files require application restart to take effect.

### Technical Details
- **Model**: `PortainerConfig` (already created and migrated)
- **View**: `core.views.webhook_settings`
- **Template**: `templates/core/webhook_settings.html`
- **Form Fields**: `portainer_url`, `stack_name`, `portainer_user`, `portainer_password`, `webhook_secret`

## Implementation Plan

### Phase 1: Debug Current Implementation
1. **Add Logging**: Add detailed logging to the save action
2. **Form Validation**: Verify form data is being received correctly
3. **Database Operations**: Check if database save operations are working
4. **Error Handling**: Identify any exceptions or errors

### Phase 2: Fix Core Issues
1. **Database Integration**: Ensure settings are saved to `PortainerConfig` model
2. **Form Processing**: Fix any form processing issues
3. **Validation**: Implement proper form validation
4. **Error Messages**: Improve error handling and user feedback

### Phase 3: Enhance User Experience
1. **Visual Feedback**: Add immediate success/error indicators
2. **Data Masking**: Properly mask sensitive data in the UI
3. **Loading States**: Add loading indicators during save operations
4. **Form State**: Maintain form state during validation errors

## Technical Implementation

### Database Model
```python
class PortainerConfig(models.Model):
    portainer_url = models.URLField(max_length=500, blank=True)
    portainer_user = models.CharField(max_length=100, blank=True)
    portainer_password = models.CharField(max_length=255, blank=True)
    stack_name = models.CharField(max_length=100, blank=True)
    webhook_secret = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @classmethod
    def get_config(cls):
        config, created = cls.objects.get_or_create(pk=1)
        return config
```

### View Logic
```python
@login_required
@user_passes_test(is_staff_or_superuser)
def webhook_settings(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'save_config':
            try:
                config = PortainerConfig.get_config()
                
                # Handle sensitive fields
                portainer_user = request.POST.get('portainer_user', '')
                portainer_password = request.POST.get('portainer_password', '')
                webhook_secret = request.POST.get('webhook_secret', '')
                
                # Update fields if not masked
                if portainer_user and not portainer_user.startswith('***'):
                    config.portainer_user = portainer_user
                if portainer_password and not portainer_password.startswith('*'):
                    config.portainer_password = portainer_password
                if webhook_secret and not webhook_secret.startswith('****'):
                    config.webhook_secret = webhook_secret
                
                # Update non-sensitive fields
                config.portainer_url = request.POST.get('portainer_url', '')
                config.stack_name = request.POST.get('stack_name', '')
                
                # Validate required fields
                if not config.portainer_url:
                    messages.error(request, 'Portainer URL is required.')
                    return redirect('core:webhook_settings')
                
                if not config.stack_name:
                    messages.error(request, 'Stack Name is required.')
                    return redirect('core:webhook_settings')
                
                # Save to database
                config.save()
                messages.success(request, 'Configuration saved successfully!')
                
            except Exception as e:
                logger.error(f"Error saving webhook config: {str(e)}")
                messages.error(request, f'Error saving configuration: {str(e)}')
    
    # Get configuration for display
    config = PortainerConfig.get_config()
    # ... rest of view logic
```

### Template Updates
```html
<!-- Add loading state -->
<button type="submit" name="action" value="save_config" class="btn-webhook primary" id="save-btn">
    <i class="fas fa-save"></i>
    <span class="btn-text">Save Configuration</span>
    <span class="btn-loading" style="display: none;">
        <i class="fas fa-spinner fa-spin"></i> Saving...
    </span>
</button>

<!-- Add success/error indicators -->
<div id="save-status" class="mt-3" style="display: none;"></div>
```

### JavaScript Enhancements
```javascript
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('webhook-config-form');
    const saveBtn = document.getElementById('save-btn');
    const statusDiv = document.getElementById('save-status');
    
    form.addEventListener('submit', function(e) {
        if (e.submitter && e.submitter.name === 'action' && e.submitter.value === 'save_config') {
            // Show loading state
            saveBtn.disabled = true;
            saveBtn.querySelector('.btn-text').style.display = 'none';
            saveBtn.querySelector('.btn-loading').style.display = 'inline';
            
            // Hide status after 5 seconds
            setTimeout(() => {
                statusDiv.style.display = 'none';
            }, 5000);
        }
    });
});
```

## Testing Strategy

### Unit Tests
- Test `PortainerConfig.get_config()` method
- Test form validation logic
- Test sensitive data masking
- Test database save operations

### Integration Tests
- Test complete save workflow
- Test form submission with various data
- Test error handling scenarios
- Test page reload after save

### Manual Testing
- Test with valid configuration data
- Test with invalid/missing data
- Test with masked sensitive data
- Test error scenarios (database errors, etc.)

## Definition of Done
- [ ] All acceptance criteria are met
- [ ] Code is reviewed and approved
- [ ] Unit tests are written and passing
- [ ] Integration tests are written and passing
- [ ] Manual testing is completed
- [ ] Documentation is updated
- [ ] No new bugs are introduced
- [ ] Performance is not degraded

## Risk Assessment
- **Low Risk**: Standard Django form processing
- **Medium Risk**: Database transaction handling
- **Low Risk**: UI/UX improvements

## Dependencies
- Django ORM working correctly
- Database migrations applied
- User authentication system working
- CSRF protection enabled

## Notes
- This story addresses the immediate issue with settings not saving
- Future enhancements could include API-based configuration management
- Consider adding audit logging for configuration changes
- May need to update related functions that use Portainer settings 