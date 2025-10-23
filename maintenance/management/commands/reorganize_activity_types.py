"""
Management command to clean up and reorganize maintenance activity types.
Removes duplicates, consolidates similar types, and creates clear categories.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from maintenance.models import ActivityTypeCategory, MaintenanceActivityType
from django.db import transaction


class Command(BaseCommand):
    help = 'Clean up and reorganize maintenance activity types and categories'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making changes',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force deletion of existing types before recreating',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']
        
        self.stdout.write(self.style.WARNING('='*70))
        self.stdout.write(self.style.WARNING('  ACTIVITY TYPE REORGANIZATION'))
        self.stdout.write(self.style.WARNING('='*70))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        # Get or create admin user
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={'is_staff': True, 'is_superuser': True}
        )
        
        # Analyze current state
        self.analyze_current_state()
        
        if force and not dry_run:
            self.stdout.write(self.style.WARNING('\nClearing existing activity types...'))
            with transaction.atomic():
                deleted_types = MaintenanceActivityType.objects.all().delete()
                self.stdout.write(f'  Deleted {deleted_types[0]} activity types')
                
                deleted_cats = ActivityTypeCategory.objects.all().delete()
                self.stdout.write(f'  Deleted {deleted_cats[0]} categories')
        
        # Create clean structure
        if not dry_run:
            self.stdout.write(self.style.SUCCESS('\nCreating clean structure...'))
            categories = self.create_clean_categories(admin_user)
            self.create_clean_activity_types(categories, admin_user)
        else:
            self.stdout.write(self.style.WARNING('\nWould create clean structure (use without --dry-run to apply)'))
            self.show_proposed_structure()
        
        self.stdout.write(self.style.SUCCESS('\n' + '='*70))
        self.stdout.write(self.style.SUCCESS('Reorganization complete!'))

    def analyze_current_state(self):
        """Analyze and report on current activity types."""
        self.stdout.write('\n' + '='*70)
        self.stdout.write('CURRENT STATE ANALYSIS')
        self.stdout.write('='*70)
        
        categories = ActivityTypeCategory.objects.all().order_by('sort_order', 'name')
        types = MaintenanceActivityType.objects.all().select_related('category')
        
        self.stdout.write(f'\nTotal Categories: {categories.count()}')
        self.stdout.write(f'Total Activity Types: {types.count()}\n')
        
        # Show categories and their types
        for category in categories:
            category_types = types.filter(category=category)
            self.stdout.write(f'\n📁 {category.name} ({category_types.count()} types)')
            self.stdout.write(f'   {category.description}')
            for activity_type in category_types:
                self.stdout.write(f'   • {activity_type.name} - {activity_type.frequency_days} days')
        
        # Show orphaned types (if any)
        orphaned = types.filter(category__isnull=True)
        if orphaned.exists():
            self.stdout.write(self.style.WARNING(f'\n⚠️  {orphaned.count()} types without category'))
        
        # Find potential duplicates
        type_names = [t.name.lower().strip() for t in types]
        duplicates = [name for name in set(type_names) if type_names.count(name) > 1]
        if duplicates:
            self.stdout.write(self.style.ERROR(f'\n❌ Potential duplicates: {", ".join(duplicates)}'))

    def show_proposed_structure(self):
        """Show the proposed clean structure."""
        self.stdout.write('\n' + '='*70)
        self.stdout.write('PROPOSED CLEAN STRUCTURE')
        self.stdout.write('='*70)
        
        structure = """
📁 INSPECTION (Visual & Condition Monitoring)
   • Routine Inspection - Daily/Weekly visual checks
   • Safety Inspection - Monthly safety compliance check
   • Thermal Inspection - Quarterly thermal imaging scan
   
📁 TESTING (Diagnostic & Performance Testing)
   • DGA Analysis - Dissolved Gas Analysis for transformers (Quarterly)
   • Oil Analysis - Oil quality testing (Quarterly)
   • Insulation Testing - Electrical insulation test (Annual)
   • Load Testing - Performance under load (Annual)
   • Functional Testing - System functionality verification (Semi-annual)
   
📁 PREVENTIVE MAINTENANCE (Scheduled PM Activities)
   • Lubrication - Apply lubricants to moving parts (Monthly)
   • Filter Replacement - Replace filters (Semi-annual)
   • Cleaning - Equipment cleaning (Monthly)
   • Tightening & Adjustment - Torque checks, adjustments (Quarterly)
   
📁 CORRECTIVE MAINTENANCE (Repairs & Fixes)
   • Emergency Repair - Urgent failure response (As-needed)
   • Component Replacement - Replace failed parts (As-needed)
   • System Restoration - Restore after major failure (As-needed)
   • Fault Correction - Fix identified issues (As-needed)
   
