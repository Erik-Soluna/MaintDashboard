# Maintenance Categories Management Guide

This guide explains how to manage maintenance activity type categories and equipment categories in the Maintenance Dashboard system.

## Overview

The system now includes a comprehensive set of maintenance categories that go beyond basic "Preventative maintenance and inspections". These categories help organize and classify different types of maintenance activities for better planning, reporting, and analysis.

## Available Maintenance Categories

### Core Categories (Automatically Created)
1. **Preventive** - Regular maintenance to prevent equipment failure
2. **Corrective** - Repair and fix activities to restore equipment function
3. **Inspection** - Visual and testing checks to assess equipment condition
4. **Cleaning** - Cleaning and housekeeping activities
5. **Calibration** - Calibration and adjustment activities
6. **Testing** - Functional and performance testing

### Extended Categories (Automatically Created)
7. **Emergency** - Urgent repairs and emergency response activities
8. **Predictive** - Data-driven maintenance based on condition monitoring
9. **Condition-Based** - Maintenance triggered by equipment condition indicators
10. **Reliability-Centered** - Strategic maintenance planning for critical equipment
11. **Lubrication** - Oil changes, greasing, and lubrication activities
12. **Alignment** - Equipment alignment and balancing activities
13. **Overhaul** - Major equipment rebuilds and overhauls
14. **Installation** - New equipment installation and commissioning
15. **Decommissioning** - Equipment removal and decommissioning activities
16. **Training** - Maintenance training and skill development

## Managing Categories

### Through Django Admin Interface

1. **Access Admin**: Navigate to `/admin/` and log in with admin credentials
2. **Activity Type Categories**: Go to `Maintenance > Activity Type Categories`
3. **Equipment Categories**: Go to `Core > Equipment Categories`

#### Admin Features for Activity Type Categories:
- **Visual Preview**: See color swatches and icon previews
- **Bulk Actions**: 
  - Activate/Deactivate multiple categories
  - Duplicate categories for easy customization
- **Inline Editing**: Edit sort order and active status directly in the list
- **Advanced Filtering**: Filter by active status, creation date, and global flag

#### Admin Features for Equipment Categories:
- **Simple Management**: Add, edit, and deactivate equipment categories
- **Bulk Operations**: Manage multiple categories at once

### Through Command Line

#### Adding Maintenance Categories
```bash
# Basic category
python manage.py add_maintenance_category "Custom Category"

# With description
python manage.py add_maintenance_category "Custom Category" --description "Description here"

# With custom color and icon
python manage.py add_maintenance_category "Custom Category" \
    --description "Description here" \
    --color "#ff6b6b" \
    --icon "fas fa-cog" \
    --sort-order 100 \
    --active

# Set as global category
python manage.py add_maintenance_category "Global Category" --global
```

#### Adding Equipment Categories
```bash
# Basic equipment category
python manage.py add_equipment_category "Custom Equipment"

# With description and active status
python manage.py add_equipment_category "Custom Equipment" \
    --description "Description here" \
    --active
```

## Category Properties

### Activity Type Categories
- **Name**: Unique identifier for the category
- **Description**: Detailed explanation of the category's purpose
- **Color**: Hex color code for visual identification in dashboards
- **Icon**: FontAwesome icon class for visual representation
- **Sort Order**: Numerical order for display purposes
- **Active Status**: Whether the category is currently available
- **Global Flag**: Whether the category applies across all equipment types

### Equipment Categories
- **Name**: Unique identifier for the equipment type
- **Description**: Detailed explanation of the equipment category
- **Active Status**: Whether the category is currently available

## Best Practices

### Naming Conventions
- Use clear, descriptive names (e.g., "HVAC Maintenance" not "HVAC")
- Avoid abbreviations unless they're industry standard
- Keep names consistent with existing categories

### Color Selection
- Use contrasting colors for different categories
- Consider colorblind accessibility
- Maintain consistency with your organization's branding

### Icon Selection
- Choose FontAwesome icons that clearly represent the activity
- Keep icon usage consistent across similar categories
- Test icon visibility at different sizes

### Sort Order
- Use increments of 10 (10, 20, 30...) for easy insertion of new categories
- Keep related categories grouped together
- Reserve lower numbers for most commonly used categories

## Customization Examples

### Adding a Specialized Category
```bash
python manage.py add_maintenance_category "Safety Inspection" \
    --description "Safety-focused inspection activities including lockout/tagout verification" \
    --color "#dc3545" \
    --icon "fas fa-shield-alt" \
    --sort-order 25 \
    --active
```

### Adding Equipment-Specific Category
```bash
python manage.py add_equipment_category "Solar Panels" \
    --description "Photovoltaic solar panel systems and related equipment" \
    --active
```

## Troubleshooting

### Common Issues

1. **Category Not Appearing**: Check if the category is marked as active
2. **Color Not Displaying**: Verify the hex color code format (#RRGGBB)
3. **Icon Not Showing**: Ensure the FontAwesome icon class is correct
4. **Sort Order Issues**: Check for duplicate sort order values

### Validation Rules
- Category names must be unique
- Color codes must be valid hex format
- Icon classes must be valid FontAwesome classes
- Sort order should be a positive integer

## Advanced Features

### Global Categories
Global categories are available across all equipment types and are useful for:
- General maintenance activities
- Cross-equipment procedures
- Standard operating procedures

### Category Templates
Categories can be associated with templates that provide:
- Default duration estimates
- Required tools and parts
- Safety considerations
- Checklist templates

## Support

For additional help with category management:
1. Check the Django admin interface help text
2. Review the command line help: `python manage.py add_maintenance_category --help`
3. Consult the system documentation
4. Contact your system administrator
