#!/usr/bin/env python3
"""
Script to create demo maintenance reports with DGA failure content.
This demonstrates the MaintenanceReport functionality.
"""

import os
import sys
import django
from django.utils import timezone
from datetime import datetime, timedelta

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maintenance_dashboard.settings')
django.setup()

from maintenance.models import (
    MaintenanceReport, MaintenanceActivity, MaintenanceActivityType, 
    ActivityTypeCategory
)
from equipment.models import Equipment
from core.models import Location, EquipmentCategory
from django.contrib.auth.models import User


def create_demo_reports():
    """Create demo maintenance reports with DGA failure content."""
    
    print("Creating demo maintenance reports...")
    
    # Get or create test user
    user, created = User.objects.get_or_create(
        username='demo_user',
        defaults={
            'email': 'demo@example.com',
            'first_name': 'Demo',
            'last_name': 'User'
        }
    )
    if created:
        user.set_password('demo123')
        user.save()
        print(f"Created demo user: {user.username}")
    
    # Get or create test location
    location, created = Location.objects.get_or_create(
        name='Main Plant',
        defaults={'is_site': True}
    )
    if created:
        print(f"Created location: {location.name}")
    
    # Get or create equipment category
    category, created = EquipmentCategory.objects.get_or_create(
        name='Transformers',
        defaults={'description': 'Electrical transformers'}
    )
    if created:
        print(f"Created equipment category: {category.name}")
    
    # Get or create equipment
    equipment, created = Equipment.objects.get_or_create(
        name='Main Power Transformer T-001',
        defaults={
            'category': category,
            'location': location,
            'manufacturer_serial': 'T001-2024-001',
            'model_number': '500kV Power Transformer',
            'manufacturer': 'PowerTech Industries',
            'asset_tag': 'T001-ASSET-001'
        }
    )
    if created:
        print(f"Created equipment: {equipment.name}")
    
    # Get or create activity type category
    activity_category, created = ActivityTypeCategory.objects.get_or_create(
        name='Preventive',
        defaults={'description': 'Preventive maintenance activities'}
    )
    if created:
        print(f"Created activity category: {activity_category.name}")
    
    # Get or create activity type
    activity_type, created = MaintenanceActivityType.objects.get_or_create(
        name='T-A-1',
        defaults={
            'category': activity_category,
            'description': 'Annual transformer inspection and DGA analysis',
            'frequency_days': 365,
            'estimated_duration_hours': 8
        }
    )
    if created:
        print(f"Created activity type: {activity_type.name}")
    
    # Get or create maintenance activity
    activity, created = MaintenanceActivity.objects.get_or_create(
        title='Annual Transformer T-001 Inspection and DGA Analysis',
        defaults={
            'equipment': equipment,
            'activity_type': activity_type,
            'description': 'Annual comprehensive inspection including dissolved gas analysis',
            'scheduled_start': timezone.now() - timedelta(days=7),
            'scheduled_end': timezone.now() - timedelta(days=7, hours=-8),
            'status': 'completed',
            'actual_start': timezone.now() - timedelta(days=7),
            'actual_end': timezone.now() - timedelta(days=7, hours=-6),
            'assigned_to': user,
            'created_by': user,
            'updated_by': user
        }
    )
    if created:
        print(f"Created maintenance activity: {activity.title}")
    
    # DGA Failure Report Content
    dga_failure_content = """
    DISSOLVED GAS ANALYSIS REPORT - TRANSFORMER T-001
    
    Date: 2024-01-15
    Technician: John Smith
    Work Hours: 6.5 hours
    
    EQUIPMENT INFORMATION:
    - Equipment: Main Power Transformer T-001
    - Location: Main Plant
    - Serial Number: T001-2024-001
    - Model: 500kV Power Transformer
    
    CRITICAL ISSUES FOUND:
    - Critical issue: Elevated levels of acetylene (C2H2) detected in oil sample
    - Critical issue: High concentration of hydrogen (H2) indicating potential arcing
    - Major problem: Carbon monoxide (CO) levels above normal limits
    - Minor issue: Slight increase in methane (CH4) levels
    
    GAS ANALYSIS RESULTS:
    - Hydrogen (H2): 450 ppm (Normal: <100 ppm) - CRITICAL
    - Methane (CH4): 85 ppm (Normal: <50 ppm) - ELEVATED
    - Ethane (C2H6): 45 ppm (Normal: <30 ppm) - ELEVATED
    - Ethylene (C2H4): 120 ppm (Normal: <50 ppm) - HIGH
    - Acetylene (C2H2): 25 ppm (Normal: <1 ppm) - CRITICAL
    - Carbon Monoxide (CO): 350 ppm (Normal: <200 ppm) - HIGH
    - Carbon Dioxide (CO2): 2800 ppm (Normal: <2000 ppm) - ELEVATED
    
    DIAGNOSIS:
    The presence of acetylene (C2H2) at 25 ppm indicates electrical arcing or sparking within the transformer. Combined with elevated hydrogen levels, this suggests a serious internal fault that requires immediate attention.
    
    RECOMMENDATIONS:
    1. Immediate load reduction recommended
    2. Schedule emergency shutdown for internal inspection
    3. Prepare for potential transformer replacement
    4. Monitor gas levels daily until shutdown
    
    PARTS REPLACED:
    - Replaced oil sampling valve
    - Changed oil filter cartridge
    - Installed new gas monitoring sensor
    
    MEASUREMENTS TAKEN:
    - Oil temperature: 65°C
    - Ambient temperature: 22°C
    - Oil pressure: 2.5 bar
    - Load current: 85% of rated capacity
    
    SAFETY NOTES:
    - Transformer operating under reduced load conditions
    - Continuous monitoring required
    - Emergency shutdown procedures reviewed with operations team
    
    NEXT STEPS:
    - Schedule emergency maintenance within 48 hours
    - Coordinate with operations for safe shutdown
    - Prepare replacement transformer if needed
    """
    
    # Create the DGA failure report
    dga_report, created = MaintenanceReport.objects.get_or_create(
        title='DGA Analysis Report - Critical Acetylene Detection',
        defaults={
            'activity': activity,
            'report_type': 'failure',
            'content': dga_failure_content,
            'uploaded_by': user,
            'created_by': user,
            'updated_by': user,
            'technician_name': 'John Smith',
            'work_hours': 6.5,
            'report_date': datetime(2024, 1, 15).date()
        }
    )
    
    if created:
        print(f"Created DGA failure report: {dga_report.title}")
        
        # Auto-analyze the report
        from maintenance.views import analyze_report_content
        try:
            analyzed_data = analyze_report_content(dga_failure_content)
            dga_report.analyzed_data = analyzed_data
            dga_report.is_processed = True
            dga_report.save()
            print("✅ Report automatically analyzed and processed")
            
            # Display analysis results
            print(f"\n📊 Analysis Results:")
            print(f"   - Issues found: {len(analyzed_data.get('issues', []))}")
            print(f"   - Parts replaced: {len(analyzed_data.get('parts_replaced', []))}")
            print(f"   - Measurements: {len(analyzed_data.get('measurements', []))}")
            print(f"   - Priority score: {dga_report.get_priority_score()}")
            print(f"   - Critical issues: {dga_report.has_critical_issues()}")
            
        except Exception as e:
            print(f"❌ Error analyzing report: {str(e)}")
            dga_report.processing_errors = str(e)
            dga_report.save()
    
    # Create a normal inspection report for comparison
    normal_content = """
    ROUTINE INSPECTION REPORT - TRANSFORMER T-001
    
    Date: 2024-01-10
    Technician: Jane Doe
    Work Hours: 4 hours
    
    EQUIPMENT INFORMATION:
    - Equipment: Main Power Transformer T-001
    - Location: Main Plant
    
    INSPECTION FINDINGS:
    - Minor issue: Slight oil seepage from gasket
    - Minor issue: Dust accumulation on cooling fins
    
    MEASUREMENTS TAKEN:
    - Oil temperature: 45°C
    - Ambient temperature: 20°C
    - Oil pressure: 2.2 bar
    
    PARTS REPLACED:
    - Replaced gasket seal
    - Changed air filter
    
    RECOMMENDATIONS:
    - Continue normal operation
    - Schedule next inspection in 6 months
    - Clean cooling fins during next maintenance
    """
    
    normal_report, created = MaintenanceReport.objects.get_or_create(
        title='Routine Inspection Report - Normal Operation',
        defaults={
            'activity': activity,
            'report_type': 'inspection',
            'content': normal_content,
            'uploaded_by': user,
            'created_by': user,
            'updated_by': user,
            'technician_name': 'Jane Doe',
            'work_hours': 4.0,
            'report_date': datetime(2024, 1, 10).date()
        }
    )
    
    if created:
        print(f"Created normal inspection report: {normal_report.title}")
        
        # Auto-analyze the normal report
        try:
            analyzed_data = analyze_report_content(normal_content)
            normal_report.analyzed_data = analyzed_data
            normal_report.is_processed = True
            normal_report.save()
            print("✅ Normal report automatically analyzed and processed")
            
            # Display analysis results
            print(f"\n📊 Normal Report Analysis:")
            print(f"   - Issues found: {len(analyzed_data.get('issues', []))}")
            print(f"   - Parts replaced: {len(analyzed_data.get('parts_replaced', []))}")
            print(f"   - Measurements: {len(analyzed_data.get('measurements', []))}")
            print(f"   - Priority score: {normal_report.get_priority_score()}")
            print(f"   - Critical issues: {normal_report.has_critical_issues()}")
            
        except Exception as e:
            print(f"❌ Error analyzing normal report: {str(e)}")
            normal_report.processing_errors = str(e)
            normal_report.save()
    
    print(f"\n🎉 Demo reports created successfully!")
    print(f"   - Equipment: {equipment.name}")
    print(f"   - Activity: {activity.title}")
    print(f"   - Reports: {MaintenanceReport.objects.filter(activity=activity).count()}")
    
    return {
        'equipment': equipment,
        'activity': activity,
        'dga_report': dga_report,
        'normal_report': normal_report
    }


if __name__ == '__main__':
    try:
        demo_data = create_demo_reports()
        print(f"\n✅ Demo setup completed successfully!")
        print(f"\nYou can now:")
        print(f"1. View reports at: /maintenance/reports/list/")
        print(f"2. View DGA report at: /maintenance/reports/{demo_data['dga_report'].id}/")
        print(f"3. Test analysis functionality in the web interface")
        
    except Exception as e:
        print(f"❌ Error creating demo reports: {str(e)}")
        import traceback
        traceback.print_exc() 