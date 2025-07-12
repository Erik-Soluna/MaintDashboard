from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
        ('equipment', '0001_initial'),
        ('maintenance', '0001_initial'),
        ('events', '0001_initial'),
    ]

    operations = [
        # Add indexes for Location model
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_location_parent_location ON core_location(parent_location_id);",
            reverse_sql="DROP INDEX IF EXISTS idx_location_parent_location;"
        ),
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_location_is_site ON core_location(is_site);",
            reverse_sql="DROP INDEX IF EXISTS idx_location_is_site;"
        ),
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_location_is_active ON core_location(is_active);",
            reverse_sql="DROP INDEX IF EXISTS idx_location_is_active;"
        ),
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_location_customer ON core_location(customer_id);",
            reverse_sql="DROP INDEX IF EXISTS idx_location_customer;"
        ),
        
        # Add indexes for Equipment model
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_equipment_location ON equipment_equipment(location_id);",
            reverse_sql="DROP INDEX IF EXISTS idx_equipment_location;"
        ),
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_equipment_status ON equipment_equipment(status);",
            reverse_sql="DROP INDEX IF EXISTS idx_equipment_status;"
        ),
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_equipment_is_active ON equipment_equipment(is_active);",
            reverse_sql="DROP INDEX IF EXISTS idx_equipment_is_active;"
        ),
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_equipment_category ON equipment_equipment(category_id);",
            reverse_sql="DROP INDEX IF EXISTS idx_equipment_category;"
        ),
        
        # Add indexes for MaintenanceActivity model
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_maintenance_equipment ON maintenance_maintenanceactivity(equipment_id);",
            reverse_sql="DROP INDEX IF EXISTS idx_maintenance_equipment;"
        ),
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_maintenance_status ON maintenance_maintenanceactivity(status);",
            reverse_sql="DROP INDEX IF EXISTS idx_maintenance_status;"
        ),
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_maintenance_scheduled_start ON maintenance_maintenanceactivity(scheduled_start);",
            reverse_sql="DROP INDEX IF EXISTS idx_maintenance_scheduled_start;"
        ),
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_maintenance_scheduled_end ON maintenance_maintenanceactivity(scheduled_end);",
            reverse_sql="DROP INDEX IF EXISTS idx_maintenance_scheduled_end;"
        ),
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_maintenance_actual_end ON maintenance_maintenanceactivity(actual_end);",
            reverse_sql="DROP INDEX IF EXISTS idx_maintenance_actual_end;"
        ),
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_maintenance_assigned_to ON maintenance_maintenanceactivity(assigned_to_id);",
            reverse_sql="DROP INDEX IF EXISTS idx_maintenance_assigned_to;"
        ),
        
        # Add indexes for CalendarEvent model
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_calendar_equipment ON events_calendarevent(equipment_id);",
            reverse_sql="DROP INDEX IF EXISTS idx_calendar_equipment;"
        ),
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_calendar_event_date ON events_calendarevent(event_date);",
            reverse_sql="DROP INDEX IF EXISTS idx_calendar_event_date;"
        ),
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_calendar_is_completed ON events_calendarevent(is_completed);",
            reverse_sql="DROP INDEX IF EXISTS idx_calendar_is_completed;"
        ),
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_calendar_assigned_to ON events_calendarevent(assigned_to_id);",
            reverse_sql="DROP INDEX IF EXISTS idx_calendar_assigned_to;"
        ),
        
        # Add composite indexes for common query patterns
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_equipment_location_status ON equipment_equipment(location_id, status);",
            reverse_sql="DROP INDEX IF EXISTS idx_equipment_location_status;"
        ),
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_maintenance_equipment_status ON maintenance_maintenanceactivity(equipment_id, status);",
            reverse_sql="DROP INDEX IF EXISTS idx_maintenance_equipment_status;"
        ),
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_maintenance_scheduled_start_status ON maintenance_maintenanceactivity(scheduled_start, status);",
            reverse_sql="DROP INDEX IF EXISTS idx_maintenance_scheduled_start_status;"
        ),
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_calendar_event_date_completed ON events_calendarevent(event_date, is_completed);",
            reverse_sql="DROP INDEX IF EXISTS idx_calendar_event_date_completed;"
        ),
        
        # Add indexes for UserProfile model
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_userprofile_user ON core_userprofile(user_id);",
            reverse_sql="DROP INDEX IF EXISTS idx_userprofile_user;"
        ),
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_userprofile_role ON core_userprofile(role_id);",
            reverse_sql="DROP INDEX IF EXISTS idx_userprofile_role;"
        ),
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_userprofile_default_site ON core_userprofile(default_site_id);",
            reverse_sql="DROP INDEX IF EXISTS idx_userprofile_default_site;"
        ),
    ]