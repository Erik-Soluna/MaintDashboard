# Equipment Conditional Fields Feature

## Overview

The Equipment Conditional Fields feature allows you to make fields from one equipment category available to other categories. This is particularly useful for power-related equipment that shares common characteristics, such as transformers and switchgear that both need oil type information.

## Key Features

- **Cross-Category Field Sharing**: Make fields from one category available to other categories
- **Field Overrides**: Customize field labels, help text, requirements, and other properties for the target category
- **User-Friendly Management**: Web interface for managing conditional field assignments
- **Dynamic Forms**: Equipment forms automatically include conditional fields based on category
- **Visual Indicators**: Conditional fields are clearly marked in forms with source category information

## Use Cases

### Example: Oil Type for Power Equipment

**Scenario**: You have "Transformers" and "Switchgear" equipment categories. Transformers have an "Oil Type" field, but some switchgear equipment also uses oil and needs this field.

**Solution**: Create a conditional field assignment that makes the "Oil Type" field from "Transformers" available to "Switchgear" equipment, optionally renaming it to "Insulating Medium Type" for clarity.

### Example: Protection Relay Information

**Scenario**: Protection relays need to know about the circuit breakers they control, and transformers need to know about their protection relays.

**Solution**: Create bidirectional conditional field assignments:
- "Breaker Type" from "Switchgear" → "Protection" (as "Associated Breaker Type")
- "Relay Type" from "Protection" → "Transformers" (as "Protection Relay Type")

## How It Works

### 1. Field Assignment Process

1. **Source Category**: The category that originally defines the field
2. **Target Category**: The category that will receive access to the field
3. **Field**: The specific field to be shared
4. **Overrides**: Optional customizations for the target category

### 2. Form Integration

When creating or editing equipment:
- The system checks the equipment's category
- It includes both native fields (from the category itself) and conditional fields (assigned from other categories)
- Conditional fields are marked with a visual indicator showing their source category
- Field properties (labels, help text, etc.) can be overridden for the target category

### 3. Data Storage

- Conditional field values are stored using the same `EquipmentCustomValue` model
- The system automatically determines whether a field is native or conditional when saving
- Values are preserved even if conditional field assignments are later removed

## Management Interface

### Accessing Conditional Fields Settings

1. Go to **Settings** → **Equipment Items** → **Conditional Fields**
2. Or navigate directly to `/equipment-conditional-fields/settings/`

### Creating Conditional Field Assignments

1. Click **"Add Conditional Field"**
2. Select the **Source Category** (provides the field)
3. Select the **Target Category** (receives the field)
4. Choose the **Field** to assign
5. Optionally configure field overrides
6. Click **"Create Assignment"**

### Managing Existing Assignments

- **Enable/Disable**: Toggle assignments on/off without deleting them
- **Edit**: Modify field overrides through the admin interface
- **Remove**: Delete assignments (doesn't affect existing data)

## Technical Implementation

### Models

#### EquipmentCategoryConditionalField
```python
class EquipmentCategoryConditionalField(TimeStampedModel):
    source_category = models.ForeignKey(EquipmentCategory, ...)
    target_category = models.ForeignKey(EquipmentCategory, ...)
    field = models.ForeignKey(EquipmentCategoryField, ...)
    is_active = models.BooleanField(default=True)
    
    # Override fields
    override_label = models.CharField(max_length=200, blank=True)
    override_help_text = models.TextField(blank=True)
    override_required = models.BooleanField(null=True, blank=True)
    override_default_value = models.TextField(blank=True)
    override_sort_order = models.PositiveIntegerField(null=True, blank=True)
    override_field_group = models.CharField(max_length=100, blank=True)
```

### Equipment Model Methods

```python
def get_conditional_fields(self):
    """Get conditional fields assigned to this equipment's category."""

def get_all_custom_fields(self):
    """Get both native and conditional custom fields for this equipment."""

def get_conditional_value(self, field_name):
    """Get the value of a conditional field by name."""

def set_conditional_value(self, field_name, value):
    """Set the value of a conditional field by name."""
```

### Form Integration

The `DynamicEquipmentForm` automatically includes conditional fields:
- Detects conditional field assignments for the selected category
- Applies field overrides (labels, help text, etc.)
- Shows visual indicators for conditional fields
- Handles saving both native and conditional field values

## Setup and Configuration

### Initial Setup

1. **Run Migration**: Apply the database migration for the new model
   ```bash
   python manage.py migrate equipment
   ```

2. **Create Example Data** (Optional): Set up demonstration conditional fields
   ```bash
   python manage.py setup_conditional_fields_example
   ```

3. **Access Management Interface**: Navigate to the conditional fields settings page

### Creating Your First Conditional Field

1. **Create Source Fields**: First, create custom fields in the source category
2. **Create Assignment**: Use the management interface to assign fields to target categories
3. **Configure Overrides**: Optionally customize field properties for the target category
4. **Test**: Create equipment in the target category to verify the conditional field appears

## Best Practices

### Field Naming
- Use clear, descriptive field names in the source category
- Consider using override labels to make fields more contextually appropriate for target categories
- Example: "Oil Type" → "Insulating Medium Type" for switchgear

### Category Organization
- Group related equipment types together
- Consider the logical relationships between equipment categories
- Avoid creating circular dependencies between categories

### Field Overrides
- Use override labels to make fields more relevant to the target category
- Adjust required/optional status based on the target category's needs
- Organize fields into appropriate groups for better form layout

### Maintenance
- Regularly review conditional field assignments
- Remove assignments that are no longer needed
- Consider the impact on existing equipment when modifying assignments

## Troubleshooting

### Common Issues

1. **Field Not Appearing**: Check that the conditional field assignment is active
2. **Data Loss**: Conditional field values are preserved even if assignments are removed
3. **Form Errors**: Ensure field overrides are valid (e.g., required fields have valid choices)

### Debugging

- Check the conditional fields settings page for assignment status
- Verify field assignments in the Django admin interface
- Review equipment form logs for any field-related errors

## Future Enhancements

### Planned Features
- **Bulk Assignment**: Assign multiple fields at once
- **Field Templates**: Predefined field sets for common equipment types
- **Advanced Validation**: Cross-field validation rules
- **Import/Export**: Bulk management of conditional field assignments

### API Integration
- REST API endpoints for conditional field management
- Integration with external equipment management systems
- Automated field assignment based on equipment specifications

## Conclusion

The Equipment Conditional Fields feature provides a flexible and powerful way to share field definitions between equipment categories while maintaining data integrity and user experience. This feature is particularly valuable for power systems and other industries where equipment types share common characteristics but are organized into different categories for management purposes.
