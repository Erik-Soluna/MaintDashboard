# Generated manually to add more maintenance categories

from django.db import migrations


def add_more_maintenance_categories(apps, schema_editor):
    """Add additional maintenance activity type categories."""
    ActivityTypeCategory = apps.get_model('maintenance', 'ActivityTypeCategory')
    
    # Additional maintenance categories
    additional_categories = [
        {
            'name': 'Emergency',
            'description': 'Urgent repairs and emergency response activities',
            'color': '#dc3545',
            'icon': 'fas fa-exclamation-triangle',
            'sort_order': 7,
        },
        {
            'name': 'Predictive',
            'description': 'Data-driven maintenance based on condition monitoring',
            'color': '#6f42c1',
            'icon': 'fas fa-chart-line',
            'sort_order': 8,
        },
        {
            'name': 'Condition-Based',
            'description': 'Maintenance triggered by equipment condition indicators',
            'color': '#fd7e14',
            'icon': 'fas fa-heartbeat',
            'sort_order': 9,
        },
        {
            'name': 'Reliability-Centered',
            'description': 'Strategic maintenance planning for critical equipment',
            'color': '#20c997',
            'icon': 'fas fa-shield-alt',
            'sort_order': 10,
        },
        {
            'name': 'Lubrication',
            'description': 'Oil changes, greasing, and lubrication activities',
            'color': '#6c757d',
            'icon': 'fas fa-tint',
            'sort_order': 11,
        },
        {
            'name': 'Alignment',
            'description': 'Equipment alignment and balancing activities',
            'color': '#e83e8c',
            'icon': 'fas fa-crosshairs',
            'sort_order': 12,
        },
        {
            'name': 'Overhaul',
            'description': 'Major equipment rebuilds and overhauls',
            'color': '#495057',
            'icon': 'fas fa-cogs',
            'sort_order': 13,
        },
        {
            'name': 'Installation',
            'description': 'New equipment installation and commissioning',
            'color': '#28a745',
            'icon': 'fas fa-plus-circle',
            'sort_order': 14,
        },
        {
            'name': 'Decommissioning',
            'description': 'Equipment removal and decommissioning activities',
            'color': '#6c757d',
            'icon': 'fas fa-minus-circle',
            'sort_order': 15,
        },
        {
            'name': 'Training',
            'description': 'Maintenance training and skill development',
            'color': '#17a2b8',
            'icon': 'fas fa-graduation-cap',
            'sort_order': 16,
        },
    ]
    
    for cat_data in additional_categories:
        ActivityTypeCategory.objects.get_or_create(
            name=cat_data['name'],
            defaults=cat_data
        )


def reverse_additional_categories(apps, schema_editor):
    """Remove additional maintenance categories."""
    ActivityTypeCategory = apps.get_model('maintenance', 'ActivityTypeCategory')
    
    # Remove additional categories
    additional_category_names = [
        'Emergency', 'Predictive', 'Condition-Based', 'Reliability-Centered',
        'Lubrication', 'Alignment', 'Overhaul', 'Installation', 
        'Decommissioning', 'Training'
    ]
    
    ActivityTypeCategory.objects.filter(
        name__in=additional_category_names
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_populate_default_data'),
    ]

    operations = [
        migrations.RunPython(add_more_maintenance_categories, reverse_additional_categories),
    ]
