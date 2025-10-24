# Breadcrumb Control System

The maintenance dashboard now includes a comprehensive breadcrumb control system that allows you to manage breadcrumb navigation globally and on individual pages.

## Features

### Global Breadcrumb Settings
- **Enable/Disable**: Turn breadcrumbs on or off globally
- **Customizable Text**: Change the "Home" text to anything you want
- **Custom Separator**: Use any character as the breadcrumb separator (e.g., `>`, `|`, `→`, `/`)
- **Color Customization**: Control link, text, and separator colors through branding

### Page-Level Control
- **Hide Breadcrumbs**: Disable breadcrumbs for specific pages
- **Show Breadcrumbs**: Explicitly enable breadcrumbs for specific pages
- **Custom Settings**: Override global settings for individual pages

## Usage

### Global Settings
Configure breadcrumb settings in **Settings → Branding → Basic Settings**:

1. **Breadcrumb Settings** section:
   - ✅ **Enable Breadcrumbs**: Global on/off switch
   - **Home Text**: Text for the home link (default: "Home")
   - **Separator**: Character between breadcrumb items (default: ">")

2. **Appearance** tab → **Breadcrumb Colors** section:
   - **Breadcrumb Link**: Color for clickable breadcrumb links
   - **Breadcrumb Text**: Color for non-clickable breadcrumb text
   - **Breadcrumb Separator**: Color for the separator character

### Page-Level Control

#### Hide Breadcrumbs on a Page
```html
{% load breadcrumb_controls %}
{% breadcrumb_control 'hide' %}

{% block content %}
<!-- Your page content here -->
{% endblock %}
```

#### Show Breadcrumbs on a Page
```html
{% load breadcrumb_controls %}
{% breadcrumb_control 'show' %}

{% block content %}
<!-- Your page content here -->
{% endblock %}
```

#### Custom Breadcrumb Settings for a Page
```html
{% load breadcrumb_controls %}
{% breadcrumb_control 'custom' home_text='Dashboard' separator='|' %}

{% block content %}
<!-- Your page content here -->
{% endblock %}
```

#### Custom Breadcrumb Content
```html
{% load breadcrumb_controls %}
{% breadcrumb_control 'show' %}

{% block breadcrumb %}
<li class="breadcrumb-item"><a href="{% url 'equipment:equipment_list' %}">Equipment</a></li>
<li class="breadcrumb-item active">{{ equipment.name }}</li>
{% endblock %}
```

## Examples

### Equipment Detail Page
```html
{% extends 'base.html' %}
{% load breadcrumb_controls %}

{% breadcrumb_control 'custom' home_text='Dashboard' separator='→' %}

{% block breadcrumb %}
<li class="breadcrumb-item"><a href="{% url 'equipment:equipment_list' %}">Equipment</a></li>
<li class="breadcrumb-item active">{{ equipment.name }}</li>
{% endblock %}
```

### Maintenance Calendar Page
```html
{% extends 'base.html' %}
{% load breadcrumb_controls %}

{% breadcrumb_control 'hide' %}

{% block content %}
<!-- Calendar content without breadcrumbs -->
{% endblock %}
```

### Settings Page with Custom Breadcrumbs
```html
{% extends 'base.html' %}
{% load breadcrumb_controls %}

{% breadcrumb_control 'custom' home_text='Main' separator='>' %}

{% block breadcrumb %}
<li class="breadcrumb-item"><a href="{% url 'core:settings' %}">Settings</a></li>
<li class="breadcrumb-item active">Branding</li>
{% endblock %}
```

## Template Tags Reference

### `{% breadcrumb_control %}`
Controls breadcrumb display for the current page.

**Parameters:**
- `action`: `'hide'`, `'show'`, or `'custom'`
- `home_text`: Custom text for home link (when action='custom')
- `separator`: Custom separator character (when action='custom')

**Examples:**
```html
{% breadcrumb_control 'hide' %}
{% breadcrumb_control 'show' %}
{% breadcrumb_control 'custom' home_text='Dashboard' separator='|' %}
```

### `{% get_breadcrumb_setting %}`
Gets a breadcrumb setting value with page-level override support.

**Parameters:**
- `setting_name`: Name of the setting (e.g., 'enabled', 'home_text', 'separator')

**Examples:**
```html
{% get_breadcrumb_setting 'enabled' %}
{% get_breadcrumb_setting 'home_text' %}
{% get_breadcrumb_setting 'separator' %}
```

## CSS Variables

The breadcrumb system uses CSS custom properties that can be customized:

```css
:root {
    --breadcrumb-link: #4299e1;      /* Link color */
    --breadcrumb-text: #a0aec0;      /* Text color */
    --breadcrumb-separator: #a0aec0; /* Separator color */
}
```

## Migration

After deploying, run the migration to add the new breadcrumb fields:

```bash
python manage.py migrate core
```

## Best Practices

1. **Use sparingly**: Only hide breadcrumbs when the page navigation is clear without them
2. **Consistent naming**: Use consistent breadcrumb text across related pages
3. **Clear hierarchy**: Ensure breadcrumbs show a logical path to the current page
4. **Accessibility**: Breadcrumbs help users understand their location in the site structure

## Troubleshooting

### Breadcrumbs not showing
- Check if `breadcrumb_enabled` is set to `True` in branding settings
- Verify the page doesn't have `{% breadcrumb_control 'hide' %}`
- Check that the page isn't the dashboard or calendar (these automatically hide breadcrumbs)

### Custom settings not working
- Ensure you're using `{% breadcrumb_control 'custom' %}` with the correct parameters
- Check that the template loads the `breadcrumb_controls` template tags
- Verify the parameter names match exactly (e.g., `home_text`, not `home_text`)

### Colors not applying
- Check that the breadcrumb color fields are set in branding settings
- Verify the CSS variables are being generated correctly
- Check browser developer tools for CSS variable values
