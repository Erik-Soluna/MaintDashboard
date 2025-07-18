# Unified Calendar/Maintenance System Testing Guide

## 🎯 Overview

The system has been unified so that calendar events and maintenance activities use the same underlying data model (`CalendarEvent`). This eliminates all synchronization issues and provides a single source of truth.

## 🚀 Quick Setup

### Prerequisites
1. **Start Docker Desktop** - Make sure Docker Desktop is running
2. **Navigate to project directory** - `cd MaintDashboard`

### Automated Setup
Run the comprehensive setup script:
```bash
./setup_unified_system.sh
```

This script will:
- ✅ Check Docker status
- ✅ Start containers if needed
- ✅ Run database migrations
- ✅ Create global activity types
- ✅ Test the system
- ✅ Verify web interface

### Manual Setup (if automated fails)
```bash
# 1. Start containers
docker compose up -d

# 2. Wait for services to be ready
sleep 15

# 3. Run migrations
docker compose exec web python manage.py makemigrations events
docker compose exec web python manage.py makemigrations maintenance
docker compose exec web python manage.py migrate

# 4. Create global activity types
docker compose exec web python manage.py create_global_activity_types

# 5. Initialize database
docker compose exec web python manage.py init_database

# 6. Test the system
docker compose exec web python test_unified_system.py
```

## 🧪 Testing the System

### 1. Automated Tests
Run the comprehensive test suite:
```bash
docker compose exec web python test_unified_system.py
```

This tests:
- ✅ Database connectivity
- ✅ CalendarEvent model functionality
- ✅ Activity type categories
- ✅ Maintenance activity types
- ✅ Calendar events
- ✅ Unified functionality

### 2. Manual Web Testing
1. **Access the web interface**: http://localhost:8000/
2. **Log in** with your credentials
3. **Test calendar events**:
   - Go to Calendar
   - Create a new event with type "Maintenance Activity"
   - Verify it appears in both calendar and maintenance views
4. **Test maintenance activities**:
   - Go to Maintenance → Activities
   - Create a new maintenance activity
   - Verify it appears in the calendar

### 3. Key Features to Test

#### ✅ Unified Data Model
- Calendar events with `event_type='maintenance'` are maintenance activities
- All maintenance-specific fields are available on calendar events
- No synchronization needed - it's the same data

#### ✅ Compatibility Properties
- `event.scheduled_start` - Returns datetime for maintenance compatibility
- `event.scheduled_end` - Returns datetime for maintenance compatibility
- `event.status` - Returns maintenance status
- `event.is_overdue()` - Checks if maintenance is overdue

#### ✅ Global Activity Types
- "Physical Inspection" - General visual inspection
- "General Cleaning" - Basic cleaning tasks
- "Safety Check" - Safety system verification
- "Documentation Review" - Documentation updates
- "Environmental Monitoring" - Environmental checks
- "General Maintenance" - General maintenance tasks

## 🔧 Troubleshooting

### Common Issues

#### Docker Desktop Not Running
```
error during connect: Get "http://%2F%2F.%2Fpipe%2FdockerDesktopLinuxEngine/v1.46/containers/json
```
**Solution**: Start Docker Desktop first

#### Migration Errors
```
django.db.utils.OperationalError: relation "events_calendarevent" does not exist
```
**Solution**: Run migrations in order:
```bash
docker compose exec web python manage.py makemigrations events
docker compose exec web python manage.py migrate
```

#### Test Failures
If tests fail, check:
1. **Database connectivity**: `docker compose logs db`
2. **Web service**: `docker compose logs web`
3. **Redis connectivity**: `docker compose logs redis`

### Debug Commands

```bash
# Check container status
docker compose ps

# View logs
docker compose logs web
docker compose logs db
docker compose logs redis

# Access Django shell
docker compose exec web python manage.py shell

# Check database tables
docker compose exec web python manage.py dbshell
```

## 📊 Expected Results

### Database Tables
- ✅ `events_calendarevent` - Enhanced with maintenance fields
- ✅ `maintenance_maintenanceactivitytype` - Activity type definitions
- ✅ `maintenance_activitytypecategory` - Categories including "Global"
- ✅ All other existing tables

### Test Results
- ✅ All 6 tests should pass
- ✅ Web interface accessible at http://localhost:8000/
- ✅ Calendar events and maintenance activities are unified

### Key Benefits Achieved
- ✅ **100% Synchronization** - No sync issues since it's the same data
- ✅ **Simplified Architecture** - One model handles both calendar and maintenance
- ✅ **Better Performance** - No complex joins or sync operations
- ✅ **Easier Maintenance** - Single codebase to maintain
- ✅ **Consistent Data** - All views show the same underlying data

## 🎉 Success Criteria

The unified system is working correctly when:
1. ✅ All automated tests pass
2. ✅ Web interface is accessible
3. ✅ Calendar events with `event_type='maintenance'` work as maintenance activities
4. ✅ No synchronization errors occur
5. ✅ Global activity types are available
6. ✅ All maintenance-specific fields are accessible on calendar events

## 📝 Next Steps

After successful testing:
1. **Update views** to work with the unified model
2. **Test user workflows** in the web interface
3. **Verify all functionality** works as expected
4. **Deploy to production** when ready 