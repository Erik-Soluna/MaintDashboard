# Generated manually to populate default data

from django.db import migrations
from django.contrib.auth.models import User


def create_default_data(apps, schema_editor):
    """Create default equipment categories and activity type categories."""
    EquipmentCategory = apps.get_model('core', 'EquipmentCategory')
    ActivityTypeCategory = apps.get_model('maintenance', 'ActivityTypeCategory')
    
    # Create default equipment categories
    equipment_categories = [
        {
            'name': 'Transformers',
            'description': 'Power transformers and distribution transformers'
        },
        {
            'name': 'Switchgear',
            'description': 'Circuit breakers, switches, and protective devices'
        },
        {
            'name': 'Motors',
            'description': 'Electric motors and drives'
        },
        {
            'name': 'Generators',
            'description': 'Emergency generators and backup power systems'
        },
        {
            'name': 'HVAC',
            'description': 'Heating, ventilation, and air conditioning systems'
        },
    ]
    
    for cat_data in equipment_categories:
        EquipmentCategory.objects.get_or_create(
            name=cat_data['name'],
            defaults={'description': cat_data['description']}
        )
    
    # Create default activity type categories
    activity_categories = [
        {
            'name': 'Preventive',
            'description': 'Regular maintenance activities to prevent equipment failure',
            'color': '#28a745',
            'icon': 'fas fa-wrench',
            'sort_order': 1,
        },
        {
            'name': 'Corrective',
            'description': 'Repair and fix activities to restore equipment function',
            'color': '#ffc107',
            'icon': 'fas fa-tools',
            'sort_order': 2,
        },
        {
            'name': 'Inspection',
            'description': 'Visual and testing checks to assess equipment condition',
            'color': '#17a2b8',
            'icon': 'fas fa-search',
            'sort_order': 3,
        },
        {
            'name': 'Cleaning',
            'description': 'Cleaning and housekeeping activities',
            'color': '#6f42c1',
            'icon': 'fas fa-broom',
            'sort_order': 4,
        },
        {
            'name': 'Calibration',
            'description': 'Calibration and adjustment activities',
            'color': '#fd7e14',
            'icon': 'fas fa-balance-scale',
            'sort_order': 5,
        },
        {
            'name': 'Testing',
            'description': 'Functional and performance testing',
            'color': '#e83e8c',
            'icon': 'fas fa-vial',
            'sort_order': 6,
        },
    ]
    
    for cat_data in activity_categories:
        ActivityTypeCategory.objects.get_or_create(
            name=cat_data['name'],
            defaults=cat_data
        )


def reverse_default_data(apps, schema_editor):
    """Remove default data (optional reverse migration)."""
    EquipmentCategory = apps.get_model('core', 'EquipmentCategory')
    ActivityTypeCategory = apps.get_model('maintenance', 'ActivityTypeCategory')
    
    # Remove default equipment categories
    EquipmentCategory.objects.filter(
        name__in=['Transformers', 'Switchgear', 'Motors', 'Generators', 'HVAC']
    ).delete()
    
    # Remove default activity type categories
    ActivityTypeCategory.objects.filter(
        name__in=['Preventive', 'Corrective', 'Inspection', 'Cleaning', 'Calibration', 'Testing']
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_add_logo_model'),
        ('maintenance', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_default_data, reverse_default_data),
    ]
