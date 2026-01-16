# Modal Layout and Time Handling Documentation

This document answers the questions about the maintenance scheduling modal, how time is saved, and how events are recalled on the calendar.

---

## 1. Modal Layout Overview

### Current Modal Layout (Create Maintenance Modal)

The current "Create New Maintenance Activity" modal is located in `templates/events/calendar.html` (lines 954-1101) and has the following field layout:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Create New Maintenance Activity                       │
├─────────────────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────┬─────────────────────────────────────┐
│ │ Title *                         │ Priority *                          │
│ │ [________________________]      │ [Select Priority ▼]                 │
│ └─────────────────────────────────┤                                     │
│ ┌─────────────────────────────────┤ Status *                            │
│ │ Description                     │ [Select Status ▼]                   │
│ │ [________________________]      │                                     │
│ │ [________________________]      │                                     │
│ │ [________________________]      │                                     │
│ └─────────────────────────────────┴─────────────────────────────────────┘
│ ┌─────────────────────────────────┬─────────────────────────────────────┐
│ │ Scheduled Start *               │ Scheduled End *                     │
│ │ [datetime-local input]          │ [datetime-local input]              │
│ │                                 │                                     │
│ │ Timezone *                      │                                     │
│ │ [Central Time ▼]                │                                     │
│ └─────────────────────────────────┴─────────────────────────────────────┘
│ ┌─────────────────────────────────┬─────────────────────────────────────┐
│ │ Activity Type *                 │ Equipment *                         │
│ │ [Select Activity Type ▼]        │ ┌─────────────────────────────────┐ │
│ │                                 │ │ Category 1                      │ │
│ │                                 │ │ ☐ Equipment A                   │ │
│ │                                 │ │ ☐ Equipment B                   │ │
│ │                                 │ │ Category 2                      │ │
│ │                                 │ │ ☐ Equipment C                   │ │
│ │                                 │ └─────────────────────────────────┘ │
│ └─────────────────────────────────┴─────────────────────────────────────┘
│ ┌───────────────────────────────────────────────────────────────────────┐
│ │ Assigned To                                                           │
│ │ [________________________________]                                    │
│ └───────────────────────────────────────────────────────────────────────┘
├─────────────────────────────────────────────────────────────────────────┤
│                               [Cancel]  [Create Activity]               │
└─────────────────────────────────────────────────────────────────────────┘
```

### Proposed Modal Layout (Per WORK-001 Enhancements)

Based on the work order requirements, the modal will be reorganized:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Create New Maintenance Activity                       │
├─────────────────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────┬─────────────────────────────────────┐
│ │ Activity Type *                 │ Equipment *                         │
│ │ [Select Activity Type ▼]        │ [Site | Location display format]    │
│ │                                 │ ☐ Site A | Transformer Bay 1        │
│ │                                 │ ☐ Site B | Transformer Bay 2        │
│ └─────────────────────────────────┴─────────────────────────────────────┘
│ ┌─────────────────────────────────┬─────────────────────────────────────┐
│ │ Priority (Auto-set by Activity Type)                                  │
│ │ [Low/Medium/High/Critical] (read-only, based on activity type)        │
│ ├─────────────────────────────────┬─────────────────────────────────────┤
│ │ De-energization Required *      │                                     │
│ │ ○ Yes  ○ No                     │                                     │
│ └─────────────────────────────────┴─────────────────────────────────────┘
│ ┌─────────────────────────────────┬─────────────────────────────────────┐
│ │ Title *                         │                                     │
│ │ [Auto-generated or custom]      │                                     │
│ └─────────────────────────────────┴─────────────────────────────────────┘
│ ┌─────────────────────────────────┬─────────────────────────────────────┐
│ │ Scheduled Start *               │ Scheduled End *                     │
│ │ [datetime-local input]          │ [datetime-local input]              │
│ │                                 │                                     │
│ │ Timezone *                      │                                     │
│ │ [Central Time ▼]                │                                     │
│ └─────────────────────────────────┴─────────────────────────────────────┘
│ ┌───────────────────────────────────────────────────────────────────────┐
│ │ Notes (previously "Description")                                      │
│ │ [________________________]                                            │
│ │ [________________________]                                            │
│ └───────────────────────────────────────────────────────────────────────┘
│ ┌───────────────────────────────────────────────────────────────────────┐
│ │ Assigned To                                                           │
│ │ [________________________________]                                    │
│ └───────────────────────────────────────────────────────────────────────┘
├─────────────────────────────────────────────────────────────────────────┤
│ Note: Status is automatically set to "Scheduled" for new activities.    │
│                               [Cancel]  [Create Activity]               │
└─────────────────────────────────────────────────────────────────────────┘
```

**Key Changes:**
1. Activity Type and Equipment moved to TOP
2. Equipment displays as "Site | Location" format
3. Status field REMOVED (forced to "Scheduled")
4. "Description" renamed to "Notes"
5. Priority auto-set by Activity Type
6. New "De-energization Required" field added

---

## 2. How Time Is Saved in Scheduling

### Database Storage

