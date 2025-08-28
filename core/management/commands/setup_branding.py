from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import BrandingSettings, CSSCustomization


class Command(BaseCommand):
    help = 'Set up default branding settings and CSS customizations'

    def handle(self, *args, **options):
        self.stdout.write('Setting up default branding settings...')
        
        # Create default branding settings
        branding, created = BrandingSettings.objects.get_or_create(
            is_active=True,
            defaults={
                'site_name': 'Maintenance Dashboard',
                'site_tagline': 'Professional maintenance management system',
                'window_title_prefix': 'SOLUNA -',
                'window_title_suffix': ' - Maintenance System',
                'header_brand_text': 'Maintenance Dashboard',
                'navigation_overview_label': 'Overview',
                'navigation_equipment_label': 'Equipment',
                'navigation_maintenance_label': 'Maintenance',
                'navigation_calendar_label': 'Calendar',
                'navigation_map_label': 'Map',
                'navigation_settings_label': 'Settings',
                'navigation_debug_label': 'Debug',
                'footer_copyright_text': '© 2025 Maintenance Dashboard. All rights reserved.',
                'footer_powered_by_text': 'Powered by Django',
                'primary_color': '#4299e1',
                'secondary_color': '#2d3748',
                'accent_color': '#3182ce',
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS('✅ Created default branding settings')
            )
        else:
            self.stdout.write(
                self.style.WARNING('⚠️  Branding settings already exist')
            )
        
        # Create sample CSS customizations
        sample_css = [
            {
                'name': 'Enhanced Button Styling',
                'item_type': 'buttons',
                'description': 'Adds rounded corners and subtle shadows to buttons',
                'css_code': '''/* Enhanced Button Styling */
.btn {
    border-radius: 8px;
    transition: all 0.2s ease;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.btn:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
}

.btn-primary {
    background: linear-gradient(135deg, var(--primary-color), var(--accent-color));
    border: none;
}

.btn-primary:hover {
    background: linear-gradient(135deg, var(--accent-color), var(--primary-color));
}''',
                'priority': 10,
                'order': 1,
            },
            {
                'name': 'Card Enhancements',
                'item_type': 'cards',
                'description': 'Improves card appearance with better shadows and hover effects',
                'css_code': '''/* Card Enhancements */
.card {
    border-radius: 12px;
    border: none;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    transition: all 0.3s ease;
}

.card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
}

.card-header {
    border-radius: 12px 12px 0 0;
    border-bottom: 1px solid var(--border-color);
    background: linear-gradient(135deg, var(--bg-secondary), var(--bg-tertiary));
}''',
                'priority': 10,
                'order': 2,
            },
            {
                'name': 'Navigation Improvements',
                'item_type': 'navigation',
                'description': 'Enhances navigation tabs with better spacing and transitions',
                'css_code': '''/* Navigation Improvements */
.nav-tabs-custom .nav-link {
    position: relative;
    overflow: hidden;
}

.nav-tabs-custom .nav-link::before {
    content: '';
    position: absolute;
    bottom: 0;
    left: 50%;
    width: 0;
    height: 2px;
    background: var(--primary-color);
    transition: all 0.3s ease;
    transform: translateX(-50%);
}

.nav-tabs-custom .nav-link:hover::before {
    width: 100%;
}

.nav-tabs-custom .nav-link.active::before {
    width: 100%;
}''',
                'priority': 15,
                'order': 1,
            },
            {
                'name': 'Form Enhancements',
                'item_type': 'forms',
                'description': 'Improves form controls with better focus states and animations',
                'css_code': '''/* Form Enhancements */
.form-control {
    border-radius: 8px;
    transition: all 0.2s ease;
    border: 2px solid var(--border-color);
}

.form-control:focus {
    border-color: var(--primary-color);
    box-shadow: 0 0 0 3px rgba(66, 153, 225, 0.1);
    transform: translateY(-1px);
}

.form-control:hover {
    border-color: var(--primary-color);
}''',
                'priority': 20,
                'order': 1,
            },
            {
                'name': 'Table Improvements',
                'item_type': 'tables',
                'description': 'Enhances table appearance with better spacing and hover effects',
                'css_code': '''/* Table Improvements */
.table {
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.table th {
    background: linear-gradient(135deg, var(--bg-secondary), var(--bg-tertiary));
    border: none;
    padding: 15px 12px;
    font-weight: 600;
}

.table td {
    padding: 12px;
    border-bottom: 1px solid var(--border-color);
    transition: background-color 0.2s ease;
}

.table tbody tr:hover {
    background-color: var(--bg-tertiary);
    transform: scale(1.01);
}''',
                'priority': 25,
                'order': 1,
            },
        ]
        
        # Get or create a superuser for the created_by field
        try:
            superuser = User.objects.filter(is_superuser=True).first()
            if not superuser:
                superuser = User.objects.create_superuser('admin', 'admin@example.com', 'admin')
        except:
            superuser = None
        
        for css_data in sample_css:
            css_customization, created = CSSCustomization.objects.get_or_create(
                name=css_data['name'],
                defaults={
                    'item_type': css_data['item_type'],
                    'description': css_data['description'],
                    'css_code': css_data['css_code'],
                    'priority': css_data['priority'],
                    'order': css_data['order'],
                    'created_by': superuser,
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Created CSS customization: {css_data["name"]}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'⚠️  CSS customization already exists: {css_data["name"]}')
                )
        
        self.stdout.write(
            self.style.SUCCESS('🎨 Branding setup completed successfully!')
        )
        self.stdout.write('You can now customize your branding at /branding/')
