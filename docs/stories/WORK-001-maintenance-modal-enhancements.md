# WORK-001: Maintenance Modal and Priority System Enhancements

## Status: IMPLEMENTED

## Summary
This work order captures the UI/UX changes for the maintenance modal and the priority system overhaul as discussed in the committee review.

## Changes Implemented

### 1. Equipment Display Format
- **Change**: Equipment now displays in "Site | Location" format (e.g., "Site Name > POD Name > MDC Name")
- **Files Modified**: `templates/events/calendar.html`
- **Details**: The equipment checkboxes in the modal now show the hierarchical location path using `equipment.location.get_hierarchical_display` instead of just the equipment name

### 2. Modal Field Reordering
- **Change**: Activity Type and Equipment fields moved to the TOP of the modal
- **Files Modified**: `templates/events/calendar.html`
- **Details**: The modal form layout has been reorganized with Activity Type and Equipment as the first fields, followed by De-energization Required, Priority, Title, Notes, and Scheduling fields

### 3. Rename Description to Notes
- **Change**: "Description" field label changed to "Notes"
- **Files Modified**: `templates/events/calendar.html`
- **Details**: The field ID has been changed from `maintenanceDescription` to `maintenanceNotes` with label "Notes" and helpful placeholder text

### 4. Remove Status from Modal
- **Change**: Status field removed from visible form; new activities are forced to "Scheduled" status
- **Files Modified**: `templates/events/calendar.html`
- **Details**: Status is now a hidden field with value "scheduled" that gets submitted automatically

### 5. De-energization Required Field
- **Change**: New field added to indicate if de-energization is required
- **Files Modified**: 
  - `templates/events/calendar.html` (frontend)
  - `maintenance/models.py` (new field)
  - `maintenance/forms.py` (form field)
  - `maintenance/views.py` (API handler)
  - `maintenance/migrations/0012_add_deenergization_required.py` (migration)
- **Details**: Boolean field with TRUE/FALSE options, defaults to FALSE

### 6. Priority System Overhaul
- **Change**: Priority is now auto-assigned based on Activity Type
- **Files Modified**: `templates/events/calendar.html`
- **Details**: JavaScript mapping determines priority:
  - **Low Priority**:
    - Thermal Imaging
    - Operational Inspection
  - **Medium Priority**:
    - 3 Year Torque Check
    - Annual Torque Check
    - DGA Sample
  - **High Priority**:
    - Corrective Maintenance
  - **Default**: Medium priority if activity type not matched

### 7. Visual Inspection Removal
- **Note**: The "Visual Inspection" activity type should be removed from the database via admin panel or management command. This was not automated to avoid data migration issues.

## Technical Details

### Frontend Changes (calendar.html)
- Modal form restructured for better UX
- Auto-priority JavaScript function `setupPriorityAutoAssignment()` added
- Priority field is now disabled (read-only) and shows auto-assigned value
- Hidden priority field submits actual value

### Backend Changes
- New model field: `MaintenanceActivity.deenergization_required` (BooleanField, default=False)
- Form updated to include `deenergization_required` field
- API endpoint updated to handle the new field

### Database Migration
- Migration `0012_add_deenergization_required.py` adds the new field

## Acceptance Criteria
- [x] Equipment displays in "Site | Location" format
- [x] Activity Type and Equipment are at the top of the modal
- [x] Description renamed to Notes
- [x] Status field removed, forced to "Scheduled"
- [x] De-energization Required field added
- [x] Priority auto-assigns based on Activity Type
- [x] Backend supports all new fields

## Testing Notes
1. Open the calendar view
2. Click "Add" or click on a date to open the maintenance modal
3. Verify field ordering: Activity Type, Equipment, De-energization, Priority, Title, Notes, Scheduling
4. Select an Activity Type and verify priority auto-assigns
5. Verify equipment shows location path
6. Create a maintenance activity and verify it saves correctly

## Related PRs/Commits
- Branch: `cursor/maintenance-modal-priority-13e8`
