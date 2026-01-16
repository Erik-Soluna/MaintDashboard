# Work Order: Maintenance Modal and Priority System Enhancements

## Work Order Information
- **Work Order ID**: WORK-001
- **Priority**: High
- **Status**: Ready for Development
- **Created**: 2026-01-16
- **PR Reference**: Committee Follow Up and Walk Thru of Maintenance Schedule to Completion

## Summary

This work order documents the requested changes from the committee review to improve the Maintenance Dashboard modal and priority system. Changes include UI/UX improvements to the maintenance activity modal and a complete overhaul of the priority system with automatic priority assignment based on activity types.

---

## Change Requests

### 1. Equipment Display Format Change

**Request**: Make equipment field display as "Site | Location"

**Current Behavior**: Equipment displays as equipment name only

**Desired Behavior**: Equipment field should display in format: `{Site} | {Location}`

**Technical Details**:
- Modify equipment dropdown/display in maintenance modal
- Use `equipment.get_site()` for Site name
- Use `equipment.location.name` or `equipment.get_full_location_path()` for Location
- Format: `Site Name | Location Name` (e.g., "Solar Farm A | Inverter Building")

**Files to Modify**:
- `maintenance/forms.py` - Update equipment field display
- `templates/maintenance/add_activity.html` - Update display format
- `templates/maintenance/edit_activity.html` - Update display format

**Acceptance Criteria**:
- [ ] Equipment dropdown shows "Site | Location" format
- [ ] Equipment display in activity detail shows "Site | Location" format
- [ ] Format is consistent across all maintenance views

---

### 2. Transformer List Fix - Production Deployment

**Request**: Ensure that Dev version is pushed to Production for Transformer list fix

**Action Required**: Verify and deploy the transformer list fix from development to production

**Technical Details**:
- Confirm transformer list fix is in current dev branch
- Ensure fix is included in PR merge
- Deploy to production after PR approval

**Acceptance Criteria**:
- [ ] Transformer list fix verified in dev branch
- [ ] Fix included in PR
- [ ] Production deployment completed

---

### 3. Modal Field Reordering

**Request**: Move Activity Type and Equipment to top of modal

**Current Order**:
1. Equipment
2. Activity Type
3. Title
4. Description
5. Status
6. Priority
7. ...

**Desired Order**:
1. **Activity Type** (moved to first position)
2. **Equipment** (moved to second position)
3. Title
4. Notes (renamed from Description)
5. Priority (status removed)
6. ...

**Technical Details**:
- Reorder fields in `MaintenanceActivityForm` crispy forms layout
- Update form field order in `maintenance/forms.py`

**Files to Modify**:
- `maintenance/forms.py` - Reorder Layout fields

**Acceptance Criteria**:
- [ ] Activity Type appears first in modal
- [ ] Equipment appears second in modal
- [ ] Field order is consistent in add and edit forms

---

### 4. Rename Description to Notes

**Request**: Change "Description" field label to "Notes" for clarity

**Current Label**: Description

**Desired Label**: Notes

**Technical Details**:
- Update field label in form
- Update help text if applicable
- Maintain database field name (no migration required)

**Files to Modify**:
- `maintenance/forms.py` - Update field label
- `maintenance/models.py` - Update help_text if desired

**Acceptance Criteria**:
- [ ] Field label shows "Notes" instead of "Description"
- [ ] Help text updated for clarity
- [ ] No database migration required

---

### 5. Remove Status from Modal - Force Scheduled Only

**Request**: Remove status field from the maintenance activity creation modal. All new activities should automatically be set to "Scheduled" status.

**Current Behavior**: User can select status (Scheduled, Pending, In Progress, etc.)

**Desired Behavior**: 
- Status field hidden from creation modal
- New activities automatically set to "Scheduled" status
- Status can only be changed through workflow actions (Complete, Cancel, etc.)

**Technical Details**:
- Remove `status` field from `MaintenanceActivityForm` fields
- Set default status to 'scheduled' in form save method
- Status changes should be done through dedicated actions/buttons

**Files to Modify**:
- `maintenance/forms.py` - Remove status from visible fields
- `maintenance/views.py` - Ensure status is set to 'scheduled' on creation

**Acceptance Criteria**:
- [ ] Status field not visible in add activity modal
- [ ] New activities automatically created with "Scheduled" status
- [ ] Existing status change workflows remain functional

---

### 6. Priority System Overhaul