📁 CALIBRATION (Accuracy & Precision)
   • Instrument Calibration - Measuring instruments (Annual)
   • Protection Relay Calibration - Relay settings (Annual)
   • Sensor Calibration - Temperature, pressure sensors (Semi-annual)
   
📁 COMPLIANCE (Regulatory & Standards)
   • Regulatory Inspection - Government/authority inspection (Annual)
   • Compliance Audit - Standards compliance check (Annual)
   • Documentation Review - Records & certifications review (Annual)
        """
        self.stdout.write(structure)

    def create_clean_categories(self, admin_user):
        """Create clean, well-organized categories."""
        categories_data = [
            {
                'name': 'Inspection',
                'description': 'Visual checks and condition monitoring to identify issues early',
                'color': '#17a2b8',  # Info blue
                'icon': 'fas fa-search',
                'sort_order': 1,
                'created_by': admin_user,
            },
            {
                'name': 'Testing',
                'description': 'Diagnostic testing and analysis to assess equipment health',
                'color': '#ffc107',  # Warning yellow
                'icon': 'fas fa-flask',
                'sort_order': 2,
                'created_by': admin_user,
            },
            {
                'name': 'Preventive Maintenance',
                'description': 'Scheduled maintenance to prevent failures and extend equipment life',
                'color': '#28a745',  # Success green
                'icon': 'fas fa-shield-alt',
                'sort_order': 3,
                'created_by': admin_user,
            },
            {
                'name': 'Corrective Maintenance',
                'description': 'Repairs and corrections to restore equipment functionality',
                'color': '#dc3545',  # Danger red
                'icon': 'fas fa-wrench',
                'sort_order': 4,
                'created_by': admin_user,
            },
            {
                'name': 'Calibration',
                'description': 'Equipment calibration to ensure accuracy and compliance',
                'color': '#6f42c1',  # Purple
                'icon': 'fas fa-balance-scale',
                'sort_order': 5,
                'created_by': admin_user,
            },
            {
                'name': 'Compliance',
                'description': 'Regulatory compliance, audits, and documentation review',
                'color': '#fd7e14',  # Orange
                'icon': 'fas fa-clipboard-check',
                'sort_order': 6,
                'created_by': admin_user,
            },
        ]
        
        categories = {}
        for data in categories_data:
            category, created = ActivityTypeCategory.objects.get_or_create(
                name=data['name'],
                defaults=data
            )
            categories[data['name']] = category
            status = '✅ Created' if created else '♻️  Updated'
            self.stdout.write(f'  {status}: {category.name}')
        
        return categories

    def create_clean_activity_types(self, categories, admin_user):
        """Create clean, non-duplicate activity types."""
        activity_types_data = [
            # ====== INSPECTION ======
            {
                'name': 'Routine Inspection',
                'category': categories['Inspection'],
                'description': 'Daily or weekly visual inspection of equipment condition, operation, and safety',
                'estimated_duration_hours': 1,
                'frequency_days': 7,
                'is_mandatory': True,
                'tools_required': 'Flashlight, inspection checklist, camera',
                'parts_required': 'None',
                'safety_notes': 'Follow lockout/tagout if accessing enclosed areas',
            },
            {
                'name': 'Safety Inspection',
                'category': categories['Inspection'],
                'description': 'Comprehensive safety inspection including guards, labels, grounding, and PPE requirements',
                'estimated_duration_hours': 2,
                'frequency_days': 30,
                'is_mandatory': True,
                'tools_required': 'Safety checklist, ground resistance tester',
                'parts_required': 'Safety labels, warning signs (as needed)',
                'safety_notes': 'Document all safety deficiencies immediately',
            },
            {
                'name': 'Thermal Inspection',
                'category': categories['Inspection'],
                'description': 'Infrared thermal imaging to detect hot spots, loose connections, and overheating',
                'estimated_duration_hours': 3,
                'frequency_days': 90,
                'is_mandatory': False,
                'tools_required': 'Thermal imaging camera, reference temperature standards',
                'parts_required': 'None',
                'safety_notes': 'Equipment can remain energized, maintain safe distances',
            },
            
            # ====== TESTING ======
            {
                'name': 'DGA Analysis',
                'category': categories['Testing'],
                'description': 'Dissolved Gas Analysis for transformers - tests oil for fault gases (H2, CH4, C2H2, etc.)',
                'estimated_duration_hours': 3,
                'frequency_days': 90,
                'is_mandatory': True,
                'tools_required': 'Oil sampling kit, sample bottles, labels, gloves',
                'parts_required': 'Sample containers, lab analysis fee',
                'safety_notes': 'Follow oil sampling procedures, avoid contamination, hot oil hazard',
            },
            {
                'name': 'Oil Analysis',
                'category': categories['Testing'],
                'description': 'General oil quality testing for contamination, moisture, acidity, and dielectric strength',
                'estimated_duration_hours': 2,
                'frequency_days': 180,
                'is_mandatory': True,
                'tools_required': 'Oil sampling kit, testing equipment',
                'parts_required': 'Sample containers, lab analysis',
                'safety_notes': 'Follow proper sampling procedures to avoid contamination',
            },
            {
                'name': 'Insulation Testing',
                'category': categories['Testing'],
                'description': 'Measure electrical insulation resistance (Megger test) to detect insulation degradation',
                'estimated_duration_hours': 2,
                'frequency_days': 365,
                'is_mandatory': True,
                'tools_required': 'Megohmmeter (Megger), test leads, safety equipment',
                'parts_required': 'None',
                'safety_notes': 'Equipment MUST be de-energized and isolated. High voltage test.',
            },
            {
                'name': 'Load Testing',
                'category': categories['Testing'],
                'description': 'Test equipment performance under various load conditions',
                'estimated_duration_hours': 4,
                'frequency_days': 365,
                'is_mandatory': True,
                'tools_required': 'Load bank, power analyzer, monitoring equipment',
                'parts_required': 'None',
                'safety_notes': 'Monitor temperature and loading closely, have emergency shutdown ready',
            },
            {
                'name': 'Functional Testing',
                'category': categories['Testing'],
                'description': 'Verify all system functions, controls, and safety features operate correctly',
                'estimated_duration_hours': 3,
                'frequency_days': 180,
                'is_mandatory': False,
                'tools_required': 'Testing procedures, multimeter, verification checklist',
                'parts_required': 'None',
                'safety_notes': 'Test safety interlocks first, follow sequence procedures',
            },
            
            # ====== PREVENTIVE MAINTENANCE ======
            {
                'name': 'Lubrication',
                'category': categories['Preventive Maintenance'],
                'description': 'Apply lubricants to bearings, gears, and moving parts per manufacturer schedule',
                'estimated_duration_hours': 1,
                'frequency_days': 30,
                'is_mandatory': True,
                'tools_required': 'Grease gun, oil can, cleaning rags, lubricant chart',
                'parts_required': 'Appropriate lubricants per specification',
                'safety_notes': 'Clean surfaces before lubricating, use correct lubricant type',
            },
            {
                'name': 'Filter Replacement',
                'category': categories['Preventive Maintenance'],
                'description': 'Replace air, oil, fuel, and cooling filters per maintenance schedule',
                'estimated_duration_hours': 2,
                'frequency_days': 180,
                'is_mandatory': True,
                'tools_required': 'Filter wrench, drain pan, hand tools',
                'parts_required': 'Replacement filters, O-rings, gaskets',
                'safety_notes': 'De-energize and cool equipment before filter changes',
            },
            {
                'name': 'Cleaning',
                'category': categories['Preventive Maintenance'],
                'description': 'Clean equipment surfaces, remove dust/debris, clean cooling fins and ventilation',
                'estimated_duration_hours': 1,
                'frequency_days': 30,
                'is_mandatory': False,
                'tools_required': 'Cleaning supplies, brushes, compressed air, vacuum',
                'parts_required': 'Cleaning solutions, protective coatings',
                'safety_notes': 'Protect electrical components, use approved cleaning agents',
            },
            {
                'name': 'Tightening & Adjustment',
                'category': categories['Preventive Maintenance'],
                'description': 'Torque check connections, adjust clearances, tighten hardware per specifications',
                'estimated_duration_hours': 2,
                'frequency_days': 90,
                'is_mandatory': True,
                'tools_required': 'Torque wrench, feeler gauges, hand tools',
                'parts_required': 'Lock washers, thread locker (as needed)',
                'safety_notes': 'De-energize equipment, follow torque specifications',
            },
            {
                'name': 'Belt & Coupling Inspection',
                'category': categories['Preventive Maintenance'],
                'description': 'Inspect and replace worn belts, check coupling alignment',
                'estimated_duration_hours': 2,
                'frequency_days': 90,
                'is_mandatory': False,
                'tools_required': 'Belt tension gauge, alignment tools',
                'parts_required': 'Replacement belts (as needed)',
                'safety_notes': 'De-energize equipment, check for pinch points',
            },
            
            # ====== CORRECTIVE MAINTENANCE ======
            {
                'name': 'Emergency Repair',
                'category': categories['Corrective Maintenance'],
                'description': 'Immediate response to equipment failure or critical issues',
                'estimated_duration_hours': 4,
                'frequency_days': 0,  # As-needed
                'is_mandatory': True,
                'tools_required': 'Emergency tool kit, diagnostic equipment, spare parts',
                'parts_required': 'Emergency spare parts inventory',
                'safety_notes': 'Prioritize safety over speed, follow emergency procedures',
            },
            {
                'name': 'Component Replacement',
                'category': categories['Corrective Maintenance'],
                'description': 'Replace failed or damaged components identified during inspection or testing',
                'estimated_duration_hours': 4,
                'frequency_days': 0,  # As-needed
                'is_mandatory': True,
                'tools_required': 'Hand tools, lifting equipment, torque wrench',
                'parts_required': 'Replacement components, hardware, gaskets',
                'safety_notes': 'De-energize and isolate, use proper lifting techniques',
            },
            {
                'name': 'Fault Correction',
                'category': categories['Corrective Maintenance'],
                'description': 'Diagnose and correct identified faults or performance issues',
                'estimated_duration_hours': 3,
                'frequency_days': 0,  # As-needed
                'is_mandatory': True,
                'tools_required': 'Diagnostic equipment, multimeter, test equipment',
                'parts_required': 'Determined after diagnosis',
                'safety_notes': 'Follow troubleshooting procedures, document findings',
            },
            {
                'name': 'System Restoration',
                'category': categories['Corrective Maintenance'],
                'description': 'Restore complete system operation after major failure or outage',
                'estimated_duration_hours': 8,
                'frequency_days': 0,  # As-needed
                'is_mandatory': True,
                'tools_required': 'Complete tool set, testing equipment, documentation',
                'parts_required': 'System components as required',
                'safety_notes': 'Follow restoration procedures, verify all systems before energizing',
            },
            
            # ====== CALIBRATION ======
            {
                'name': 'Instrument Calibration',
                'category': categories['Calibration'],
                'description': 'Calibrate measuring instruments, gauges, and sensors against traceable standards',
                'estimated_duration_hours': 2,
                'frequency_days': 365,
                'is_mandatory': True,
                'tools_required': 'Calibration equipment, reference standards, certificates',
                'parts_required': 'Calibration stickers, documentation',
                'safety_notes': 'Use NIST-traceable standards, document all calibrations',
            },
            {
                'name': 'Protection Relay Calibration',
                'category': categories['Calibration'],
                'description': 'Test and calibrate protection relays to ensure proper trip settings',
                'estimated_duration_hours': 3,
                'frequency_days': 365,
                'is_mandatory': True,
                'tools_required': 'Relay test set, multimeter, protection manual',
                'parts_required': 'None',
                'safety_notes': 'De-energize equipment, follow relay testing procedures',
            },
            
            # ====== COMPLIANCE ======
            {
                'name': 'Regulatory Inspection',
                'category': categories['Compliance'],
                'description': 'Required inspections by regulatory authorities or certification bodies',
                'estimated_duration_hours': 4,
                'frequency_days': 365,
                'is_mandatory': True,
                'tools_required': 'Compliance checklist, documentation, measurement equipment',
                'parts_required': 'None',
                'safety_notes': 'Prepare all required documentation, ensure equipment compliance',
            },
            {
                'name': 'Compliance Audit',
                'category': categories['Compliance'],
                'description': 'Internal audit of equipment compliance with standards (NFPA, IEEE, OSHA, etc.)',
                'estimated_duration_hours': 3,
                'frequency_days': 365,
                'is_mandatory': False,
                'tools_required': 'Audit checklist, standards documentation',
                'parts_required': 'None',
                'safety_notes': 'Review all safety documentation, verify training records',
            },
            {
                'name': 'Documentation Review',
                'category': categories['Compliance'],
                'description': 'Review and update equipment records, drawings, test results, and certifications',
                'estimated_duration_hours': 2,
                'frequency_days': 365,
                'is_mandatory': False,
                'tools_required': 'Document management system access',
                'parts_required': 'None',
                'safety_notes': 'Ensure all certifications are current',
            },
        ]
        
        created_count = 0
        for data in activity_types_data:
            activity_type, created = MaintenanceActivityType.objects.get_or_create(
                name=data['name'],
                defaults=data
            )
            if created:
                created_count += 1
                self.stdout.write(f'  ✅ Created: {activity_type.name}')
            else:
                self.stdout.write(f'  ♻️  Exists: {activity_type.name}')
        
        self.stdout.write(self.style.SUCCESS(f'\n  Total: {created_count} new activity types created'))