Time is stored in the `MaintenanceActivity` model with these fields (from `maintenance/models.py`):

- **`scheduled_start`**: `DateTimeField` - The start datetime
- **`scheduled_end`**: `DateTimeField` - The end datetime  
- **`timezone`**: `CharField` - User's selected timezone (e.g., "America/Chicago")

### Time Saving Process

1. **User Input**: User selects datetime via `<input type="datetime-local">` widgets

2. **Timezone Conversion** (from `maintenance/forms.py` lines 371-388):
   ```python
   def _convert_to_timezone(self, naive_datetime, timezone_str):
       # Convert naive datetime to the specified timezone
       target_tz = pytz.timezone(timezone_str)
       # Use make_aware which properly handles DST transitions
       localized_dt = django_timezone.make_aware(naive_datetime, target_tz)
       # Convert to UTC for storage
       return localized_dt.astimezone(pytz.UTC)
   ```

3. **Storage**: All datetimes are **converted to UTC** before saving to the database

4. **API Submission** (from `maintenance/views.py` lines 479-489):
   ```python
   # Parse as naive datetime, then localize to user's timezone
   naive_dt = datetime.strptime(scheduled_start, '%Y-%m-%dT%H:%M')
   scheduled_start_dt = user_tz.localize(naive_dt)
   ```

### Example Flow:
```
User Input:     2026-01-20 09:00 (Central Time - America/Chicago)
                        ↓
Localization:   2026-01-20 09:00 CST (timezone-aware)
                        ↓
UTC Conversion: 2026-01-20 15:00 UTC
                        ↓
Database:       Stored as 2026-01-20 15:00 UTC with timezone="America/Chicago"
```

---

## 3. How Time Is Recalled on Calendar Events

### Calendar Event Fetching

The calendar uses FullCalendar and fetches events from the API endpoint `events:fetch_unified_events`.

### Time Display Process

1. **Database Query** (from `maintenance/views.py` lines 2569-2604):
   ```python
   # Convert datetimes to the activity's timezone for display
   scheduled_start_utc = activity.scheduled_start.astimezone(pytz.UTC)
   scheduled_end_utc = activity.scheduled_end.astimezone(pytz.UTC)
   ```

2. **API Response**:
   ```json
   {
       "id": "maint_123",
       "title": "Thermal Imaging - Site A",
       "start": "2026-01-20T15:00:00+00:00",
       "end": "2026-01-20T18:00:00+00:00",
       "scheduled_start": "2026-01-20T15:00:00+00:00",
       "scheduled_end": "2026-01-20T18:00:00+00:00"
   }
   ```

3. **FullCalendar Configuration** (from `templates/events/calendar.html` lines 1189-1195):
   ```javascript
   // Get user's timezone from profile (passed from server)
   const userTimezone = '{{ user_timezone|default:"America/Chicago" }}';
   
   var calendar = new FullCalendar.Calendar(calendarEl, {
       timeZone: userTimezone, // Use user's profile timezone
       // ...
   });
   ```

4. **Display Conversion**: FullCalendar automatically converts UTC times to the user's configured timezone

### Calendar Event Click → Modal Display

When a user clicks an event on the calendar:

1. **Event Click Handler** (line 1255-1291):
   ```javascript
   eventClick: function(info) {
       // Extract activity ID
       const actualActivityId = info.event.id.replace('maint_', '');
       // Open maintenance details modal
       openMaintenanceModal(actualActivityId);
   }
   ```

2. **Modal Data Loading** fetches activity details including:
   - Scheduled start/end times (displayed in user's timezone)
   - Status, Priority, Equipment info
   - Notes/Description

### Example Flow (Recall):
```
Database:        2026-01-20 15:00 UTC
                        ↓
API Response:    2026-01-20T15:00:00+00:00 (ISO format with UTC offset)
                        ↓
FullCalendar:    Converts to user's timezone (America/Chicago)
                        ↓
Calendar Display: Shows as 2026-01-20 09:00 AM CST
                        ↓
Modal Click:     Displays "Scheduled Start: 01/20/2026 9:00 AM CST"
```

---

## Summary

| Aspect | Implementation |
|--------|---------------|
| **Modal Layout** | Two-column form with Activity Type/Equipment at top (after WORK-001) |
| **Time Input** | HTML5 `datetime-local` inputs |
| **Time Storage** | All times converted to UTC, original timezone stored separately |
| **Time Display** | Converted back to user's profile timezone via FullCalendar |
| **Calendar Integration** | FullCalendar handles timezone conversion automatically |
| **Modal Recall** | Click event → Fetch activity details → Display in user's timezone |

---

## Files Involved

- **Modal Template**: `templates/events/calendar.html` (lines 954-1101)
- **Form Processing**: `maintenance/forms.py` (MaintenanceActivityForm class)
- **API Endpoint**: `maintenance/views.py` (create_maintenance_activity, fetch_unified_events)
- **Model**: `maintenance/models.py` (MaintenanceActivity class)
- **Calendar JS**: `templates/events/calendar.html` (JavaScript section starting line 1142)
