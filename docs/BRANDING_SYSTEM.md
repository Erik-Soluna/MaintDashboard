# Branding System Documentation

## Overview

The Branding System is a comprehensive customization platform that allows administrators to modify the appearance, labels, and styling of the Maintenance Dashboard without requiring code changes. It provides a user-friendly interface for managing:

- **Site Branding**: Logo, favicon, site name, and tagline
- **Navigation Labels**: Customizable text for all navigation items
- **Theme Colors**: Primary, secondary, and accent color management
- **CSS Customizations**: Advanced styling capabilities for specific components
- **Live Preview**: Real-time testing of changes

## Features

### 1. Site Branding Management

#### Basic Settings
- **Site Name**: Main website name displayed in header
- **Site Tagline**: Optional subtitle below the site name
- **Window Title Prefix/Suffix**: Text to prepend/append to all page titles
- **Header Brand Text**: Text displayed next to the logo

#### Visual Elements
- **Logo Upload**: Support for custom site logos
- **Favicon Management**: Website favicon customization
- **Footer Text**: Customizable copyright and powered-by text

### 2. Navigation Label Customization

All navigation items can have their labels customized:
- Overview → Custom label
- Equipment → Custom label
- Maintenance → Custom label
- Calendar → Custom label
- Map → Custom label
- Settings → Custom label
- Debug → Custom label

### 3. Theme Color Management

- **Primary Color**: Main brand color used throughout the interface
- **Secondary Color**: Supporting color for secondary elements
- **Accent Color**: Highlight color for interactive elements

### 4. CSS Customization System

#### Component-Based Organization
CSS customizations are organized by component type:
- Header
- Navigation
- Dashboard
- Equipment
- Maintenance
- Calendar
- Map
- Settings
- Forms
- Tables
- Buttons
- Cards
- Modals
- Alerts
- Breadcrumbs
- Footer
- Global

#### Priority and Order System
- **Priority**: Higher priority CSS loads later (0-100 scale)
- **Order**: Within the same priority level, lower order numbers load first
- **Override Logic**: Higher priority CSS can override lower priority styles

#### Advanced Features
- **Syntax Highlighting**: CodeMirror integration for better code editing
- **Live Preview**: Real-time CSS testing
- **Validation**: Basic CSS syntax checking
- **Formatting**: Automatic CSS code formatting
- **Version Control**: Track who created each customization

## User Interface

### Main Branding Page (`/branding/`)

The main branding interface is organized into tabs:

#### 1. Basic Settings Tab
- Site information fields
- Logo and branding options
- Footer customization

#### 2. Navigation Labels Tab
- All navigation menu label fields
- Organized in logical groups

#### 3. Appearance Tab
- Color picker for theme colors
- Visual color selection interface

#### 4. CSS Customizations Tab
- List of existing CSS customizations
- Quick access to create, edit, and manage CSS
- Status indicators and metadata

#### 5. Live Preview Tab
- Real-time preview of branding changes
- Sample interface elements for testing
- Header, navigation, and footer previews

### CSS Management Interface

#### CSS Customization List (`/branding/css/`)
- Comprehensive list of all CSS customizations
- Filtering by type, status, and priority
- Search functionality
- Bulk management options

#### CSS Customization Form (`/branding/css/create/`, `/branding/css/<id>/edit/`)
- **CodeMirror Editor**: Professional code editing with syntax highlighting
- **Live Preview**: Real-time CSS testing
- **Validation Tools**: Syntax checking and formatting
- **Help System**: Built-in documentation and examples

#### CSS Preview & Testing (`/branding/css/preview/`)
- Side-by-side editor and preview
- Sample UI elements for testing
- Active CSS customization display
- Helpful examples and tips

## Technical Implementation

### Models

#### BrandingSettings
```python
class BrandingSettings(models.Model):
    site_name = models.CharField(max_length=200)
    site_tagline = models.CharField(max_length=300, blank=True)
    window_title_prefix = models.CharField(max_length=100, default="")
    window_title_suffix = models.CharField(max_length=100, default="")
    header_brand_text = models.CharField(max_length=200)
    # Navigation labels
    navigation_overview_label = models.CharField(max_length=50)
    # ... other navigation labels
    # Theme colors
    primary_color = models.CharField(max_length=7, default="#4299e1")
    secondary_color = models.CharField(max_length=7, default="#2d3748")
    accent_color = models.CharField(max_length=7, default="#3182ce")
    # Assets
    logo = models.ForeignKey(Logo, on_delete=models.SET_NULL, null=True, blank=True)
    favicon = models.ImageField(upload_to='favicons/', blank=True)
    is_active = models.BooleanField(default=True)
```

#### CSSCustomization
```python
class CSSCustomization(models.Model):
    name = models.CharField(max_length=100)
    item_type = models.CharField(max_length=20, choices=ITEM_TYPE_CHOICES)
    description = models.TextField(blank=True)
    css_code = models.TextField()
    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(default=0)
    order = models.IntegerField(default=0)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
```

