# -*- coding: utf-8 -*-

"""Controller for equipment management."""

import logging
import json  # Import the json module
import traceback
from datetime import datetime
from gluon import current

T = current.T

logging.basicConfig(level=logging.DEBUG)


def _get_equipment_data(equipment_id=None, as_dict=False, query=None):
    """
    Helper function to retrieve equipment data with related information.

    Args:
        equipment_id (int, optional): The ID of the equipment to retrieve.
            Defaults to None.
        as_dict (bool, optional): Whether to return the data as a list of
            dictionaries. Defaults to None.
        query (SQLQuery, optional): An optional SQL query to filter the
            results. Defaults to None.

    Returns:
        list: A list of equipment records or a list of dictionaries.
    """
    if query is None:
        query = db.equipment

    if equipment_id:
        query = (db.equipment.id == equipment_id) & query

    equipment_records = db(query).select()

    if as_dict:
        equipment_list = []
        for eq in equipment_records:
            eq_dict = eq.as_dict()
            for key, value in eq_dict.items():
                if isinstance(value, datetime):
                    eq_dict[key] = value.isoformat()
            equipment_list.append(eq_dict)
        return equipment_list
    else:
        return equipment_records


@auth.requires_login()
def manage_equipment():
    """Render the manage equipment page with related data."""
    # Actually fetch equipment data instead of returning an empty list
    equipment_list = _get_equipment_data(as_dict=True)
    fields = ['name', 'category', 'manufacturer_serial', 'location']  # A simplified list
    field_labels = {
        'name': 'Equipment Name',
        'category': 'Category',
        'manufacturer_serial': 'Serial',
        'location': 'Location'
    }

    return dict(
        equipment_list=equipment_list,
        fields=fields,
        field_labels=field_labels,
        json=json,
    )


@auth.requires_login()
def search_equipment():
    """Search for equipment based on a search term."""
    search_term = request.vars.get('search_term')
    if not search_term:
        return response.json(
            {'status': 'error', 'message': 'No search term provided'}
        )

    # Build the search query
    query = (db.equipment.name.contains(search_term)) | (
        db.equipment.manufacturer_serial.contains(search_term)
    ) | (
        db.equipment.soluna_asset_tag.contains(search_term)
    )  # Add more fields as needed

    equipment_list = _get_equipment_data(query=query, as_dict=True)

    return response.json({'status': 'success', 'equipment': equipment_list})


@auth.requires_login()
def details():
    """Display details for a specific equipment."""
    equipment_id = request.args(0)  # Get the equipment ID from the URL
    if not equipment_id:
        session.flash = 'No equipment ID provided'
        redirect(URL('equipment', 'manage_equipment'))

    equipment = db(db.equipment.id == equipment_id).select().first()
    if not equipment:
        session.flash = 'Equipment not found'
        redirect(URL('equipment', 'manage_equipment'))

    # Fetch the Equipment Category information
    equipment_category = (
        db.equipment_category[equipment.category] if equipment.category else None
    )

    # If JSON format is requested (for AJAX), return JSON
    if request.extension == 'json':
        equipment_data = equipment.as_dict()
        # Convert datetime objects to strings before passing to JSON
        for key, value in equipment_data.items():
            if isinstance(value, datetime):
                equipment_data[key] = value.isoformat()

        # Include equipment_category name if available
        equipment_data['category_name'] = (
            equipment_category.name if equipment_category else None
        )
        return response.json({'status': 'success', 'equipment': equipment_data})

    # Get equipment_maintenance_schedule only when not requesting JSON
    #maintenance_schedule = get_equipment_maintenance_schedule(equipment_id) # REMOVE LINE

    return dict(
        equipment=equipment,
        #maintenance_schedule=maintenance_schedule, # REMOVE LINE
        equipment_category=equipment_category,
    )


@auth.requires_login()
def details_dev():
    """Display details for a specific equipment."""
    equipment_id = request.args(0)  # Get the equipment ID from the URL
    if not equipment_id:
        session.flash = 'No equipment ID provided'
        redirect(URL('equipment', 'manage_equipment'))

    equipment = db(db.equipment.id == equipment_id).select().first()
    if not equipment:
        session.flash = 'Equipment not found'
        redirect(URL('equipment', 'manage_equipment'))

    # Fetch the Equipment Category information
    equipment_category = (
        db.equipment_category[equipment.category] if equipment.category else None
    )

    # If JSON format is requested (for AJAX), return JSON
    if request.extension == 'json':
        equipment_data = equipment.as_dict()
        # Convert datetime objects to strings before passing to JSON
        for key, value in equipment_data.items():
            if isinstance(value, datetime):
                equipment_data[key] = value.isoformat()

        # Include equipment_category name if available
        equipment_data['category_name'] = (
            equipment_category.name if equipment_category else None
        )
        return response.json({'status': 'success', 'equipment': equipment_data})

    # Get equipment_maintenance_schedule only when not requesting JSON
    #maintenance_schedule = get_equipment_maintenance_schedule(equipment_id)

    return dict(
        equipment=equipment,
        #maintenance_schedule=maintenance_schedule,
        equipment_category=equipment_category,
    )


