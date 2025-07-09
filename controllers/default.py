# -*- coding: utf-8 -*-
"""
Default controller providing the Dashboard, user authentication, and functions to
manage alerts, attachments, logs, and site filtering.
"""

import logging
from gluon import redirect, URL, current, SQLFORM
# Retrieve T from the current object.
T = current.T

logging.basicConfig(level=logging.DEBUG)

def index():
    """Dashboard landing page."""
    if not auth.user:
        redirect(URL('user', args='login'))
    
    # Fetch all site locations from the database to always display the locations
    sites = db(db.site_location).select()
    
    return dict(message="Welcome to the Maintenance Management System!", sites=sites)

def user():
    """Handles authentication (login, logout, register, etc.)."""
    # Fetch all site locations from the database to always display the locations
    sites = db(db.site_location).select()

    return dict(form=auth(), sites=sites)

@auth.requires_login()
def manage_alerts():
    """Manage alerts with a CRUD interface."""
     # Fetch all site locations from the database to always display the locations
    sites = db(db.site_location).select()

    grid = SQLFORM.grid(db.alerts,
                        create=True, editable=True, deletable=True, csv=True)
    return dict(grid=grid, sites=sites)

@auth.requires_login()
def manage_attachments():
    """Manage equipment attachments with a CRUD interface."""
     # Fetch all site locations from the database to always display the locations
    sites = db(db.site_location).select()

    grid = SQLFORM.grid(db.attachments,
                        create=True, editable=True, deletable=True, csv=True)
    return dict(grid=grid, sites=sites)

@auth.requires_login()
def manage_action_logs():
    """View action logs (read-only)."""
     # Fetch all site locations from the database to always display the locations
    sites = db(db.site_location).select()

    grid = SQLFORM.grid(db.action_logs, create=False, editable=False,
                        deletable=False, csv=True)
    return dict(grid=grid, sites=sites)

@auth.requires_login()
def set_site_filter():
    """Set the selected site location as the active session filter."""
    site_id = request.vars.get('site_id')
    if site_id and db.site_location(site_id):
        session.site_filter = site_id
        response.flash = "Site location updated."
        logging.debug(f"Site filter set to: {site_id}")
    else:
        response.flash = "Invalid site location."
        logging.warning("Attempted to set invalid site location.")
    redirect(request.env.http_referer or URL('default', 'index'))

def settings():
    """Renders the settings page."""
    # Retrieve users for the adminSettings tab
    users = db(db.auth_user).select()
    sites = db(db.site_location).select()
    
    return dict(users=users, sites = sites)
