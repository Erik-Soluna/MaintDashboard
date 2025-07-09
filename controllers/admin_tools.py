# File: controllers/admin_tools.py
# -*- coding: utf-8 -*-
"""
Admin tools controller providing endpoints for managing user parameters,
bulk deletion of users, creating and editing users/roles, and populating the
database with sample data.
"""

import logging
import datetime
from gluon import response, request, redirect, URL, current, SQLFORM
T = current.T

logging.basicConfig(level=logging.DEBUG)

@auth.requires_membership('admin')
def manage_user_parameters():
    """Manage parameters for users."""
    users = db(db.auth_user).select()  # Fetch all users
    roles = db(db.auth_group).select()   # Fetch all roles

    if request.post_vars:
        user_id = request.post_vars.get('user_id')
        selected_roles = request.post_vars.getlist('roles')

        if not user_id or not selected_roles:
            return response.json({'status': 'error', 'message': 'Invalid user or roles'})

        # Remove existing role assignments for the user.
        db(db.auth_membership.user_id == int(user_id)).delete()

        for role_id in selected_roles:
            db.auth_membership.insert(user_id=int(user_id), group_id=int(role_id))

        db.commit()
        logging.debug(f"Updated roles for User ID {user_id}: {selected_roles}")
        session.flash = f"Roles updated successfully for User ID {user_id}."
        redirect(URL('admin_tools', 'manage_user_parameters'))

    return dict(users=users, roles=roles)

@auth.requires_membership('admin')
def bulk_delete_users():
    """Delete selected users."""
    user_ids = request.post_vars.getlist('user_ids')
    if not user_ids:
        return response.json({'status': 'error', 'message': 'No users selected for deletion'})

    # Prevent deletion of the current admin account.
    if str(auth.user_id) in user_ids:
        return response.json({'status': 'error', 'message': "Cannot delete your own account"})

    try:
        count = db(db.auth_user.id.belongs(user_ids)).delete()
        db.commit()
        logging.debug(f"Deleted users: {user_ids}")
        return response.json({'status': 'success', 'message': f"{count} user(s) deleted successfully."})
    except Exception as e:
        logging.error(f"Error deleting users: {str(e)}")
        return response.json({'status': 'error', 'message': str(e)})

@auth.requires_membership('admin')
def create_user():
    """Create a new user and assign them to the default user group (ID 2)."""
    try:
        user_id = db.auth_user.insert(
            first_name=request.post_vars.get('first_name'),
            last_name=request.post_vars.get('last_name'),
            email=request.post_vars.get('email'),
            password=db.auth_user.password.validate(request.post_vars.get('password'))[0]
        )
        db.commit()

        if not user_id:
            return response.json({'status': 'error', 'message': 'Failed to create user'})

        # Assign user to Default User Group (ID 2)
        db.auth_membership.insert(user_id=user_id, group_id=2)
        db.commit()

        logging.debug(f"Created user with ID: {user_id}")
        return response.json({'status': 'success', 'id': user_id})
    except Exception as e:
        import traceback
        error_message = traceback.format_exc()
        logging.error(f"Error in create_user: {error_message}")
        return response.json({'status': 'error', 'message': str(e), 'trace': error_message})

@auth.requires_membership('admin')
def edit_user():
    """Edit a specific user's details."""
    user_id = request.args(0, cast=int) or redirect(URL('admin_tools', 'manage_user_parameters'))
    form = SQLFORM(db.auth_user, user_id, showid=False)

    if form.process().accepted:
        logging.debug(f"User ID {user_id} updated successfully.")
        session.flash = "User updated successfully."
        redirect(URL('admin_tools', 'manage_user_parameters'))
    elif form.errors:
        response.flash = "There were errors in the form."

    return dict(form=form)

@auth.requires_membership('admin')
def update_user_role():
    """Admin function to update user roles."""
    user_id = request.post_vars.get('user_id')
    role_id = request.post_vars.get('role_id')

    if not user_id or not role_id:
        return response.json({'status': 'error', 'message': 'Invalid user or role'})

    existing_role = db((db.auth_membership.user_id == user_id) & 
                       (db.auth_membership.group_id == role_id)).select().first()

    if not existing_role:
        db.auth_membership.insert(user_id=user_id, group_id=role_id)
        db.commit()
        logging.debug(f"Added role {role_id} to user {user_id}")

    return response.json({'status': 'success'})

@auth.requires_membership('admin')
def remove_user_role():
    """Admin function to remove a user's role."""
    user_id = request.post_vars.get('user_id')
    role_id = request.post_vars.get('role_id')

    if not user_id or not role_id:
        return response.json({'status': 'error', 'message': 'Invalid user or role'})

    db((db.auth_membership.user_id == user_id) & 
       (db.auth_membership.group_id == role_id)).delete()
    db.commit()
    logging.debug(f"Removed role {role_id} from user {user_id}")

    return response.json({'status': 'success'})

@auth.requires_membership('admin')
def add_sample_data():
    """Populate the database with sample data."""
    try:
        # Ensure necessary categories exist
        categories = {
            'Transformers': None,
            'Power Meters': None
        }
        for category in categories:
            record = db(db.equipment_category.name == category).select().first()
            if record:
                categories[category] = record.id
            else:
                categories[category] = db.equipment_category.insert(name=category)
        
        # Ensure necessary locations exist
        locations = {
            'POD 1': None,
            'POD 2': None
        }
        for location in locations:
            record = db(db.equipment_location.name == location).select().first()
            if record:
                locations[location] = record.id
            else:
                locations[location] = db.equipment_location.insert(name=location)
        
        # Insert sample equipment if none exists already
        if not db(db.equipment).count():
            transformer_id = db.equipment.insert(
                name="Transformer 1",
                category=categories['Transformers'],
                equipment_location=locations['POD 1']
            )
            power_meter_id = db.equipment.insert(
                name="Power Meter 2",
                category=categories['Power Meters'],
                equipment_location=locations['POD 2']
            )

            # Insert sample maintenance tasks
            maintenance_id_1 = db.maintenance.insert(
                equipment_id=transformer_id,
                title="Transformer Oil Check",
                pm_designator="PM-001",
                description="Check the quality of oil in Transformer 1",
                required_status="De-energized"
            )
            maintenance_id_2 = db.maintenance.insert(
                equipment_id=power_meter_id,
                title="Power Meter Calibration",
                pm_designator="PM-002",
                description="Calibrate Power Meter 2",
                required_status="Energized"
            )

            # Insert sample schedules for the maintenance tasks
            db.schedule.insert(
                maintenance_id=maintenance_id_1,
                start_datetime=request.now,
                end_datetime=request.now + datetime.timedelta(hours=2)
            )
            db.schedule.insert(
                maintenance_id=maintenance_id_2,
                start_datetime=request.now + datetime.timedelta(days=1),
                end_datetime=request.now + datetime.timedelta(days=1, hours=3)
            )
            db.commit()
            logging.debug("Sample data added successfully.")
        
        session.flash = "Sample data added successfully!"
    except Exception as e:
        logging.error(f"Error adding sample data: {str(e)}")
        session.flash = "Error adding sample data."

    redirect(URL('admin_tools', 'dev_tools'))
