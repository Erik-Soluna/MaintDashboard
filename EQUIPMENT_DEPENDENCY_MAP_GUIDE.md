# Equipment Dependency Map Guide

## Overview

The Equipment Dependency Map provides an interactive visual representation of equipment connections and dependencies organized by customer. Each customer has their own dedicated map showing their equipment hierarchy. When upstream equipment goes offline, all downstream equipment automatically shows as "cascade offline" on the map.

## Customer-Specific Maps

The map view displays **multiple customer maps**, each showing:
- All equipment belonging to that customer
- Connections between the customer's equipment
- Location hierarchy (sites and sub-locations)
- Real-time cascade offline visualization

### Viewing Maps
- **All Customers**: Default view shows all customer maps in separate sections
- **Single Customer**: Use the dropdown selector to view only one customer's map
- Each customer section shows equipment count, offline count, maintenance count, and location count

## Features

### 🗺️ Interactive Map
- **Drag-and-drop positioning** - Move equipment nodes around the canvas
- **Auto-layout** - Automatically arranges equipment hierarchically
- **Persistent positions** - Equipment positions are saved in your browser
- **Visual connectors** - SVG lines show dependencies between equipment
- **Status color-coding** - Equipment color changes based on status
- **Click to view** - Click any equipment node to view its details

### 🔗 Equipment Connections
- **Connection Types**: Power, Data, Cooling, Control, Mechanical, Other
- **Critical vs Non-Critical**:
  - **Critical** (solid red line): Downstream goes offline when upstream fails
  - **Non-Critical** (dashed blue line): Downstream remains unaffected
- **Circular dependency prevention**: System prevents connection loops
- **Multi-level cascading**: Status cascades through multiple equipment levels

### 📊 Status Visualization

Equipment nodes change color based on their effective status:
- **Green** - Active and online
- **Orange** - Under maintenance
- **Gray** - Inactive
- **Red (Pulsing)** - Cascade offline (upstream failure)

## How to Use

### Creating Equipment Connections

1. **Navigate to the Map**
   - Go to **Map** from the main navigation

2. **Open Connection Manager**
   - Click **"Manage Connections"** button

3. **Create a Connection**
   - Select **Upstream Equipment** (the one that supplies power/data/service)
   - Select **Downstream Equipment** (the one that depends on the upstream)
   - Choose **Connection Type** (power, data, cooling, etc.)
   - Check **Critical Connection** if downstream should go offline when upstream fails
   - Add optional description
   - Click **"Create Connection"**

4. **Visual Feedback**
   - A line will appear connecting the two equipment nodes
   - Critical connections are solid red lines
   - Non-critical connections are dashed blue lines

### Managing Existing Connections

1. **View Connections**
   - Open **"Manage Connections"** modal
   - Scroll through "Existing Connections" list
   - Each shows: Upstream → Downstream (Type | Critical/Non-Critical)

2. **Delete Connections**
   - Click the red trash icon next to any connection
   - Confirm deletion
   - Connection line disappears from map

### Organizing the Map

- **Auto Layout All**: Automatically arranges all customer maps hierarchically (root nodes at top)
- **Auto Layout (Per Customer)**: Arranges equipment for a specific customer's map
- **Reset All**: Clears all saved positions and runs auto-layout
- **Reset (Per Customer)**: Resets positions for a specific customer's map
- **Hide/Show Connections**: Toggle visibility of connector lines across all maps
- **Show/Hide Labels**: Toggle equipment location and status labels
- **Drag Equipment**: Click and drag any equipment node to reposition
- **Customer Filter**: Select specific customer or view all customers
- **Per-Customer Positioning**: Each customer's equipment positions are saved separately

## Cascading Offline Behavior

### Example Scenario:
```
Power Source (Active)
    ↓ [Critical Power Connection]
Distribution Panel (Active)
    ↓ [Critical Power Connection]
End Device (Active)
```

**When Power Source goes offline:**
```
Power Source (Inactive) ← Manually set offline
    ↓
Distribution Panel (Cascade Offline) ← Automatically cascade
    ↓
End Device (Cascade Offline) ← Automatically cascade
```

**When Power Source comes back online:**
```
Power Source (Active) ← Manually set online
    ↓
Distribution Panel (Active) ← Automatically recovers
    ↓
End Device (Active) ← Automatically recovers
```

