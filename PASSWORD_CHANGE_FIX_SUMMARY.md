# Password Change AttributeError Fix

## Problem
The application was throwing an AttributeError when trying to access a `force_password_change` attribute on the `UserProfile` model that didn't exist:

```
AttributeError: 'UserProfile' object has no attribute 'force_password_change'
Exception Location: /app/core/middleware.py, line 186, in process_request
```

## Root Cause
The middleware was trying to access a `force_password_change` attribute on UserProfile objects, but this field was not defined in the model.

## Solution Applied

### 1. Added `force_password_change` field to UserProfile model
- Added a new boolean field `force_password_change` with default value `False`
- This field allows administrators to force specific users to change their passwords

### 2. Created Django migration
- Created migration file `0004_add_force_password_change.py` to add the new field to the database
- The migration will add the field with default value `False` for all existing users

### 3. Updated middleware to handle the field safely
- Modified `ForcePasswordChangeMiddleware` to check for the `force_password_change` attribute safely
- Added fallback logic to handle cases where the UserProfile doesn't exist or the attribute is missing
- Improved error handling with try/except blocks

### 4. Added helper methods and signals
- Added `clear_force_password_change()` method to UserProfile model
- Added signals to handle password changes and user login events
- Improved logging for troubleshooting

## Changes Made

### Files Modified:
1. `core/models.py` - Added `force_password_change` field and helper method
2. `core/middleware.py` - Updated middleware to safely handle the new field
3. `core/signals.py` - Added signals for password change handling
4. `core/migrations/0004_add_force_password_change.py` - New migration file

### Key Features:
- **Backwards compatible**: Existing users will have `force_password_change` set to `False` by default
- **Safe field access**: Middleware uses `getattr()` with default values to prevent AttributeError
- **Flexible password forcing**: Administrators can now force specific users to change passwords
- **Automatic cleanup**: The force flag is cleared when users successfully change their password

## Deployment Steps
1. Apply the migration: `python manage.py migrate core`
2. Restart the Django application
3. The fix should resolve the AttributeError immediately

## Usage
To force a user to change their password:
```python
user_profile = UserProfile.objects.get(user=user)
user_profile.force_password_change = True
user_profile.save()
```

The user will be redirected to the password change page on their next login attempt.