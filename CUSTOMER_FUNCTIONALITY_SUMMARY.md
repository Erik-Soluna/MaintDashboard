# Customer Location Assignment Feature

## Overview

This feature allows you to assign customers to specific locations for better tracking of maintenance impact. For example: "Sophie > POD 1 belongs to Marathon" means POD 1 location at Sophie site is assigned to Marathon customer.

## Features Implemented

### 1. **Customer Model** (`core/models.py`)
- **Customer** entity with the following fields:
  - `name` - Customer/client name (required, unique)
  - `code` - Customer code/abbreviation (auto-generated from name if not provided)
  - `contact_email` - Primary contact email for notifications
  - `contact_phone` - Primary contact phone number
  - `description` - Additional customer information
  - `is_active` - Active/inactive status
  - Timestamps and user tracking (created_by, updated_by, etc.)

### 2. **Location-Customer Association** (`core/models.py`)
- Added `customer` field to Location model (foreign key to Customer)
- **Customer Inheritance**: Locations inherit customer from parent locations if not directly assigned
- Helper methods:
  - `get_effective_customer()` - Returns customer (direct or inherited)
  - `get_customer_display()` - Shows if customer is direct or inherited
  - Updated `__str__()` to include customer name in location display

### 3. **Customer Management Interface**

#### **Customer Settings Page** (`/settings/customers/`)
- Paginated list of all customers
- Shows customer name, code, contact info, location count, and status
- Statistics cards showing total and active customers
- Add/Edit/Delete actions for each customer

#### **Customer Form** (`/customers/add/`, `/customers/<id>/edit/`)
- Comprehensive form for creating/editing customers
- Auto-generates customer code from name if not provided
- Shows associated locations when editing existing customers
- Form validation and error handling

#### **Customer Deletion** (`/customers/<id>/delete/`)
- Safe deletion with dependency checking
- Prevents deletion if customer has associated locations
- Lists all associated locations for confirmation
- Requires explicit confirmation before deletion

### 4. **Enhanced Location Management**
- Location forms now include customer selection dropdown
- Customer field appears in location creation/editing
- Customers are filtered to show only active ones

### 5. **Dashboard Integration**
- **Pod Status Cards**: Now display customer information when available
- Customer name shown with user icon below pod name
- CSS styling for customer display in pod cards
- Customer information included in overview data

### 6. **Navigation & UI**
- Added "Customers" to Settings dropdown menu
- Consistent styling with existing interface
- Responsive design for mobile compatibility

## Database Schema Changes

### New Table: `core_customer`
```sql
- id (Primary Key)
- name (VARCHAR, UNIQUE)
- code (VARCHAR, UNIQUE) 
- contact_email (EMAIL, OPTIONAL)
- contact_phone (VARCHAR, OPTIONAL)
- description (TEXT, OPTIONAL)
- is_active (BOOLEAN, DEFAULT TRUE)
- created_at, updated_at (TIMESTAMPS)
- created_by_id, updated_by_id (FOREIGN KEYS to User)
```

### Modified Table: `core_location`
```sql
+ customer_id (FOREIGN KEY to core_customer, OPTIONAL)
```

## Usage Examples

### 1. **Creating Customers**
1. Go to Settings → Customers
2. Click "Add Customer"
3. Enter customer details (name is required, code auto-generates)
4. Save customer

### 2. **Assigning Locations to Customers**
1. Go to Settings → Locations
2. Edit an existing location or create a new one
3. Select customer from dropdown
4. Save location

### 3. **Viewing Customer Impact**
1. Dashboard now shows customer names in pod status cards
2. When maintenance is performed on a location, you can see which customer is affected
3. Location lists show customer assignments

### 4. **Customer Inheritance**
- If a site is assigned to "Marathon", all pods under that site inherit "Marathon" as customer
- Individual pods can override with their own customer assignment
- `get_effective_customer()` method handles this logic automatically

## Files Modified/Created

### Core Models & Logic
- `core/models.py` - Added Customer model and Location-Customer relationship
- `core/forms.py` - Added CustomerForm and updated LocationForm
- `core/views.py` - Added customer management views and updated dashboard
- `core/urls.py` - Added customer management URL patterns

### Templates
- `templates/core/customers_settings.html` - Customer list/management page
- `templates/core/customer_form.html` - Customer add/edit form
- `templates/core/delete_customer.html` - Customer deletion confirmation
- `templates/core/dashboard.html` - Updated to show customer info in pod cards
- `templates/base.html` - Added customer management to settings menu

### Database Migration
- Migration file will be created for Customer model and Location.customer field

## Benefits

1. **Maintenance Impact Tracking**: Know exactly which customers are affected by maintenance activities
2. **Better Communication**: Contact information stored for customer notifications
3. **Reporting**: Can generate reports by customer to show maintenance activities
4. **Hierarchy Support**: Customer assignments can be inherited through location hierarchy
5. **Flexible Assignment**: Can assign customers at site level or individual location level

## Next Steps

1. **Run Migration**: Create and apply database migrations for the new schema
2. **Import Existing Data**: If you have existing customer data, create import functionality
3. **Notifications**: Enhance maintenance notifications to include customer contact information
4. **Reporting**: Add customer-based filtering to maintenance reports
5. **API Integration**: Add customer information to API endpoints for external integrations

## Example Scenario

**Setup:**
- Site: "Sophie"
- Locations: "POD 1", "POD 2", "POD 3" (under Sophie)
- Customer: "Marathon"

**Assignment Options:**
1. **Site Level**: Assign "Marathon" to "Sophie" site → All pods inherit Marathon
2. **Individual Level**: Assign "Marathon" only to "POD 1" → Only POD 1 shows Marathon

**Dashboard Display:**
- POD 1 card shows: "POD 1 (Marathon)"
- Maintenance on POD 1 equipment clearly shows Marathon is affected

This implementation provides a complete customer tracking system that integrates seamlessly with the existing maintenance dashboard functionality.