### How It Works:
1. Equipment has both `status` (its actual state) and `effective_status` (considering upstream)
2. When checking effective status, system recursively checks all critical upstream equipment
3. If any critical upstream equipment is offline, effective status becomes `cascade_offline`
4. This cascades through multiple levels automatically
5. Non-critical connections don't cause cascading offline

## API Endpoints

### Create Connection
```http
POST /equipment/api/connections/
Content-Type: application/json

{
    "upstream_equipment": 1,
    "downstream_equipment": 2,
    "connection_type": "power",
    "is_critical": true,
    "description": "Main power supply"
}
```

### Delete Connection
```http
DELETE /equipment/api/connections/{connection_id}/
```

## Admin Interface

Equipment connections can also be managed through the Django admin:
- Navigate to **Admin** → **Equipment** → **Equipment Connections**
- Create, edit, or delete connections
- View connection details and audit information
- Filter by connection type, critical status, active status

## Testing

### Run Automated Tests
```bash
# In Docker
docker exec -it <container_name> python manage.py test_equipment_connections

# Direct (if not using Docker)
python manage.py test_equipment_connections
```

### Test Scenarios Covered:
1. ✅ All equipment online
2. ✅ Cascading offline when upstream fails
3. ✅ Recovery when upstream comes back online
4. ✅ Get all affected downstream equipment
5. ✅ Circular dependency prevention

### Manual Testing Steps:
1. Create test equipment (Power Source, Panel, Device)
2. Create connections: Power Source → Panel → Device
3. Set Power Source to "Inactive"
4. View map - Panel and Device should show as cascade offline (red, pulsing)
5. Set Power Source back to "Active"
6. View map - All equipment should be green again

## Database Schema

### EquipmentConnection Model
- `upstream_equipment` - Foreign key to Equipment (supplier)
- `downstream_equipment` - Foreign key to Equipment (dependent)
- `connection_type` - Choice field (power, data, cooling, control, mechanical, other)
- `is_critical` - Boolean (cascade offline if true)
- `description` - Text field
- `is_active` - Boolean
- Unique together: (upstream_equipment, downstream_equipment)
- Indexes on: upstream_equipment, downstream_equipment, connection_type+is_active

### Equipment Model Additions
New methods:
- `is_offline()` - Check if equipment is offline
- `get_effective_status()` - Get status considering upstream dependencies
- `get_upstream_equipment()` - Get list of equipment this depends on
- `get_downstream_equipment()` - Get list of equipment that depend on this
- `get_all_affected_downstream()` - Recursive list of all affected equipment
- `get_connection_to(other)` - Get connection to another equipment
- `get_connection_from(other)` - Get connection from another equipment

## Troubleshooting

### Connections Not Showing on Map
1. Check that connections are marked as `is_active=True`
2. Verify both upstream and downstream equipment exist and are active
3. Check browser console for JavaScript errors
4. Try clicking "Hide/Show Connections" to refresh

### Cascade Offline Not Working
1. Ensure connection has `is_critical=True`
2. Verify upstream equipment status is actually offline
3. Check for any broken connection chains
4. Run test command to verify: `python manage.py test_equipment_connections`

### Cannot Create Connection
- **"Equipment cannot connect to itself"**: Select different equipment
- **"Circular dependency"**: Connection would create a loop (A→B→C→A)
- **"Connection already exists"**: Use admin to view/edit existing connection

## Best Practices

1. **Map Organization**
   - Use Auto Layout to organize equipment hierarchically
   - Group equipment by location for easier visualization
   - Use descriptive connection descriptions

2. **Connection Strategy**
   - Mark only truly critical connections as critical
   - Use power connections for electrical dependencies
   - Use data connections for communication dependencies
   - Use cooling connections for HVAC dependencies

3. **Status Management**
   - Set equipment to "Under Maintenance" instead of "Inactive" when possible
   - This helps distinguish planned vs unplanned outages
   - Monitor cascade offline to identify vulnerable equipment

4. **Testing New Connections**
   - After creating connections, temporarily set upstream offline
   - Verify downstream equipment shows cascade offline
   - Set upstream back online and verify recovery

## Future Enhancements

Potential future features:
- Equipment grouping/clustering on map
- Multiple connection paths with failover
- Historical cascade offline tracking
- Automatic connection suggestions based on location
- Export map as image/PDF
- Real-time status updates via WebSocket