**Request**: Complete overhaul of the priority system with automatic priority assignment and de-energization tracking.

#### 6.1 Add De-energization Required Field

**New Field**: `de_energization_required` (Boolean: TRUE/FALSE)

**Technical Details**:
- Add new field to `MaintenanceActivity` model
- Add checkbox to maintenance activity form
- Default value: FALSE

**Database Migration Required**: Yes

#### 6.2 Automatic Priority Assignment by Activity Type

**Activity Type to Priority Mapping**:

| Activity Type | Default Priority | De-energization Required |
|--------------|------------------|--------------------------|
| Thermal Imaging | Low | FALSE |
| Operational Inspection | Low | FALSE |
| Visual Inspection | **REMOVE** | N/A |
| Corrective Maintenance | High | TRUE |
| 3 Year Torque Check | Medium | TRUE |
| Annual Torque Check | Medium | TRUE |
| DGA Sample | Medium | TRUE |

**Technical Details**:
- Update `MaintenanceActivityType` model to include `default_priority` field
- Update `MaintenanceActivityType` model to include `default_de_energization_required` field
- Create data migration to set defaults for existing activity types
- Auto-populate priority when activity type is selected
- User can override if needed

#### 6.3 Updated Priority Status Labels

**New Priority Definitions**:

| Priority | Definition |
|----------|------------|
| **Low** | Maintenance not requiring de-energization |
| **Medium** | Maintenance requiring de-energization |
| **High** | Maintenance requiring de-energization AND required to have equipment functioning |
| **Critical** | Maintenance requiring de-energization AND required to have site operational |

**Technical Details**:
- Update `PRIORITY_CHOICES` help text in model
- Update priority field tooltips/help text in forms
- Consider adding priority definitions to UI tooltip

#### 6.4 Remove Visual Inspection Activity Type

**Request**: Remove "Visual Inspection" from activity types

**Technical Details**:
- Mark as inactive rather than delete (to preserve historical data)
- OR create data migration to remove if no existing activities use it

**Files to Modify**:
- `maintenance/models.py` - Add new fields
- `maintenance/forms.py` - Add de-energization field, update priority logic
- `maintenance/migrations/` - New migration for model changes
- `maintenance/management/commands/` - Update activity type creation commands
- `templates/maintenance/add_activity.html` - Add JavaScript for auto-priority
- `templates/maintenance/edit_activity.html` - Add JavaScript for auto-priority

**Acceptance Criteria**:
- [ ] De-energization Required field added to model
- [ ] De-energization Required checkbox in form
- [ ] Activity types have default priority and de-energization settings
- [ ] Priority auto-populates when activity type selected
- [ ] User can override auto-populated priority
- [ ] Priority definitions updated in UI
- [ ] Visual Inspection activity type removed/deactivated
- [ ] Existing data preserved

---

## Implementation Plan

### Phase 1: Model Changes (Database Migrations)

1. Add `de_energization_required` field to `MaintenanceActivity` model
2. Add `default_priority` field to `MaintenanceActivityType` model
3. Add `default_de_energization_required` field to `MaintenanceActivityType` model
4. Create and run migrations

### Phase 2: Data Migration

1. Create data migration to set activity type defaults:
   - Thermal Imaging: priority=low, de_energization=false
   - Operational Inspection: priority=low, de_energization=false
   - Corrective Maintenance: priority=high, de_energization=true
   - 3 Year Torque Check: priority=medium, de_energization=true
   - Annual Torque Check: priority=medium, de_energization=true
   - DGA Sample: priority=medium, de_energization=true
2. Deactivate Visual Inspection activity type

### Phase 3: Form Changes

1. Update `MaintenanceActivityForm`:
   - Reorder fields (Activity Type, Equipment first)
   - Rename Description to Notes
   - Remove Status field from creation form
   - Add De-energization Required field
2. Update form save logic to:
   - Default status to 'scheduled'
   - Auto-populate priority from activity type

### Phase 4: Template/JavaScript Changes

1. Update equipment display format to "Site | Location"
2. Add JavaScript to auto-populate priority when activity type changes
3. Update priority field help text/tooltips

### Phase 5: Testing

1. Test modal field ordering
2. Test auto-priority assignment
3. Test de-energization field
4. Test equipment display format
5. Test status defaults
6. Regression test existing functionality

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Data migration affects existing activities | Low | Medium | Use default values, preserve existing data |
| Priority changes confuse users | Medium | Low | Add tooltips explaining new definitions |
| Activity type removal breaks reports | Low | High | Deactivate instead of delete |

