"""
Utility functions for the maintenance dashboard.
"""

import logging

logger = logging.getLogger(__name__)


def ensure_default_activity_types():
    """
    Ensure default activity types exist in the database.
    This function can be called from other parts of the system to check for defaults.
    """
    try:
        from maintenance.models import MaintenanceActivityType, ActivityTypeCategory
        from django.contrib.auth.models import User
        
        # Check if we have any activity types
        if MaintenanceActivityType.objects.exists():
            logger.info("Activity types already exist, skipping default creation")
            return True
        
        # Get admin user for created_by field
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            admin_user = User.objects.filter(is_staff=True).first()
        if not admin_user:
            logger.warning("No admin user found for creating default activity types")
            return False
        
        # Create default categories
        categories = {}
        default_categories = [
            {
                'name': 'Preventive Maintenance',
                'description': 'Regular preventive maintenance activities',
                'color': '#28a745',
                'icon': 'fas fa-tools',
                'sort_order': 1,
            },
            {
                'name': 'Inspection',
                'description': 'Inspection and testing activities',
                'color': '#17a2b8',
                'icon': 'fas fa-search',
                'sort_order': 2,
            },
        ]
        
        for cat_data in default_categories:
            category, created = ActivityTypeCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults={
                    'description': cat_data['description'],
                    'color': cat_data['color'],
                    'icon': cat_data['icon'],
                    'sort_order': cat_data['sort_order'],
                    'is_active': True,
                    'is_global': True,
                    'created_by': admin_user,
                }
            )
            categories[cat_data['name']] = category
            if created:
                logger.info(f"Created default category: {category.name}")
        
        # Create basic activity types
        basic_activity_types = [
            {
                'name': 'PM-001',
                'category': categories.get('Preventive Maintenance'),
                'description': 'Regular preventive maintenance inspection and service',
                'estimated_duration_hours': 4,
                'frequency_days': 90,
            },
            {
                'name': 'INS-001',
                'category': categories.get('Inspection'),
                'description': 'Monthly operational inspection',
                'estimated_duration_hours': 1,
                'frequency_days': 30,
            },
        ]
        
        for at_data in basic_activity_types:
            if at_data['category']:
                activity_type, created = MaintenanceActivityType.objects.get_or_create(
                    name=at_data['name'],
                    defaults={
                        'category': at_data['category'],
                        'description': at_data['description'],
                        'estimated_duration_hours': at_data['estimated_duration_hours'],
                        'frequency_days': at_data['frequency_days'],
                        'is_mandatory': True,
                        'is_active': True,
                        'created_by': admin_user,
                    }
                )
                if created:
                    logger.info(f"Created default activity type: {activity_type.name}")
        
        logger.info("Default activity types ensured successfully")
        return True
        
    except ImportError:
        logger.warning("Maintenance app not available, cannot ensure default activity types")
        return False
    except Exception as e:
        logger.error(f"Error ensuring default activity types: {str(e)}")
        return False


def get_or_create_default_activity_type():
    """
    Get or create a default activity type for general use.
    Returns the first available activity type or creates a basic one.
    """
    try:
        from maintenance.models import MaintenanceActivityType, ActivityTypeCategory
        from django.contrib.auth.models import User
        
        # Try to get an existing activity type
        activity_type = MaintenanceActivityType.objects.filter(is_active=True).first()
        if activity_type:
            return activity_type
        
        # If none exist, ensure defaults are created
        if ensure_default_activity_types():
            return MaintenanceActivityType.objects.filter(is_active=True).first()
        
        return None
        
    except ImportError:
        return None
    except Exception as e:
        logger.error(f"Error getting default activity type: {str(e)}")
        return None 