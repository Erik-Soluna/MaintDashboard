# POD Generation Feature

## Overview
The POD (Power Distribution Unit) generation feature allows users to automatically create PODs and MDCs (Main Distribution Centers) for existing sites in the maintenance dashboard.

## Features

### Management Command
- **Command**: `python manage.py generate_pods`
- **Location**: `core/management/commands/generate_pods.py`
- **Supports**: Up to 100 PODs per site
- **Configurable**: Number of MDCs per POD

### Command Options
- `--site-id`: Generate PODs for a specific site ID
- `--site-name`: Generate PODs for sites matching a name pattern
- `--pod-count`: Number of PODs to generate per site (1-100, default: 11)
- `--mdcs-per-pod`: Number of MDCs to generate per POD (1-10, default: 2)
- `--force`: Force regeneration of existing PODs

### Web Interface
- **URL**: `/core/settings/locations/`
- **Button**: "Generate PODs" button in the locations management page
- **Modal**: Configurable form with options for:
  - Target site selection (All sites or specific site)
  - POD count (1-100)
  - MDCs per POD (1-10)
  - Force regeneration option
  - Real-time output display

### API Endpoint
- **URL**: `/core/locations/generate-pods/`
- **Method**: POST
- **Authentication**: Required (staff/superuser)
- **Response**: JSON with success status and command output

## Usage Examples

### Command Line
```bash
# Generate 11 PODs with 2 MDCs each for all sites
python manage.py generate_pods

# Generate 50 PODs with 3 MDCs each for a specific site
python manage.py generate_pods --site-id 1 --pod-count 50 --mdcs-per-pod 3

# Generate PODs for sites containing "Dorothy"
python manage.py generate_pods --site-name "Dorothy" --pod-count 25

# Force regeneration of existing PODs
python manage.py generate_pods --force
```

### Web Interface
1. Navigate to Settings → Locations
2. Click the "Generate PODs" button
3. Configure the options in the modal:
   - Select target site(s)
   - Set POD count (1-100)
   - Set MDCs per POD (1-10)
   - Choose whether to force regeneration
4. Click "Generate PODs"
5. View the output and wait for page refresh

## Implementation Details

### Models Used
- `Location`: Hierarchical location model with `is_site` flag
- `User`: System user for creating locations

### Hierarchy Structure
```
Site (is_site=True)
├── POD 1 (is_site=False)
│   ├── MDC 1 (is_site=False)
│   ├── MDC 2 (is_site=False)
│   └── ...
├── POD 2 (is_site=False)
│   ├── MDC 3 (is_site=False)
│   ├── MDC 4 (is_site=False)
│   └── ...
└── ...
```

### Validation
- POD count: 1-100
- MDCs per POD: 1-10
- Site must exist and be active
- Prevents duplicate PODs unless force flag is used

### Error Handling
- Validates input parameters
- Handles missing sites gracefully
- Provides detailed error messages
- Logs all operations

## Testing

### Management Command Test
```bash
docker-compose exec web python test_generate_pods.py
```

### Web Interface Test
```bash
python test_web_interface.py
```

## Files Modified/Created

### New Files
- `core/management/commands/generate_pods.py`
- `test_generate_pods.py`
- `test_web_interface.py`
- `POD_GENERATION_FEATURE.md`

### Modified Files
- `core/views.py`: Added `generate_pods` view
- `core/urls.py`: Added URL pattern for generate_pods
- `templates/core/locations_settings.html`: Added Generate PODs button and modal

## Security
- Requires staff/superuser permissions
- CSRF protection enabled
- Input validation and sanitization
- No direct database access from web interface

## Performance
- Efficient bulk creation using `get_or_create`
- Minimal database queries
- Progress feedback for large operations
- Non-blocking web interface with async response 