---

## Dependencies

- Django ORM for model changes
- Database migrations applied
- JavaScript for form interactivity
- Crispy Forms for form layout

---

## Notes

- All changes should maintain backward compatibility with existing data
- Consider adding user documentation for new priority definitions
- Future enhancement: Add priority color coding to calendar/list views

---

## Detailed Code Implementation Plan

### Overview

This section provides specific code changes required to implement the work order requirements.

---

### File: `maintenance/models.py`

#### Change 1: Add fields to MaintenanceActivityType

**Location**: After line ~127 (after `applicable_equipment_categories`)

```python
# Add these new fields to MaintenanceActivityType model
default_priority = models.CharField(
    max_length=10,
    choices=[
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ],
    default='medium',
    help_text="Default priority when this activity type is selected"
)
default_de_energization_required = models.BooleanField(
    default=False,
    help_text="Whether this activity type typically requires de-energization"
)
```

#### Change 2: Add de_energization_required to MaintenanceActivity

**Location**: After line ~184 (after `priority` field)

```python
# Add after priority field in MaintenanceActivity model
de_energization_required = models.BooleanField(
    default=False,
    help_text="Whether de-energization is required for this maintenance"
)
```

#### Change 3: Update PRIORITY_CHOICES help text

**Location**: Lines ~157-162

```python
PRIORITY_CHOICES = [
    ('low', 'Low - Maintenance not requiring de-energization'),
    ('medium', 'Medium - Maintenance requiring de-energization'),
    ('high', 'High - Requires de-energization and equipment functioning'),
    ('critical', 'Critical - Requires de-energization and site operational'),
]
```

---

### File: `maintenance/forms.py`

#### Change 1: Update Meta.fields to remove status and add de_energization_required

**Location**: Lines ~280-288 (MaintenanceActivityForm Meta class)

```python
class Meta:
    model = MaintenanceActivity
    fields = [
        'activity_type', 'equipment', 'title', 'description',  # Reordered
        'priority', 'de_energization_required', 'assigned_to',  # Status removed, de_energization added
        'scheduled_start', 'scheduled_end', 'timezone',
        'required_status', 'tools_required', 'parts_required',
        'safety_notes'
    ]
```

#### Change 2: Rename description label to "Notes"

**Location**: In `__init__` method, after `super().__init__(*args, **kwargs)`

```python
# Rename description field label to Notes
self.fields['description'].label = 'Notes'
self.fields['description'].help_text = 'Additional notes for this maintenance activity'
```

#### Change 3: Update crispy forms Layout for field ordering

**Location**: Lines ~702-755 (layout_fields definition)

```python
layout_fields = [
    Fieldset(
        'Activity Details',
        Row(
            Column('activity_type', css_class='form-group col-md-6 mb-0'),
            Column('equipment', css_class='form-group col-md-6 mb-0'),
        ),
        HTML('<div class="alert alert-info">' +
             '<strong>Quick Create:</strong> Can\'t find the activity type you need? ' +
             '<button type="button" class="btn btn-sm btn-outline-primary ms-2" onclick="toggleQuickCreate()">' +
             '<i class="fas fa-plus"></i> Create New</button>' +
             '</div>'),
        HTML('<div id="quick-create-fields" style="display: none;" class="border rounded p-3 mb-3 bg-light">' +
             '... existing quick create HTML ...' +
             '</div>'),
        'title',
        'description',  # Will show as "Notes" due to label change
        HTML('<div id="activity-suggestions" class="alert alert-info" style="display: none;"></div>')
    ),
    Fieldset(
        'Priority & Assignment',
        Row(
            Column('priority', css_class='form-group col-md-4 mb-0'),
            Column('de_energization_required', css_class='form-group col-md-4 mb-0'),
            Column('assigned_to', css_class='form-group col-md-4 mb-0'),
        ),
        HTML('<div class="priority-help-text small text-muted mt-2">' +
             '<strong>Priority Definitions:</strong><br>' +
             '• <strong>Low:</strong> Maintenance not requiring de-energization<br>' +
             '• <strong>Medium:</strong> Maintenance requiring de-energization<br>' +
             '• <strong>High:</strong> Requires de-energization + equipment must be functioning<br>' +
             '• <strong>Critical:</strong> Requires de-energization + site must be operational' +
             '</div>')
    ),
    # ... rest of fieldsets
]
```