@auth.requires_login()
def get_equipment_data():
    """AJAX endpoint to get equipment data with pagination."""
    try:
        page = int(request.vars.page or 1)
        items_per_page = int(request.vars.items_per_page or 20)
        search_term = request.vars.search_term or ''

        # Calculate offset
        offset = (page - 1) * items_per_page

        # Build query
        query = db.equipment
        if search_term:
            query = (db.equipment.name.contains(search_term)) | (
                db.equipment.manufacturer_serial.contains(search_term)
            ) | (db.equipment.soluna_asset_tag.contains(search_term))

        # Count total records for pagination
        total_records = db(query).count()
        total_pages = (total_records + items_per_page - 1) // items_per_page

        # Get records with pagination
        records = db(query).select(
            limitby=(offset, offset + items_per_page), orderby=db.equipment.name
        )

        # Convert records to dictionaries with related information
        equipment_list = []
        for record in records:
            item = record.as_dict()
            # Add related information
            if record.category:
                item['category_name'] = db.equipment_category[record.category].name
            if record.location:
                item['location_name'] = db.location[record.location].name
            equipment_list.append(item)

        return response.json(
            {
                'status': 'success',
                'equipment': equipment_list,
                'pagination': {
                    'total_records': total_records,
                    'total_pages': total_pages,
                    'current_page': page,
                    'items_per_page': items_per_page,
                },
            }
        )
    except Exception as e:
        logging.error(f"Error in get_equipment_data: {str(e)}")
        logging.error(traceback.format_exc())
        return response.json(
            {
                'status': 'error',
                'message': f'Failed to retrieve equipment data: {str(e)}',
            }
        )


@auth.requires_login()
def add_equipment():
    """Display a custom form for adding new equipment."""
    categories = db(db.equipment_category).select()
    locations = db(db.location).select()

    if request.method == 'POST':
        # Process the form submission
        equipment_name = request.vars.name
        category_id = request.vars.category
        manufacturer_serial = request.vars.manufacturer_serial
        soluna_asset_tag = request.vars.soluna_asset_tag
        location_id = request.vars.location
        datasheet = request.vars.datasheet
        warranty_details = request.vars.warranty_details
        installed_upgrades = request.vars.installed_upgrades
        power_ratings = request.vars.power_ratings
        trip_setpoints = request.vars.trip_setpoints
        schematics = request.vars.schematics
        dga_due = request.vars.dga_due
        item_due_date = request.vars.item_due_date
        active_items = request.vars.active_items
        item_status = request.vars.item_status

        try:
            # Insert the new equipment record into the database
            db.equipment.insert(
                name=equipment_name,
                category=category_id,
                manufacturer_serial=manufacturer_serial,
                soluna_asset_tag=soluna_asset_tag,
                location=location_id,
                datasheet=datasheet,
                warranty_details=warranty_details,
                installed_upgrades=installed_upgrades,
                power_ratings=power_ratings,
                trip_setpoints=trip_setpoints,
                schematics=schematics,
                dga_due=dga_due,
                item_due_date=item_due_date,
                active_items=active_items,
                item_status=item_status,
            )
            db.commit()
            session.flash = 'Equipment added successfully!'
            redirect(URL('equipment', 'manage_equipment'))

        except Exception as e:
            db.rollback()
            logging.error(f'Error adding equipment: {str(e)}')
            session.flash = f'Error adding equipment: {str(e)}'

    return dict(categories=categories, locations=locations) # ADD THE VARIABLES


@auth.requires_login()
def delete_equipment():
    """AJAX endpoint to delete equipment."""
    try:
        equipment_id = request.vars.id

        if not equipment_id:
            return response.json(
                {'status': 'error', 'message': 'No equipment ID provided'}
            )

        db(db.equipment.id == equipment_id).delete()
        db.commit()
        return response.json(
            {'status': 'success', 'message': 'Equipment deleted successfully'}
        )
    except Exception as e:
        db.rollback()
        logging.error(f"Error in delete_equipment: {str(e)}")
        logging.error(traceback.format_exc())
        return response.json(
            {'status': 'error', 'message': f'Error deleting equipment: {str(e)}'}
        )


def get_equipment_maintenance_schedule(equipment_id):
    """Return a list of required maintenance activities for the given equipment."""
    schedule = []
    # Ensure a valid equipment_id to prevent key errors
    equipment = db.equipment[equipment_id]
    if equipment:
        activities = [
            {'activity': 'T-A-1'},
            {'activity': 'T-A-2'},
            {'activity': 'T-R/A-3'},
        ]  # Define your activities here - hardcoded for this model

        for activity in activities:
            # Query for any events. The database has fields 'equipment_id',
            # 'activity_type', 'date' where equipment_id is the id of the
            # equipment and activity is the activity type. Date would
            # determine if it falls under 'last_completed' or 'upcoming'
            equipment_events = db(
                (db.calendar_event.equipment_id == equipment_id)
                # & (db.calendar_event.activity_type == activity['activity']) # REMOVED THIS LINE
            ).select(
                orderby=db.calendar_event.date
            )  # type: ignore

            # Assign the calendar entries for that activity.
            last_completed = None
            upcoming = None
            for equipment_event in equipment_events:
                if equipment_event.date < datetime.now().date():
                    last_completed = equipment_event.date.strftime('%m-%d-%Y')
                else:
                    upcoming = equipment_event.date.strftime('%m-%d-%Y')
                    break  # Only take the immediate future entry

            # Assign the entries and calendar entries
            activity['last_completed'] = (
                last_completed if last_completed is not None else "N/A"
            )
            activity['upcoming'] = upcoming if upcoming is not None else "N/A"
            schedule.append(activity)
    return schedule
