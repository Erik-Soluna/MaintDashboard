# -*- coding: utf-8 -*-

"""
Database and Authentication initialization.
"""

import logging
import uuid
from gluon.tools import Auth, Crud

logging.basicConfig(level=logging.DEBUG)

# Initialize the Database and Authentication
db = DAL("sqlite://storage.sqlite", migrate=True)
auth = Auth(db)
crud = Crud(db)
auth.define_tables(username=True, migrate=True)

# Prevent Table Duplication - Define Reference Tables First
if "equipment_category" not in db.tables:
    db.define_table(
        "equipment_category",
        Field(
            "name",
            "string",
            unique=True,
            label="Category Name",
            requires=IS_NOT_EMPTY(),
        ),
        format="%(name)s",
    )

# Combined Location Table
if "location" not in db.tables:
    db.define_table(
        "location",
        Field("name", "string", label="Location Name", requires=IS_NOT_EMPTY()),
        Field(
            "parent_location",
            "reference location",
            label="Parent Location",
            default=None,
        ),  # Self-reference for hierarchy
        Field("latitude", "double", label="Latitude (Future Use)"),
        Field("longitude", "double", label="Longitude (Future Use)"),
        Field(
            "is_site", "boolean", default=False, label="Is Site Location?"
        ),  # Flag to identify site locations
        migrate=True,
    )

# Add Group ID to auth_user Table if it doesn't exist
if "groupID" not in db.auth_user.fields:
    db.auth_user.groupID = Field("groupID", "integer", default=2)

db.commit()

# Secure Admin Account Creation with Random Password
admin_user = db(db.auth_user.username == "admin").select().first()
if not admin_user:
    import random
    import string

    random_password = "".join(
        random.choices(string.ascii_letters + string.digits, k=12)
    )
    hashed_password = db.auth_user.password.validate(random_password)[0]

    admin_id = db.auth_user.insert(
        username="admin",
        email="admin@example.com",
        password=hashed_password,
        first_name="System",
        last_name="Administrator",
        groupID=1,
    )
    db.commit()
    logging.info(f"Admin account created. Username: admin, Password: {random_password}")
else:
    admin_id = admin_user.id

# Ensure Admin Role Exists
admin_role = db(db.auth_group.role == "admin").select().first()
if not admin_role:
    admin_role_id = db.auth_group.insert(
        role="admin", description="Full administrative access"
    )
    db.commit()
else:
    admin_role_id = admin_role.id

# Ensure Admin User is Assigned to the Admin Role
admin_membership = db(
    (db.auth_membership.user_id == admin_id)
    & (db.auth_membership.group_id == admin_role_id)
).select().first()
if not admin_membership:
    db.auth_membership.insert(user_id=admin_id, group_id=admin_role_id)
    db.commit()

# Define Equipment Table AFTER Reference Tables

if "equipment" not in db.tables:
    db.define_table(
        "equipment",
        Field("name", "string", required=True, label="Equipment Name", unique=True),
        Field(
            "category",
            "reference equipment_category",
            label="Category",
            requires=IS_IN_DB(
                db, "equipment_category.id", "equipment_category.name"
            ),
        ),
        Field(
            "manufacturer_serial",
            "string",
            label="Manufacturer Serial",
            unique=True,
        ),
        Field("soluna_asset_tag", "string", label="Asset Tag", unique=True),
        Field(
            "location",  # Changed from site_location/equipment_location
            "reference location",
            label="Location",
            requires=IS_IN_DB(db, "location.id", "location.name"),
        ),
        Field("datasheet", "upload", label="Datasheet"),
        Field("warranty_details", "text", label="Warranty Details"),
        Field("installed_upgrades", "text", label="Installed Upgrades"),
        Field("power_ratings", "string", label="Power Ratings"),
        Field("trip_setpoints", "string", label="Trip Setpoints"),
        Field("schematics", "upload", label="Schematics"),
        Field(
            "created_by",
            "reference auth_user",
            default=auth.user_id,
            readable=False,
            writable=False,
        ),
        Field(
            "modified_by",
            "reference auth_user",
            update=auth.user_id,
            readable=False,
            writable=False,
        ),
        Field(
            "created_on",
            "datetime",
            default=request.now,
            readable=False,
            writable=False,
        ),
        Field(
            "modified_on",
            "datetime",
            update=request.now,
            readable=False,
            writable=False,
        ),
        Field("dga_due", "date", label="DGA Due Date"),
        Field("item_due_date", "date", label="Item Due Date"),
        Field("active_items", "string", label="Active Items"),
        Field("item_status", "string", label="Item Status"),
    )

# Define Maintenance Table
if "maintenance" not in db.tables:
    db.define_table(
        "maintenance",
        Field("equipment_id", "reference equipment", label="Equipment"),
        Field("title", "string", label="Title"),
        Field("description", "text", label="Description"),
        Field("required_status", "string", label="Required Status"),
        Field("start_datetime", "datetime", label="Start Date Time"),
        Field("end_datetime", "datetime", label="End Date Time"),
    )

# Define Schedule Table
if "schedule" not in db.tables:
    db.define_table(
        "schedule",
        Field("maintenance_id", "reference maintenance", label="Maintenance Event"),
        Field("start_datetime", "datetime", label="Start Date Time"),
        Field("end_datetime", "datetime", label="End Date Time"),
    )

# Define Calendar Event Table
if "calendar_event" not in db.tables:
    db.define_table(
        "calendar_event",
        Field("equipment_id", "reference equipment", label="Equipment"),
        Field("event_name", "string", label="Event Name"),
        Field("event_date", "date", label="Event Date"),
        Field("description", "text", label="Description"),
    )


db.commit()

# Add Unique Indexes to Ensure Database Integrity
db.executesql("CREATE UNIQUE INDEX IF NOT EXISTS unique_name ON equipment (name);")
db.executesql(
    "CREATE UNIQUE INDEX IF NOT EXISTS unique_serial ON equipment (manufacturer_serial);"
)
db.executesql(
    "CREATE UNIQUE INDEX IF NOT EXISTS unique_asset_tag ON equipment (soluna_asset_tag);"
)

# Debugging: Check for Duplicate Entries
duplicates = db(db.equipment.name).select(
    db.equipment.name, groupby=db.equipment.name, having=(db.equipment.id.count() > 1)
)
if duplicates:
    logging.warning(f"Duplicate Equipment Names Found: {duplicates}")