#### Change 4: Update equipment display format to "Site | Location"

**Location**: In `__init__` method, after setting equipment queryset

```python
# Custom label for equipment to show "Site | Location"
class EquipmentChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        site = obj.get_site()
        site_name = site.name if site else "No Site"
        location_name = obj.location.name if obj.location else "No Location"
        return f"{site_name} | {location_name} - {obj.name}"

# Replace the standard equipment field
self.fields['equipment'] = EquipmentChoiceField(
    queryset=equipment_queryset.select_related('location', 'location__parent_location', 'category'),
    required=True,
    help_text="Select the equipment for this maintenance activity"
)
```

#### Change 5: Update save method to default status to 'scheduled'

**Location**: In `save` method

```python
def save(self, commit=True):
    instance = super().save(commit=False)
    
    # Force status to 'scheduled' for new activities
    if not instance.pk:
        instance.status = 'scheduled'
    
    # Auto-populate de_energization_required from activity type if not set
    if instance.activity_type and hasattr(instance.activity_type, 'default_de_energization_required'):
        if not self.cleaned_data.get('de_energization_required'):
            instance.de_energization_required = instance.activity_type.default_de_energization_required
    
    # ... rest of save method
```

---

### File: `templates/maintenance/add_activity.html`

#### Change 1: Add JavaScript for auto-priority based on activity type

**Location**: Add in the `<script>` section

```javascript
// Auto-populate priority and de-energization when activity type changes
document.addEventListener('DOMContentLoaded', function() {
    const activityTypeField = document.getElementById('id_activity_type');
    const priorityField = document.getElementById('id_priority');
    const deEnergizationField = document.getElementById('id_de_energization_required');
    
    // Activity type to default values mapping (populated from backend)
    const activityTypeDefaults = {
        {% for activity_type in activity_types %}
        '{{ activity_type.id }}': {
            'priority': '{{ activity_type.default_priority }}',
            'de_energization': {{ activity_type.default_de_energization_required|yesno:"true,false" }}
        },
        {% endfor %}
    };
    
    if (activityTypeField) {
        activityTypeField.addEventListener('change', function() {
            const selectedId = this.value;
            if (selectedId && activityTypeDefaults[selectedId]) {
                const defaults = activityTypeDefaults[selectedId];
                
                // Auto-set priority
                if (priorityField && !priorityField.dataset.userModified) {
                    priorityField.value = defaults.priority;
                }
                
                // Auto-set de-energization
                if (deEnergizationField && !deEnergizationField.dataset.userModified) {
                    deEnergizationField.checked = defaults.de_energization;
                }
            }
        });
        
        // Mark fields as user-modified when changed manually
        if (priorityField) {
            priorityField.addEventListener('change', function() {
                this.dataset.userModified = 'true';
            });
        }
        if (deEnergizationField) {
            deEnergizationField.addEventListener('change', function() {
                this.dataset.userModified = 'true';
            });
        }
    }
});
```

---

### File: `maintenance/views.py`

#### Change 1: Pass activity_types to template for JavaScript

**Location**: In `add_activity` view, add to context

```python
context = {
    # ... existing context
    'activity_types': MaintenanceActivityType.objects.filter(is_active=True).values(
        'id', 'default_priority', 'default_de_energization_required'
    ),
}
```

---

### Database Migration: `maintenance/migrations/00XX_add_priority_fields.py`

```python
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('maintenance', '0011_alter_maintenancetimelineentry_entry_type'),  # Update to latest
    ]

    operations = [
        # Add fields to MaintenanceActivityType
        migrations.AddField(
            model_name='maintenanceactivitytype',
            name='default_priority',
            field=models.CharField(
                choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical')],
                default='medium',
                help_text='Default priority when this activity type is selected',
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name='maintenanceactivitytype',
            name='default_de_energization_required',
            field=models.BooleanField(
                default=False,
                help_text='Whether this activity type typically requires de-energization',
            ),
        ),
        # Add field to MaintenanceActivity
        migrations.AddField(
            model_name='maintenanceactivity',
            name='de_energization_required',
            field=models.BooleanField(
                default=False,
                help_text='Whether de-energization is required for this maintenance',
            ),
        ),
    ]
```

---

### Data Migration: `maintenance/migrations/00XX_set_activity_type_defaults.py`

