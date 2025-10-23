ALTER TABLE maintenance_maintenanceactivity ADD COLUMN IF NOT EXISTS timezone VARCHAR(50) DEFAULT 'America/Chicago';
