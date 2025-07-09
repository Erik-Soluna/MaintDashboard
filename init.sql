-- PostgreSQL initialization script for maintenance dashboard

-- Create database if it doesn't exist (this is handled by docker-compose environment variables)
-- CREATE DATABASE maintenance_dashboard;

-- Enable commonly used extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create indexes for better performance on text search
-- These will be created by Django migrations, but we can prepare the database

-- Set timezone
SET timezone = 'UTC';

-- Basic database configuration
ALTER DATABASE maintenance_dashboard SET timezone TO 'UTC';