```python
from django.db import migrations

def set_activity_type_defaults(apps, schema_editor):
    MaintenanceActivityType = apps.get_model('maintenance', 'MaintenanceActivityType')
    
    # Define activity type defaults
    defaults = {
        'Thermal Imaging': {'priority': 'low', 'de_energization': False},
        'Operational Inspection': {'priority': 'low', 'de_energization': False},
        'Corrective Maintenance': {'priority': 'high', 'de_energization': True},
        '3 Year Torque Check': {'priority': 'medium', 'de_energization': True},
        'Annual Torque Check': {'priority': 'medium', 'de_energization': True},
        'DGA Sample': {'priority': 'medium', 'de_energization': True},
    }
    
    for name, values in defaults.items():
        MaintenanceActivityType.objects.filter(name__icontains=name).update(
            default_priority=values['priority'],
            default_de_energization_required=values['de_energization']
        )
    
    # Deactivate Visual Inspection
    MaintenanceActivityType.objects.filter(name__icontains='Visual Inspection').update(
        is_active=False
    )

def reverse_defaults(apps, schema_editor):
    # No-op for reverse
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('maintenance', '00XX_add_priority_fields'),  # Previous migration
    ]

    operations = [
        migrations.RunPython(set_activity_type_defaults, reverse_defaults),
    ]
```

---

### Equipment Queryset Fix: Ensure All Equipment Listed

The existing code in `maintenance/forms.py` uses site filtering that may exclude equipment. The fix ensures all active equipment is included:

**Current Issue**: The queryset uses `Q(location__parent_location=selected_site) | Q(location=selected_site)` which only goes one level deep.

**Fix Applied**: The `maintenance/views.py` already has `get_all_descendant_location_ids()` function that recursively gets all location IDs. We need to use this same approach in the form.

**Location**: `maintenance/forms.py`, lines ~630-665

```python
# Apply site filtering if a site is selected
if self.request and hasattr(self.request, 'session'):
    from core.models import Location
    from maintenance.views import get_all_descendant_location_ids
    
    selected_site_id = self.request.GET.get('site_id')
    if selected_site_id is None:
        selected_site_id = self.request.session.get('selected_site_id')
    
    if selected_site_id:
        if selected_site_id == 'all':
            # Handle "All Sites" selection - no filtering needed
            pass
        else:
            try:
                selected_site = Location.objects.get(id=selected_site_id, is_site=True)
                # Use recursive function to get ALL descendant locations
                location_ids = get_all_descendant_location_ids(selected_site, include_inactive=True)
                equipment_queryset = equipment_queryset.filter(location_id__in=location_ids)
            except (Location.DoesNotExist, ValueError):
                pass
```

---

### Summary of Files to Modify

| File | Changes |
|------|---------|
| `maintenance/models.py` | Add `default_priority`, `default_de_energization_required` to `MaintenanceActivityType`; Add `de_energization_required` to `MaintenanceActivity` |
| `maintenance/forms.py` | Reorder fields, rename Description to Notes, remove Status, add de_energization field, custom equipment label, fix equipment filtering |
| `maintenance/views.py` | Pass activity_types with defaults to template |
| `templates/maintenance/add_activity.html` | Add JavaScript for auto-priority |
| `templates/maintenance/edit_activity.html` | Add JavaScript for auto-priority |
| `maintenance/migrations/` | Two new migrations (schema + data) |

---

### Testing Checklist

1. **Equipment Listing**
   - [ ] All active equipment appears in dropdown regardless of site filter depth
   - [ ] Equipment displays as "Site | Location - Name" format
   - [ ] Equipment in nested locations (3+ levels deep) appears correctly

2. **Modal Field Order**
   - [ ] Activity Type appears first
   - [ ] Equipment appears second
   - [ ] Status field is NOT visible on create form
   - [ ] Description field shows as "Notes"

3. **Priority System**
   - [ ] Priority auto-populates when activity type selected
   - [ ] User can override auto-populated priority
   - [ ] De-energization Required checkbox appears and functions
   - [ ] Priority help text shows new definitions

4. **Status Behavior**
   - [ ] New activities created with "Scheduled" status automatically
   - [ ] Status can still be changed via dedicated workflows (Complete, Cancel, etc.)

5. **Data Integrity**
   - [ ] Existing activities not affected by migration
   - [ ] Visual Inspection activity type deactivated (not deleted)
   - [ ] Existing activities with Visual Inspection still visible
