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
