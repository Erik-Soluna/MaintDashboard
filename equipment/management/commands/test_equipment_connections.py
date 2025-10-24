"""
Management command to test equipment connections and cascading offline status.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from equipment.models import Equipment, EquipmentConnection
from core.models import Location, EquipmentCategory


class Command(BaseCommand):
    help = 'Test equipment connections and cascading offline behavior'

    def handle(self, *args, **options):
        self.stdout.write('🧪 Testing Equipment Connection System...\n')
        
        # Get or create test equipment
        self.stdout.write('📋 Setting up test equipment...')
        
        # Get first location and category
        location = Location.objects.filter(is_active=True).first()
        category = EquipmentCategory.objects.filter(is_active=True).first()
        
        if not location or not category:
            self.stdout.write(
                self.style.ERROR('❌ Need at least one location and category to test')
            )
            return
        
        user = User.objects.filter(is_superuser=True).first()
        
        # Create test equipment chain: Power Source → Distribution Panel → End Device
        power_source, _ = Equipment.objects.get_or_create(
            name='TEST-Power-Source',
            defaults={
                'category': category,
                'manufacturer_serial': 'TEST-PS-001',
                'asset_tag': 'TEST-PS-TAG',
                'location': location,
                'status': 'active',
                'is_active': True,
                'created_by': user
            }
        )
        
        distribution_panel, _ = Equipment.objects.get_or_create(
            name='TEST-Distribution-Panel',
            defaults={
                'category': category,
                'manufacturer_serial': 'TEST-DP-001',
                'asset_tag': 'TEST-DP-TAG',
                'location': location,
                'status': 'active',
                'is_active': True,
                'created_by': user
            }
        )
        
        end_device, _ = Equipment.objects.get_or_create(
            name='TEST-End-Device',
            defaults={
                'category': category,
                'manufacturer_serial': 'TEST-ED-001',
                'asset_tag': 'TEST-ED-TAG',
                'location': location,
                'status': 'active',
                'is_active': True,
                'created_by': user
            }
        )
        
        self.stdout.write(self.style.SUCCESS('✅ Test equipment created'))
        
        # Create connections
        self.stdout.write('\n📋 Creating test connections...')
        
        conn1, created1 = EquipmentConnection.objects.get_or_create(
            upstream_equipment=power_source,
            downstream_equipment=distribution_panel,
            defaults={
                'connection_type': 'power',
                'is_critical': True,
                'description': 'Power supply to distribution panel',
                'created_by': user
            }
        )
        
        conn2, created2 = EquipmentConnection.objects.get_or_create(
            upstream_equipment=distribution_panel,
            downstream_equipment=end_device,
            defaults={
                'connection_type': 'power',
                'is_critical': True,
                'description': 'Power supply to end device',
                'created_by': user
            }
        )
        
        self.stdout.write(self.style.SUCCESS('✅ Test connections created'))
        
        # Test 1: All equipment online
        self.stdout.write('\n' + '='*60)
        self.stdout.write('TEST 1: All Equipment Online')
        self.stdout.write('='*60)
        
        power_source.status = 'active'
        power_source.save()
        distribution_panel.status = 'active'
        distribution_panel.save()
        end_device.status = 'active'
        end_device.save()
        
        self.stdout.write(f'Power Source Status: {power_source.status} → Effective: {power_source.get_effective_status()}')
        self.stdout.write(f'Distribution Panel Status: {distribution_panel.status} → Effective: {distribution_panel.get_effective_status()}')
        self.stdout.write(f'End Device Status: {end_device.status} → Effective: {end_device.get_effective_status()}')
        
        if (power_source.get_effective_status() == 'active' and 
            distribution_panel.get_effective_status() == 'active' and 
            end_device.get_effective_status() == 'active'):
            self.stdout.write(self.style.SUCCESS('✅ TEST 1 PASSED: All equipment online'))
        else:
            self.stdout.write(self.style.ERROR('❌ TEST 1 FAILED'))
        
        # Test 2: Power source goes offline
        self.stdout.write('\n' + '='*60)
        self.stdout.write('TEST 2: Power Source Goes Offline')
        self.stdout.write('='*60)
        
        power_source.status = 'inactive'
        power_source.save()
        
        # Refresh from database
        power_source.refresh_from_db()
        distribution_panel.refresh_from_db()
        end_device.refresh_from_db()
        
        power_status = power_source.get_effective_status()
        panel_status = distribution_panel.get_effective_status()
        device_status = end_device.get_effective_status()
        
        self.stdout.write(f'Power Source Status: {power_source.status} → Effective: {power_status}')
        self.stdout.write(f'Distribution Panel Status: {distribution_panel.status} → Effective: {panel_status}')
        self.stdout.write(f'End Device Status: {end_device.status} → Effective: {device_status}')
        
        if (power_status == 'inactive' and 
            panel_status == 'cascade_offline' and 
            device_status == 'cascade_offline'):
            self.stdout.write(self.style.SUCCESS('✅ TEST 2 PASSED: Cascading offline working'))
        else:
            self.stdout.write(self.style.ERROR('❌ TEST 2 FAILED: Cascading offline not working correctly'))
        
        # Test 3: Power source back online
        self.stdout.write('\n' + '='*60)
        self.stdout.write('TEST 3: Power Source Back Online')
        self.stdout.write('='*60)
        
        power_source.status = 'active'
        power_source.save()
        
        # Refresh from database
        power_source.refresh_from_db()
        distribution_panel.refresh_from_db()
        end_device.refresh_from_db()
        
        power_status = power_source.get_effective_status()
        panel_status = distribution_panel.get_effective_status()
        device_status = end_device.get_effective_status()
        
        self.stdout.write(f'Power Source Status: {power_source.status} → Effective: {power_status}')
        self.stdout.write(f'Distribution Panel Status: {distribution_panel.status} → Effective: {panel_status}')
        self.stdout.write(f'End Device Status: {end_device.status} → Effective: {device_status}')
        
        if (power_status == 'active' and 
            panel_status == 'active' and 
            device_status == 'active'):
            self.stdout.write(self.style.SUCCESS('✅ TEST 3 PASSED: Equipment back online'))
        else:
            self.stdout.write(self.style.ERROR('❌ TEST 3 FAILED'))
        
        # Test 4: Check affected downstream
        self.stdout.write('\n' + '='*60)
        self.stdout.write('TEST 4: Get All Affected Downstream')
        self.stdout.write('='*60)
        
        affected = power_source.get_all_affected_downstream()
        self.stdout.write(f'Affected equipment if power source goes offline:')
        for equip in affected:
            self.stdout.write(f'  - {equip.name}')
        
        if len(affected) == 2 and distribution_panel in affected and end_device in affected:
            self.stdout.write(self.style.SUCCESS('✅ TEST 4 PASSED: Correctly identified affected equipment'))
        else:
            self.stdout.write(self.style.ERROR('❌ TEST 4 FAILED'))
        
        # Test 5: Circular dependency prevention
        self.stdout.write('\n' + '='*60)
        self.stdout.write('TEST 5: Circular Dependency Prevention')
        self.stdout.write('='*60)
        
        try:
            # Try to create a circular connection (end_device → power_source)
            circular_conn = EquipmentConnection(
                upstream_equipment=end_device,
                downstream_equipment=power_source,
                connection_type='power',
                is_critical=True,
                created_by=user
            )
            circular_conn.full_clean()
            circular_conn.save()
            self.stdout.write(self.style.ERROR('❌ TEST 5 FAILED: Circular connection was allowed'))
        except ValidationError as e:
            self.stdout.write(self.style.SUCCESS('✅ TEST 5 PASSED: Circular dependency prevented'))
            self.stdout.write(f'   Error message: {str(e)}')
        
        # Cleanup message
        self.stdout.write('\n' + '='*60)
        self.stdout.write('📝 Test equipment and connections remain for manual testing.')
        self.stdout.write('   To remove: Delete TEST-* equipment from admin or database.')
        self.stdout.write('='*60)

