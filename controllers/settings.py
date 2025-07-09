# controllers/settings.py
# -*- coding: utf-8 -*-
"""
Controller for application settings management.
"""

import logging
import uuid
from gluon.tools import redirect, URL, SQLFORM
from gluon import current

T = current.T

logging.basicConfig(level=logging.DEBUG)


@auth.requires_login()
@auth.requires_membership("admin")
def manage_settings():
    """Render the manage settings page with users and roles for the admin panel."""
    session._formkey = str(uuid.uuid4())  # Generate CSRF token
    users = db(db.auth_user).select()
    roles = db(db.auth_group).select()
    categories = db(db.equipment_category).select()  # Fetch categories
    locations = db(db.location).select()  # Fetch locations
    return dict(
        users=users,
        roles=roles,
        categories=categories,
        locations=locations,
        formkey=session._formkey,
    )


@auth.requires_membership("admin")
def add_category():
    """API to add a new equipment category with CSRF protection."""
    if request.post_vars.get("_formkey") != session._formkey:
        return response.json(
            {"status": "error", "message": "CSRF token missing or invalid"}
        )

    category_name = request.post_vars.get("category_name", "").strip()
    if not category_name:
        return response.json(
            {"status": "error", "message": "Category name is required"}
        )

    existing_category = (
        db(db.equipment_category.name == category_name).select().first()
    )
    if existing_category:
        return response.json(
            {"status": "error", "message": "Category already exists"}
        )

    try:
        db.equipment_category.insert(name=category_name)
        db.commit()
        logging.debug(f"Added category: {category_name}")
        return response.json({"status": "success"})
    except Exception as e:
        logging.error(f"Error adding category: {str(e)}")
        return response.json({"status": "error", "message": str(e)})


@auth.requires_membership("admin")
def delete_category():
    """API to delete an equipment category with CSRF protection."""
    if request.post_vars.get("_formkey") != session._formkey:
        return response.json(
            {"status": "error", "message": "CSRF token missing or invalid"}
        )

    category_id = request.post_vars.get("category_id")
    if not category_id:
        return response.json(
            {"status": "error", "message": "Category ID is required"}
        )

    if db(db.equipment.category == category_id).count():
        return response.json(
            {"status": "error", "message": "Cannot delete category in use"}
        )

    try:
        db(db.equipment_category.id == category_id).delete()
        db.commit()
        logging.debug(f"Deleted category ID: {category_id}")
        return response.json({"status": "success"})
    except Exception as e:
        logging.error(f"Error deleting category: {str(e)}")
        return response.json({"status": "error", "message": str(e)})


@auth.requires_membership("admin")
def add_location():
    """API to add a location (site or equipment) with CSRF protection."""
    if request.post_vars.get("_formkey") != session._formkey:
        return response.json(
            {"status": "error", "message": "CSRF token missing or invalid"}
        )

    location_name = request.post_vars.get("location_name", "").strip()
    parent_location_id = request.post_vars.get("parent_location_id")
    is_site = request.post_vars.get("is_site") == "true"  # Convert to boolean

    if not location_name:
        return response.json(
            {"status": "error", "message": "Location name is required"}
        )

    # Only Site Locations can have empty parent ID. Otherwise throw an error
    if is_site is False and not parent_location_id:
        return response.json(
            {
                "status": "error",
                "message": "Parent location must be defined for equipment location",
            }
        )

    try:
        db.location.insert(
            name=location_name, parent_location=parent_location_id, is_site=is_site
        )
        db.commit()
        logging.debug(
            f"Added location: {location_name}, Parent: {parent_location_id}, Is Site: {is_site}"
        )
        return response.json({"status": "success"})
    except Exception as e:
        logging.error(f"Error adding location: {str(e)}")
        return response.json({"status": "error", "message": str(e)})


@auth.requires_membership("admin")
def delete_location():
    """API to delete a location with CSRF protection."""
    if request.post_vars.get("_formkey") != session._formkey:
        return response.json(
            {"status": "error", "message": "CSRF token missing or invalid"}
        )

    location_id = request.post_vars.get("location_id")
    if not location_id:
        return response.json(
            {"status": "error", "message": "Location ID is required"}
        )

    if db(db.equipment.location == location_id).count():
        return response.json(
            {"status": "error", "message": "Cannot delete location in use"}
        )

    try:
        db(db.location.id == location_id).delete()
        db.commit()
        logging.debug(f"Deleted location ID: {location_id}")
        return response.json({"status": "success"})
    except Exception as e:
        logging.error(f"Error deleting location: {str(e)}")
        return response.json({"status": "error", "message": str(e)})


def manage_user_parameters():
    """Update user groupID based on form submissions."""
    if request.method == "POST":
        for key in request.vars:
            if key.startswith("groupID_"):
                user_id = key.split("_")[1]
                group_id = request.vars[key]
                try:
                    user = db.auth_user(user_id)
                    if user:
                        user.update_record(groupID=group_id)
                        db.commit()
                        session.flash = "User parameters updated successfully."
                    else:
                        session.flash = f"User with ID {user_id} not found."
                except Exception as e:
                    db.rollback()
                    session.flash = f"Error updating user: {str(e)}"
                    logging.exception("Error updating user parameters")
                    # Log the traceback to get detailed information

    redirect(URL("settings", "manage_settings", anchor="adminSettings"))


def bulk_delete_users():
    """Deletes multiple users based on checkbox selections."""
    if request.method == "POST":
        user_ids = request.vars.get("user_ids")
        if user_ids:
            try:
                # Ensure user_ids is a list
                if not isinstance(user_ids, list):
                    user_ids = [user_ids]

                # Convert user_ids to integers
                user_ids = [int(uid) for uid in user_ids]

                db(db.auth_user.id.belongs(user_ids)).delete()
                db.commit()
                session.flash = "Selected users deleted successfully."
            except Exception as e:
                db.rollback()
                session.flash = f"Error deleting users: {str(e)}"
                logging.exception("Error deleting users")  # Log the traceback

        else:
            session.flash = "No users selected for deletion."

    redirect(URL("settings", "manage_settings", anchor="adminSettings"))


def edit_user():
    """Edit a user in the auth_user table, or create a new user if user_id='new'."""
    user_id = request.args(0)

    if user_id == "new":
        # Handle creating a new user
        form = SQLFORM(
            db.auth_user,
            submit_button=T("Create User"),
            fields=["first_name", "last_name", "email", "username", "password"],
        )  # Include password field
        if form.process().accepted:
            # Create user using auth.register
            user_data = form.vars
            auth.register(
                user_data.email,  # Positional argument: email
                user_data.password,  # Positional argument: password
                first_name=user_data.first_name,
                last_name=user_data.last_name,
                username=user_data.username,
            )
            session.flash = T("User created")
            redirect(URL("settings", "manage_settings", anchor="adminSettings"))
        elif form.errors:
            response.flash = T("Form has errors")
    else:
        # Handle editing an existing user
        user = db.auth_user(user_id)
        if not user:
            session.flash = T("User not found.")
            redirect(URL("settings", "manage_settings", anchor="adminSettings"))

        form = SQLFORM(
            db.auth_user,
            user,
            deletable=False,
            fields=["first_name", "last_name", "email", "username"],
            submit_button=T("Update User"),
        )

        if form.process().accepted:
            session.flash = T("User updated")
            redirect(URL("settings", "manage_settings", anchor="adminSettings"))
        elif form.errors:
            response.flash = T("Form has errors")

    return dict(form=form)
