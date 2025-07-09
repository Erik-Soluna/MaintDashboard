# Django UserProfile.role Field Migration Fix

## Problem Description

The Django application was encountering the following error:

```
ProgrammingError at /core/dashboard/
column core_userprofile.role_id does not exist
LINE 1: ..._userprofile"."id", "core_userprofile"."user_id", "core_user...
                                                             ^
HINT:  Perhaps you meant to reference the column "core_userprofile.role".
```

## Root Cause Analysis

The issue was caused by a **missing migration** in the Django application. Here's what happened:

1. **Original Implementation**: The `UserProfile` model initially had a `role` field defined as a `CharField` with choices:
   ```python
   role = models.CharField(
       choices=[
           ('admin', 'Administrator'),
           ('manager', 'Maintenance Manager'),
           ('technician', 'Maintenance Technician'),
           ('viewer', 'Read-Only Viewer')
       ],
       default='viewer',
       max_length=20
   )
   ```

2. **Current Implementation**: The model was later changed to use a `ForeignKey` to a `Role` model:
   ```python
   role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True)
   ```

3. **Missing Migration**: The migration to convert the `CharField` to `ForeignKey` was never created or applied, causing a mismatch between the model definition and the database schema.

## Database Schema Mismatch

- **Database**: Still has `role` as a CharField
- **Django Model**: Expects `role_id` as a ForeignKey field
- **Result**: Django tries to access `role_id` but the database only has `role`

## Solution

### Step 1: Install Dependencies

The application requires several Django packages. Install them:

```bash
pip install django==4.2.7 psycopg2-binary python-decouple==3.8 Pillow
pip install django-widget-tweaks django-tables2 django-filter 
pip install django-crispy-forms crispy-bootstrap4 django-extensions
```

### Step 2: Generate Missing Migration

Run the following command to generate the missing migration:

```bash
python manage.py makemigrations core
```

This creates `core/migrations/0003_permission_role_alter_userprofile_role.py` which:
- Creates the `Permission` model
- Creates the `Role` model  
- Converts `UserProfile.role` from `CharField` to `ForeignKey`

### Step 3: Data Migration Strategy

**⚠️ Important:** Since the field type is changing from `CharField` to `ForeignKey`, you need to handle existing data. You have two options:

#### Option A: Clean Migration (Recommended for Development)
If you can afford to lose existing user role data:
```bash
python manage.py migrate
```

#### Option B: Data Preservation Migration
If you need to preserve existing role data, create a custom migration:

1. Create roles for existing choices:
   ```python
   # In a data migration
   from core.models import Role, UserProfile
   
   # Create roles matching the old choices
   admin_role = Role.objects.create(name='admin', display_name='Administrator')
   manager_role = Role.objects.create(name='manager', display_name='Maintenance Manager')
   technician_role = Role.objects.create(name='technician', display_name='Maintenance Technician')
   viewer_role = Role.objects.create(name='viewer', display_name='Read-Only Viewer')
   
   # Map existing role values to new Role objects
   role_mapping = {
       'admin': admin_role,
       'manager': manager_role,
       'technician': technician_role,
       'viewer': viewer_role,
   }
   
   # Update existing UserProfile records
   for profile in UserProfile.objects.all():
       if profile.role in role_mapping:
           profile.role = role_mapping[profile.role]
           profile.save()
   ```

### Step 4: Apply Migration

```bash
python manage.py migrate
```

### Step 5: Create Default Roles and Permissions

After migration, create the necessary roles and permissions:

```python
# Create this as a management command or in Django admin
from core.models import Role, Permission

# Create permissions
permissions = [
    Permission.objects.create(name='Full Access', codename='admin.full_access', module='admin'),
    Permission.objects.create(name='Manage All Maintenance', codename='maintenance.manage_all', module='maintenance'),
    Permission.objects.create(name='Create Equipment', codename='equipment.create', module='equipment'),
    Permission.objects.create(name='Edit Equipment', codename='equipment.edit', module='equipment'),
    Permission.objects.create(name='Delete Equipment', codename='equipment.delete', module='equipment'),
    Permission.objects.create(name='View Equipment', codename='equipment.view', module='equipment'),
    # Add more permissions as needed
]

# Create roles
admin_role = Role.objects.create(name='admin', display_name='Administrator', is_system_role=True)
admin_role.permissions.set(Permission.objects.all())

manager_role = Role.objects.create(name='manager', display_name='Maintenance Manager', is_system_role=True)
manager_role.permissions.set(Permission.objects.filter(module__in=['maintenance', 'equipment']))

technician_role = Role.objects.create(name='technician', display_name='Maintenance Technician', is_system_role=True)
technician_role.permissions.set(Permission.objects.filter(codename__in=['maintenance.complete', 'equipment.view']))

viewer_role = Role.objects.create(name='viewer', display_name='Read-Only Viewer', is_system_role=True)
viewer_role.permissions.set(Permission.objects.filter(codename__contains='view'))
```

## Prevention

To prevent this issue in the future:

1. **Always run makemigrations** when changing model field types
2. **Test migrations** in a development environment first
3. **Version control** all migration files
4. **Review migrations** before applying to production
5. **Backup database** before running migrations in production

## Files Changed

- `core/migrations/0003_permission_role_alter_userprofile_role.py` - New migration file
- `core/models.py` - Model definitions (already correct)

## Verification

After applying the fix, verify it works by:

1. Starting the Django development server
2. Accessing the dashboard URL: `http://localhost:8000/core/dashboard/`
3. Confirming no `ProgrammingError` occurs

## Migration File Content

The generated migration contains:

```python
operations = [
    migrations.CreateModel(
        name='Permission',
        fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('name', models.CharField(max_length=100, unique=True)),
            ('codename', models.CharField(max_length=100, unique=True)),
            ('description', models.TextField(blank=True)),
            ('module', models.CharField(help_text='Module this permission belongs to', max_length=50)),
            ('is_active', models.BooleanField(default=True)),
        ],
        # ... options
    ),
    migrations.CreateModel(
        name='Role',
        fields=[
            # ... Role model fields
            ('permissions', models.ManyToManyField(blank=True, to='core.permission')),
        ],
        # ... options
    ),
    migrations.AlterField(
        model_name='userprofile',
        name='role',
        field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.role'),
    ),
]
```

This migration properly handles the conversion from CharField to ForeignKey and creates the necessary supporting models.