### Context Processors

The `branding_processor` context processor provides branding data to all templates:
- Branding settings
- CSS customizations
- Navigation labels
- Theme colors
- Custom CSS code

### URL Structure

```
/branding/                          # Main branding page
/branding/css/                      # CSS customization list
/branding/css/create/               # Create new CSS customization
/branding/css/<id>/edit/            # Edit existing CSS customization
/branding/css/<id>/delete/          # Delete CSS customization
/branding/css/<id>/toggle/          # Toggle CSS customization status
/branding/css/preview/              # CSS preview and testing
```

## Usage Examples

### 1. Changing Site Colors

1. Navigate to **Settings → Branding → Appearance**
2. Use the color pickers to select new colors
3. Click **Save Appearance Settings**
4. Colors are applied immediately across the site

### 2. Customizing Navigation Labels

1. Navigate to **Settings → Branding → Navigation Labels**
2. Modify the labels for each navigation item
3. Click **Save Navigation Labels**
4. Changes appear in the navigation menu

### 3. Adding Custom CSS

1. Navigate to **Settings → Branding → CSS Customizations**
2. Click **Add CSS Customization**
3. Fill in the form:
   - **Name**: "Custom Button Styling"
   - **Item Type**: "Buttons"
   - **Description**: "Adds rounded corners to buttons"
   - **CSS Code**: Enter your CSS
   - **Priority**: 10
   - **Order**: 1
4. Use the **Preview** button to test your CSS
5. Click **Create CSS Customization**

### 4. CSS Examples

#### Enhanced Buttons
```css
.btn {
    border-radius: 20px;
    transition: all 0.3s ease;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
}
```

#### Custom Cards
```css
.card {
    border-radius: 16px;
    border: none;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
    transition: all 0.3s ease;
}

.card:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.15);
}
```

#### Form Improvements
```css
.form-control {
    border-radius: 12px;
    border: 2px solid var(--border-color);
    transition: all 0.2s ease;
}

.form-control:focus {
    border-color: var(--primary-color);
    box-shadow: 0 0 0 4px rgba(66, 153, 225, 0.1);
    transform: scale(1.02);
}
```

## Best Practices

### 1. CSS Organization
- Use specific selectors to avoid conflicts
- Group related styles together
- Use CSS variables when possible
- Comment your code for future reference

### 2. Priority Management
- Use low priority (0-30) for base styles
- Use medium priority (40-70) for component enhancements
- Use high priority (80-100) for overrides and fixes

### 3. Testing
- Always test CSS changes in the preview system
- Test on different screen sizes
- Verify that changes don't break existing functionality
- Use the validation tools before saving

### 4. Performance
- Keep CSS customizations focused and minimal
- Avoid overly complex selectors
- Use efficient CSS properties
- Monitor the impact of customizations

## Troubleshooting

### Common Issues

#### CSS Not Applying
1. Check if the customization is active
2. Verify the priority and order settings
3. Ensure CSS syntax is correct
4. Check browser console for errors

#### Conflicts with Existing Styles
1. Use more specific selectors
2. Increase the priority value
3. Use `!important` sparingly
4. Test in isolation first

#### Performance Issues
1. Review CSS complexity
2. Check for redundant rules
3. Optimize selectors
4. Consider consolidating customizations

### Debug Tools

- **CSS Preview**: Test CSS in real-time
- **Validation**: Check syntax before saving
- **Browser DevTools**: Inspect applied styles
- **Console Logs**: Check for JavaScript errors

## Security Considerations

### CSS Validation
- JavaScript execution is prevented in CSS customizations
- HTML tags are stripped from CSS input
- Basic syntax validation is performed
- User input is properly escaped

### Access Control
- Only authenticated users can access branding settings
- CSS customizations are tracked with user attribution
- Admin approval may be required for production changes

## Future Enhancements

### Planned Features
- **CSS Templates**: Pre-built CSS customization templates
- **Version History**: Track changes to branding settings
- **Approval Workflow**: Multi-stage approval for branding changes
- **A/B Testing**: Test different branding configurations
- **Export/Import**: Backup and restore branding settings

### Integration Opportunities
- **Design System**: Integration with external design systems
- **Theme Marketplace**: Share and download branding themes
- **Analytics**: Track the impact of branding changes
- **API Access**: Programmatic branding management

## Support and Resources

### Documentation
- This document provides comprehensive guidance
- Inline help is available throughout the interface
- Tooltips and examples are provided for all features

### Community
- Share CSS customizations with the community
- Get help from other users
- Contribute improvements and suggestions

### Technical Support
- For technical issues, contact the development team
- Bug reports should include detailed reproduction steps
- Feature requests are welcome and tracked

---

*This documentation is maintained by the Maintenance Dashboard development team. For questions or suggestions, please contact the team or submit an issue through the project repository.*
