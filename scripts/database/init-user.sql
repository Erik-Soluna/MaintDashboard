-- PostgreSQL User Initialization Script
-- This script creates the maintenance_user with proper permissions
-- Runs automatically when PostgreSQL container starts for the first time

-- Create the maintenance_user
CREATE USER maintenance_user WITH PASSWORD 'SecureProdPassword2024!';

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE maintenance_dashboard_prod TO maintenance_user;
GRANT ALL PRIVILEGES ON SCHEMA public TO maintenance_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO maintenance_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO maintenance_user;

-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO maintenance_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO maintenance_user;

-- Make maintenance_user a superuser (for Django migrations)
ALTER USER maintenance_user CREATEDB;
