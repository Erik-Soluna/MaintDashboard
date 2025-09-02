# Timezone Migration Guide

## 🚨 **URGENT: Database Migration Required**

The timezone feature has been deployed but requires a database migration to be run on the server.

### **Error Details**
```
ProgrammingError: column maintenance_maintenanceactivity.timezone does not exist
```

### **Root Cause**
The `timezone` field was added to the `MaintenanceActivity` model but the database migration hasn't been applied yet.

## 🔧 **Migration Steps**

### **Option 1: Run Migration Script (Recommended)**

#### **On Linux Server:**
```bash
# SSH into your server
ssh your-server

# Navigate to the application directory
cd /app

# Run the migration script
./scripts/run_timezone_migration.sh
```

#### **On Windows Server:**
```powershell
# Navigate to the application directory
cd /app

# Run the migration script
.\scripts\run_timezone_migration.ps1
```

### **Option 2: Manual Migration Commands**

```bash
# Navigate to app directory
cd /app

# Apply the maintenance app migration
python manage.py migrate maintenance

# Verify migration was applied
python manage.py showmigrations maintenance
```

### **Option 3: Docker Container Migration**

If running in Docker:

```bash
# Execute migration inside the container
docker exec -it your-container-name python manage.py migrate maintenance
```

## 📋 **Migration Details**

### **Migration File:** `maintenance/migrations/0005_add_timezone_to_maintenance_activity.py`

### **What it does:**
- Adds `timezone` field to `maintenance_maintenanceactivity` table
- Field type: `CharField(max_length=50)`
- Default value: `'America/Chicago'`
- Includes timezone choices for major timezones

### **Database Changes:**
```sql
ALTER TABLE maintenance_maintenanceactivity 
ADD COLUMN timezone VARCHAR(50) DEFAULT 'America/Chicago';
```

## ✅ **Verification Steps**

After running the migration:

1. **Check Migration Status:**
   ```bash
   python manage.py showmigrations maintenance
   ```
   Should show `[X] 0005_add_timezone_to_maintenance_activity`

2. **Test Application:**
   - Visit the calendar page
   - Try creating a maintenance activity
   - Verify timezone selection works

3. **Check Database:**
   ```sql
   SELECT column_name, data_type, column_default 
   FROM information_schema.columns 
   WHERE table_name = 'maintenance_maintenanceactivity' 
   AND column_name = 'timezone';
   ```

## 🚀 **Deployment Integration**

### **For Future Deployments:**

Add this to your deployment pipeline:

```bash
# In your deployment script
python manage.py migrate maintenance
python manage.py collectstatic --noinput
```

### **Portainer Stack Update:**

If using Portainer, add migration step to your stack:

```yaml
services:
  web:
    # ... existing config ...
    command: >
      sh -c "python manage.py migrate maintenance &&
             python manage.py collectstatic --noinput &&
             gunicorn maintenance_dashboard.wsgi:application"
```

## 🔍 **Troubleshooting**

### **If Migration Fails:**

1. **Check Django Environment:**
   ```bash
   python manage.py check
   ```

2. **Check Database Connection:**
   ```bash
   python manage.py dbshell
   ```

3. **Manual SQL (Last Resort):**
   ```sql
   ALTER TABLE maintenance_maintenanceactivity 
   ADD COLUMN timezone VARCHAR(50) DEFAULT 'America/Chicago';
   ```

### **If Timezone Field Already Exists:**

```bash
# Mark migration as applied without running it
python manage.py migrate maintenance 0005 --fake
```

## 📞 **Support**

If you encounter issues:
1. Check the application logs
2. Verify database permissions
3. Ensure Django environment is properly configured
4. Contact the development team with error details

---

**⚠️ Important:** This migration must be run before the timezone features will work properly. The application will continue to show the database error until this migration is applied.
