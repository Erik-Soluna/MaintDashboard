#!/usr/bin/env python
import os
import sys
import django
from datetime import date

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maintenance_dashboard.settings')
django.setup()

from equipment.models import Equipment
from core.models import Location, EquipmentCategory

def create_equipment_for_sophie():
    """Create test equipment and assign it to Sophie location."""
    
    try:
        # Get the Sophie location
        sophie_location = Location.objects.get(name='Sophie')
        print(f"Found Sophie location: {sophie_location.name} (ID: {sophie_location.id})")
        
        # Get or create a Servers category
        servers_category, created = EquipmentCategory.objects.get_or_create(
            name='Servers',
            defaults={
                'description': 'Server equipment category',
                'is_active': True
            }
        )
        if created:
            print(f"Created new category: {servers_category.name}")
        else:
            print(f"Using existing category: {servers_category.name}")
        
        # Create the equipment
        equipment = Equipment.objects.create(
            name='Test Equipment Sophie',
            category=servers_category,
            manufacturer_serial='SN-TEST-SOPHIE-001',
            asset_tag='AT-TEST-SOPHIE-001',
            location=sophie_location,
            status='active',
            is_active=True,
            manufacturer='Test Manufacturer',
            model_number='Test Model 2024',
            power_ratings='1000W',
            trip_setpoints='Standard',
            warranty_details='Test warranty',
            installed_upgrades='None',
            commissioning_date=date.today()
        )
        
        print(f"✅ Equipment created successfully!")
        print(f"   Name: {equipment.name}")
        print(f"   Location: {equipment.location.name}")
        print(f"   Category: {equipment.category.name}")
        print(f"   Status: {equipment.get_status_display()}")
        print(f"   Asset Tag: {equipment.asset_tag}")
        print(f"   Serial: {equipment.manufacturer_serial}")
        
        return equipment
        
    except Location.DoesNotExist:
        print("❌ Error: Sophie location not found!")
        print("Available locations:")
        locations = Location.objects.filter(is_active=True)[:10]
        for loc in locations:
            print(f"   - {loc.name} (ID: {loc.id})")
        return None
        
    except Exception as e:
        print(f"❌ Error creating equipment: {e}")
        return None

if __name__ == '__main__':
    create_equipment_for_sophie() 