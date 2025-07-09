# File: controllers/events.py
# -*- coding: utf-8 -*-
"""
Controller for handling events, including calendar views, maintenance management,
and event fetching for calendar integrations.
"""

import logging
from gluon.tools import redirect, URL, SQLFORM
from gluon import current

T = current.T

logging.basicConfig(level=logging.DEBUG)


@auth.requires_login()
def calendar_view():
    """Render the calendar view page."""
    return dict()


@auth.requires_login()
def manage_events():
    """Retrieve maintenance records grouped by equipment category and
    load calendar data.
    """
    maintenance_records = db(db.maintenance).select(
        db.maintenance.id,
        db.maintenance.title,
        db.maintenance.description,
        db.maintenance.required_status,
        db.maintenance.equipment_id,
        db.equipment.name.with_alias("equipment_name"),
        db.equipment_category.name.with_alias("equipment_category"),
        left=[
            db.equipment.on(db.maintenance.equipment_id == db.equipment.id),
            db.equipment_category.on(db.equipment.category == db.equipment_category.id)
        ]
    )

    category_map = {}
    for m in maintenance_records:
        category = m.equipment_category or "Uncategorized"
        category_map.setdefault(category, []).append({
            'id': m.maintenance.id,
            'title': m.maintenance.title or "Untitled",
            'description': m.maintenance.description or "No description",
            'required_status': m.maintenance.required_status or "Unknown",
            'equipment_id': m.maintenance.equipment_id,
            'equipment_name': m.equipment_name or "Unknown Equipment"
        })

    equipment_list = db(db.equipment).select(db.equipment.id, db.equipment.name)
    return dict(maintenance_by_category=category_map,
                equipment_list=equipment_list)


@auth.requires_login()
def fetch_events():
    """Fetch maintenance schedules and calendar events for FullCalendar."""
    start_date = request.vars.get('start')
    end_date = request.vars.get('end')

    if not start_date or not end_date:
        return response.json(
            {'status': 'error', 'message': 'Invalid date range'}
        )

    # Query maintenance events within the given date range.
    maintenance_events = db(
        (db.maintenance.start_datetime >= start_date) &
        (db.maintenance.end_datetime <= end_date)
    ).select(
        db.maintenance.id,
        db.maintenance.title,
        db.maintenance.description,
        db.maintenance.start_datetime,
        db.maintenance.end_datetime,
        db.maintenance.equipment_id,
        left=[db.equipment.on(db.maintenance.equipment_id == db.equipment.id)]
    )

    # Convert maintenance events to FullCalendar JSON format.
    events = []
    for event in maintenance_events:
        events.append({
            'id': event.id,
            'title': event.title or "No Title",
            'start': event.start_datetime.strftime('%Y-%m-%dT%H:%M:%S')
            if event.start_datetime else None,
            'end': event.end_datetime.strftime('%Y-%m-%dT%H:%M:%S')
            if event.end_datetime else None,
            'description': event.description or "",
            'equipment_id': event.equipment_id
        })

    logging.debug(f"Fetched {len(events)} events.")
    return response.json(events)


@auth.requires_login()
def get_event():
    """Retrieve either a maintenance event or a calendar event."""
    event_id = request.vars.get('id')
    if not event_id:
        return response.json(
            {'status': 'error', 'message': 'No event ID provided'}
        )

    # Attempt to retrieve the event as a maintenance event.
    maintenance = db.maintenance(event_id)
    if maintenance:
        event_data = {
            'id': maintenance.id,
            'equipment_id': maintenance.equipment_id,
            'title': maintenance.title,
            'description': maintenance.description,
            'required_status': maintenance.required_status
        }
        return response.json({'status': 'success', 'event': event_data})

    # Attempt to retrieve the event as a schedule event.
    schedule = db(db.schedule.id == event_id).select(
        db.schedule.id,
        db.schedule.maintenance_id,
        db.schedule.start_datetime,
        db.schedule.end_datetime,
        limitby=(0, 1)
    ).first()

    if schedule:
        # Assuming schedule.maintenance_id returns a record with details.
        event_data = {
            'id': schedule.id,
            'title': schedule.maintenance_id.title
            if schedule.maintenance_id else "No Title",
            'start': schedule.start_datetime.strftime('%Y-%m-%dT%H:%M:%S')
            if schedule.start_datetime else None,
            'end': schedule.end_datetime.strftime('%Y-%m-%dT%H:%M:%S')
            if schedule.end_datetime else None,
            'description': schedule.maintenance_id.description
            if schedule.maintenance_id else "",
            'equipment_id': schedule.maintenance_id.equipment_id
            if schedule.maintenance_id else None
        }
        return response.json({'status': 'success', 'event': event_data})

    logging.warning(f"Event with ID {event_id} not found.")
    return response.json(
        {'status': 'error', 'message': 'Event not found'}
    )