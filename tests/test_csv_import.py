"""
Automated tests for CSV import functionality.
Tests location hierarchy creation, validation, error handling, and progress tracking.
"""

import os
import tempfile
import csv
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.messages import get_messages

from equipment.models import Equipment, EquipmentCategory
from core.models import Location


class CSVImportTestCase(TestCase):
    """Test case for CSV import functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.client.login(username='testuser', password='testpass123')
        
        # Create base category
        self.category = EquipmentCategory.objects.create(
            name='Test Category',
            description='Test category for imports',
            created_by=self.user
        )
    
    def create_test_csv(self, data, filename='test.csv'):
        """Create a temporary CSV file for testing."""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        writer = csv.writer(temp_file)
        writer.writerows(data)
        temp_file.close()
        
        # Read the file and create SimpleUploadedFile
        with open(temp_file.name, 'rb') as f:
            uploaded_file = SimpleUploadedFile(
                filename,
                f.read(),
                content_type='text/csv'
            )
        
        # Clean up temp file
        os.unlink(temp_file.name)
        return uploaded_file
    
    def test_basic_import_success(self):
        """Test successful import of basic equipment data."""
        csv_data = [
            ['Name', 'Category', 'Manufacturer Serial', 'Asset Tag', 'Location', 'Status'],
            ['Test Equipment 1', 'Test Category', 'SER001', 'TAG001', 'Site A > Building 1', 'active'],
            ['Test Equipment 2', 'Test Category', 'SER002', 'TAG002', 'Site A > Building 2', 'active'],
        ]
        
        csv_file = self.create_test_csv(csv_data)
        
        response = self.client.post(
            reverse('equipment:import_equipment_csv'),
            {'csv_file': csv_file},
            follow=True
        )
        
        # Check response
        self.assertEqual(response.status_code, 200)
        
        # Check that equipment was created
        self.assertEqual(Equipment.objects.count(), 2)
        
        # Check that locations were created
        self.assertEqual(Location.objects.filter(is_site=True).count(), 1)  # Site A
        self.assertEqual(Location.objects.filter(is_site=False).count(), 2)  # Building 1, Building 2
        
        # Check specific equipment
        eq1 = Equipment.objects.get(manufacturer_serial='SER001')
        self.assertEqual(eq1.name, 'Test Equipment 1')
        self.assertEqual(eq1.location.name, 'Building 1')
        self.assertEqual(eq1.location.parent_location.name, 'Site A')
        
        # Check messages
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Successfully imported 2 equipment items' in str(msg) for msg in messages))
    
    def test_location_hierarchy_creation(self):
        """Test creation of multi-level location hierarchies."""
        csv_data = [
            ['Name', 'Category', 'Manufacturer Serial', 'Asset Tag', 'Location', 'Status'],
            ['Deep Equipment', 'Test Category', 'SER003', 'TAG003', 'Site B > Floor 1 > Room 101 > Cabinet A', 'active'],
        ]
        
        csv_file = self.create_test_csv(csv_data)
        
        response = self.client.post(
            reverse('equipment:import_equipment_csv'),
            {'csv_file': csv_file},
            follow=True
        )
        
        # Check that all location levels were created
        site_b = Location.objects.get(name='Site B', is_site=True)
        floor_1 = Location.objects.get(name='Floor 1', parent_location=site_b)
        room_101 = Location.objects.get(name='Room 101', parent_location=floor_1)
        cabinet_a = Location.objects.get(name='Cabinet A', parent_location=room_101)
        
        # Check hierarchy
        self.assertEqual(cabinet_a.get_full_path(), 'Site B > Floor 1 > Room 101 > Cabinet A')
        
        # Check equipment location
        equipment = Equipment.objects.get(manufacturer_serial='SER003')
        self.assertEqual(equipment.location, cabinet_a)
    
    def test_validation_errors(self):
        """Test validation error handling."""
        csv_data = [
            ['Name', 'Category', 'Manufacturer Serial', 'Asset Tag', 'Location', 'Status'],
            ['', 'Test Category', 'SER004', 'TAG004', 'Site C', 'active'],  # Missing name
            ['Test Equipment 5', 'Test Category', '', 'TAG005', 'Site C', 'active'],  # Missing serial
            ['Test Equipment 6', 'Test Category', 'SER006', 'TAG006', 'Invalid<Chars>Location', 'active'],  # Invalid chars
        ]
        
        csv_file = self.create_test_csv(csv_data)
        
        response = self.client.post(
            reverse('equipment:import_equipment_csv'),
            {'csv_file': csv_file},
            follow=True
        )
        
        # Check that no equipment was created due to validation errors
        self.assertEqual(Equipment.objects.count(), 0)
        
        # Check error messages
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('validation errors' in str(msg).lower() for msg in messages))
        self.assertTrue(any('3 rows had errors' in str(msg) for msg in messages))
    
    def test_missing_required_columns(self):
        """Test handling of missing required columns."""
        csv_data = [
            ['Name', 'Category'],  # Missing Manufacturer Serial
            ['Test Equipment', 'Test Category'],
        ]
        
        csv_file = self.create_test_csv(csv_data)
        
        response = self.client.post(
            reverse('equipment:import_equipment_csv'),
            {'csv_file': csv_file},
            follow=True
        )
        
        # Check error message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Missing required columns' in str(msg) for msg in messages))
        
        # Check that no equipment was created
        self.assertEqual(Equipment.objects.count(), 0)
    
    def test_duplicate_serial_handling(self):
        """Test handling of duplicate manufacturer serials."""
        # Create existing equipment first
        existing_location = Location.objects.create(
            name='Existing Site',
            is_site=True,
            created_by=self.user
        )
        
        Equipment.objects.create(
            name='Existing Equipment',
            category=self.category,
            manufacturer_serial='DUPLICATE001',
            asset_tag='EXISTING001',
            location=existing_location,
            created_by=self.user
        )
        
        # Try to import equipment with same serial
        csv_data = [
            ['Name', 'Category', 'Manufacturer Serial', 'Asset Tag', 'Location', 'Status'],
            ['New Equipment', 'Test Category', 'DUPLICATE001', 'NEW001', 'Site D', 'active'],
        ]
        
        csv_file = self.create_test_csv(csv_data)
        
        response = self.client.post(
            reverse('equipment:import_equipment_csv'),
            {'csv_file': csv_file},
            follow=True
        )
        
        # Check that no new equipment was created
        self.assertEqual(Equipment.objects.count(), 1)
        
        # Check warning message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('1 rows had errors' in str(msg) for msg in messages))
    
    def test_existing_location_reuse(self):
        """Test that existing locations are reused instead of duplicated."""
        # Create existing location hierarchy
        existing_site = Location.objects.create(
            name='Existing Site',
            is_site=True,
            created_by=self.user
        )
        
        existing_building = Location.objects.create(
            name='Existing Building',
            parent_location=existing_site,
            is_site=False,
            created_by=self.user
        )
        
        # Import equipment using same location path
        csv_data = [
            ['Name', 'Category', 'Manufacturer Serial', 'Asset Tag', 'Location', 'Status'],
            ['Reuse Test', 'Test Category', 'SER007', 'TAG007', 'Existing Site > Existing Building', 'active'],
        ]
        
        csv_file = self.create_test_csv(csv_data)
        
        response = self.client.post(
            reverse('equipment:import_equipment_csv'),
            {'csv_file': csv_file},
            follow=True
        )
        
        # Check that equipment was created
        self.assertEqual(Equipment.objects.count(), 1)
        
        # Check that no new locations were created
        self.assertEqual(Location.objects.count(), 2)  # Site + Building
        
        # Check that equipment uses existing location
        equipment = Equipment.objects.get(manufacturer_serial='SER007')
        self.assertEqual(equipment.location, existing_building)
    
    def test_single_location_as_site(self):
        """Test that single location names are treated as sites."""
        csv_data = [
            ['Name', 'Category', 'Manufacturer Serial', 'Asset Tag', 'Location', 'Status'],
            ['Site Equipment', 'Test Category', 'SER008', 'TAG008', 'Single Site', 'active'],
        ]
        
        csv_file = self.create_test_csv(csv_data)
        
        response = self.client.post(
            reverse('equipment:import_equipment_csv'),
            {'csv_file': csv_file},
            follow=True
        )
        
        # Check that location was created as a site
        single_site = Location.objects.get(name='Single Site')
        self.assertTrue(single_site.is_site)
        
        # Check that equipment was assigned to the site
        equipment = Equipment.objects.get(manufacturer_serial='SER008')
        self.assertEqual(equipment.location, single_site)
    
    def test_field_length_validation(self):
        """Test validation of field length limits."""
        # Create extremely long names
        long_name = 'A' * 201  # Exceeds 200 character limit
        long_serial = 'B' * 101  # Exceeds 100 character limit
        
        csv_data = [
            ['Name', 'Category', 'Manufacturer Serial', 'Asset Tag', 'Location', 'Status'],
            [long_name, 'Test Category', 'SER009', 'TAG009', 'Site E', 'active'],
            ['Normal Name', 'Test Category', long_serial, 'TAG010', 'Site E', 'active'],
        ]
        
        csv_file = self.create_test_csv(csv_data)
        
        response = self.client.post(
            reverse('equipment:import_equipment_csv'),
            {'csv_file': csv_file},
            follow=True
        )
        
        # Check that no equipment was created due to validation errors
        self.assertEqual(Equipment.objects.count(), 0)
        
        # Check error messages
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('validation errors' in str(msg).lower() for msg in messages))
    
    def test_progress_tracking(self):
        """Test that progress indicators work for large imports."""
        # Create CSV with many rows to test progress tracking
        csv_data = [['Name', 'Category', 'Manufacturer Serial', 'Asset Tag', 'Location', 'Status']]
        
        # Add 25 rows (should trigger progress indicators every 10 rows)
        for i in range(25):
            csv_data.append([
                f'Equipment {i+1}',
                'Test Category',
                f'SER{i+1:03d}',
                f'TAG{i+1:03d}',
                f'Site F > Building {i+1}',
                'active'
            ])
        
        csv_file = self.create_test_csv(csv_data)
        
        response = self.client.post(
            reverse('equipment:import_equipment_csv'),
            {'csv_file': csv_file},
            follow=True
        )
        
        # Check that all equipment was created
        self.assertEqual(Equipment.objects.count(), 25)
        
        # Check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Successfully imported 25 equipment items' in str(msg) for msg in messages))
    
    def test_date_parsing(self):
        """Test parsing of date fields."""
        csv_data = [
            ['Name', 'Category', 'Manufacturer Serial', 'Asset Tag', 'Location', 'Status', 'DGA Due Date', 'Next Maintenance Date'],
            ['Date Test', 'Test Category', 'SER010', 'TAG010', 'Site G', 'active', '2025-06-15', '2025-07-20'],
        ]
        
        csv_file = self.create_test_csv(csv_data)
        
        response = self.client.post(
            reverse('equipment:import_equipment_csv'),
            {'csv_file': csv_file},
            follow=True
        )
        
        # Check that equipment was created with dates
        equipment = Equipment.objects.get(manufacturer_serial='SER010')
        self.assertIsNotNone(equipment.dga_due_date)
        self.assertIsNotNone(equipment.next_maintenance_date)
        
        # Check specific dates
        self.assertEqual(equipment.dga_due_date.year, 2025)
        self.assertEqual(equipment.dga_due_date.month, 6)
        self.assertEqual(equipment.dga_due_date.day, 15)
    
    def test_asset_tag_auto_generation(self):
        """Test automatic asset tag generation when missing."""
        csv_data = [
            ['Name', 'Category', 'Manufacturer Serial', 'Location', 'Status'],
            ['Auto Tag Test', 'Test Category', 'SER011', 'Site H', 'active'],
        ]
        
        csv_file = self.create_test_csv(csv_data)
        
        response = self.client.post(
            reverse('equipment:import_equipment_csv'),
            {'csv_file': csv_file},
            follow=True
        )
        
        # Check that equipment was created with auto-generated asset tag
        equipment = Equipment.objects.get(manufacturer_serial='SER011')
        self.assertEqual(equipment.asset_tag, 'AUTO_SER011')
    
    def test_comprehensive_import_summary(self):
        """Test comprehensive import summary with mixed results."""
        csv_data = [
            ['Name', 'Category', 'Manufacturer Serial', 'Asset Tag', 'Location', 'Status'],
            ['Valid 1', 'Test Category', 'SER012', 'TAG012', 'Site I > Building 1', 'active'],
            ['Valid 2', 'Test Category', 'SER013', 'TAG013', 'Site I > Building 2', 'active'],
            ['', 'Test Category', 'SER014', 'TAG014', 'Site I > Building 3', 'active'],  # Invalid: missing name
            ['Valid 3', 'Test Category', 'SER015', 'TAG015', 'Site I > Building 4', 'active'],
        ]
        
        csv_file = self.create_test_csv(csv_data)
        
        response = self.client.post(
            reverse('equipment:import_equipment_csv'),
            {'csv_file': csv_file},
            follow=True
        )
        
        # Check that 3 valid equipment items were created
        self.assertEqual(Equipment.objects.count(), 3)
        
        # Check that 1 site and 4 buildings were created
        self.assertEqual(Location.objects.filter(is_site=True).count(), 1)
        self.assertEqual(Location.objects.filter(is_site=False).count(), 4)
        
        # Check messages
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Successfully imported 3 equipment items' in str(msg) for msg in messages))
        self.assertTrue(any('1 rows had errors' in str(msg) for msg in messages))
        self.assertTrue(any('Created 1 new sites' in str(msg) for msg in messages))
        self.assertTrue(any('Created 4 new locations' in str(msg) for msg in messages))


class CSVImportIntegrationTest(TestCase):
    """Integration tests for CSV import with real file handling."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='integrationuser',
            password='testpass123',
            email='integration@example.com'
        )
        self.client.login(username='integrationuser', password='testpass123')
        
        # Create base category
        self.category = EquipmentCategory.objects.create(
            name='Integration Category',
            description='Category for integration tests',
            created_by=self.user
        )
    
    def test_large_file_import_performance(self):
        """Test performance with larger CSV files."""
        # Create CSV with 100 rows
        csv_data = [['Name', 'Category', 'Manufacturer Serial', 'Asset Tag', 'Location', 'Status']]
        
        for i in range(100):
            csv_data.append([
                f'Performance Test {i+1}',
                'Integration Category',
                f'PERF{i+1:03d}',
                f'PERF{i+1:03d}',
                f'Performance Site > Building {(i % 10) + 1} > Room {(i % 5) + 1}',
                'active'
            ])
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as temp_file:
            writer = csv.writer(temp_file)
            writer.writerows(csv_data)
            temp_file_path = temp_file.name
        
        try:
            # Read file and create upload
            with open(temp_file_path, 'rb') as f:
                csv_file = SimpleUploadedFile(
                    'performance_test.csv',
                    f.read(),
                    content_type='text/csv'
                )
            
            # Time the import
            import time
            start_time = time.time()
            
            response = self.client.post(
                reverse('equipment:import_equipment_csv'),
                {'csv_file': csv_file},
                follow=True
            )
            
            end_time = time.time()
            import_duration = end_time - start_time
            
            # Check response
            self.assertEqual(response.status_code, 200)
            
            # Check that all equipment was created
            self.assertEqual(Equipment.objects.count(), 100)
            
            # Check performance (should complete within reasonable time)
            self.assertLess(import_duration, 30.0)  # Should complete within 30 seconds
            
            # Check success message
            messages = list(get_messages(response.wsgi_request))
            self.assertTrue(any('Successfully imported 100 equipment items' in str(msg) for msg in messages))
            
        finally:
            # Clean up temp file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
    
    def test_malformed_csv_handling(self):
        """Test handling of malformed CSV files."""
        # Create CSV with inconsistent column counts
        csv_data = [
            ['Name', 'Category', 'Manufacturer Serial', 'Asset Tag', 'Location', 'Status'],
            ['Valid Row', 'Test Category', 'SER016', 'TAG016', 'Site J', 'active'],
            ['Invalid Row', 'Test Category', 'SER017'],  # Missing columns
            ['Another Valid', 'Test Category', 'SER018', 'TAG018', 'Site J', 'active'],
        ]
        
        csv_file = self.create_test_csv(csv_data)
        
        response = self.client.post(
            reverse('equipment:import_equipment_csv'),
            {'csv_file': csv_file},
            follow=True
        )
        
        # Check that only valid rows were processed
        self.assertEqual(Equipment.objects.count(), 2)
        
        # Check error messages
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('1 rows had errors' in str(msg) for msg in messages))
    
    def create_test_csv(self, data, filename='test.csv'):
        """Create a temporary CSV file for testing."""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        writer = csv.writer(temp_file)
        writer.writerows(data)
        temp_file.close()
        
        # Read the file and create SimpleUploadedFile
        with open(temp_file.name, 'rb') as f:
            uploaded_file = SimpleUploadedFile(
                filename,
                f.read(),
                content_type='text/csv'
            )
        
        # Clean up temp file
        os.unlink(temp_file.name)
        return uploaded_file


if __name__ == '__main__':
    # Run tests directly if script is executed
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maintenance_dashboard.settings')
    django.setup()
    
    # Run tests
    import unittest
    unittest.main()
