#!/usr/bin/env python3
"""
Comprehensive test suite for MaintenanceReport model and functionality.
This script tests all aspects of the MaintenanceReport implementation.
"""

import os
import sys
import json
import tempfile
from datetime import timedelta
from django.test import TestCase, Client, TransactionTestCase
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from core.models import Location, EquipmentCategory
from equipment.models import Equipment
from maintenance.models import (
    MaintenanceReport, MaintenanceActivity, MaintenanceActivityType,
    ActivityTypeCategory
)


class MaintenanceReportModelTest(TestCase):
    """Test the MaintenanceReport model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.location = Location.objects.create(name='Test Location', is_site=True)
        self.equipment_category = EquipmentCategory.objects.create(name='Test Category')
        self.equipment = Equipment.objects.create(
            name='Test Equipment',
            category=self.equipment_category,
            location=self.location
        )
        self.activity_category = ActivityTypeCategory.objects.create(name='Preventive')
        self.activity_type = MaintenanceActivityType.objects.create(
            name='T-A-1',
            category=self.activity_category,
            frequency_days=30
        )
        self.activity = MaintenanceActivity.objects.create(
            equipment=self.equipment,
            activity_type=self.activity_type,
            title='Test Activity',
            scheduled_start=timezone.now(),
            scheduled_end=timezone.now() + timedelta(hours=2),
            created_by=self.user,
            updated_by=self.user
        )
    
    def test_maintenance_report_creation(self):
        """Test creating a maintenance report."""
        report = MaintenanceReport.objects.create(
            activity=self.activity,
            title='Test Report',
            content='This is a test maintenance report.',
            uploaded_by=self.user,
            created_by=self.user,
            updated_by=self.user
        )
        
        self.assertEqual(report.title, 'Test Report')
        self.assertEqual(report.content, 'This is a test maintenance report.')
        self.assertEqual(report.uploaded_by, self.user)
        self.assertFalse(report.is_processed)
        self.assertEqual(report.analyzed_data, {})
    
    def test_report_string_representation(self):
        """Test the string representation of a report."""
        report = MaintenanceReport.objects.create(
            activity=self.activity,
            title='Test Report',
            uploaded_by=self.user,
            created_by=self.user,
            updated_by=self.user
        )
        
        self.assertEqual(str(report), 'Test Report')
    
    def test_file_extension_method(self):
        """Test getting file extension."""
        report = MaintenanceReport.objects.create(
            activity=self.activity,
            title='Test Report',
            uploaded_by=self.user,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Test without file
        self.assertEqual(report.get_file_extension(), '')
        
        # Test with file (would need actual file upload in real scenario)
        # This is a placeholder for when file upload is implemented
    
    def test_file_size_methods(self):
        """Test file size calculation methods."""
        report = MaintenanceReport.objects.create(
            activity=self.activity,
            title='Test Report',
            uploaded_by=self.user,
            created_by=self.user,
            updated_by=self.user
        )
        
        # Test without file
        self.assertEqual(report.get_file_size_mb(), 0)
        self.assertEqual(report.get_file_size_kb(), 0)
        self.assertEqual(report.get_file_size_formatted(), '0 KB')
    
    def test_analyzed_data_extraction_methods(self):
        """Test methods for extracting analyzed data."""
        analyzed_data = {
            'issues': [
                {'text': 'High temperature', 'severity': 'critical'},
                {'text': 'Minor vibration', 'severity': 'low'}
            ],
            'parts_replaced': [
                {'part': 'Air filter', 'position': 100}
            ],
            'measurements': [
                {'value': 85.0, 'unit': '°C', 'position': 50}
            ]
        }
        
        report = MaintenanceReport.objects.create(
            activity=self.activity,
            title='Test Report',
            analyzed_data=analyzed_data,
            uploaded_by=self.user,
            created_by=self.user,
            updated_by=self.user
        )
        
        self.assertEqual(len(report.get_issues()), 2)
        self.assertEqual(len(report.get_critical_issues()), 1)
        self.assertEqual(len(report.get_parts_replaced()), 1)
        self.assertEqual(len(report.get_measurements()), 1)
    
    def test_critical_issues_detection(self):
        """Test detection of critical issues."""
        analyzed_data = {
            'issues': [
                {'text': 'Critical temperature problem', 'severity': 'critical'},
                {'text': 'Minor issue', 'severity': 'low'}
            ]
        }
        
        report = MaintenanceReport.objects.create(
            activity=self.activity,
            title='Test Report',
            analyzed_data=analyzed_data,
            uploaded_by=self.user,
            created_by=self.user,
            updated_by=self.user
        )
        
        self.assertTrue(report.has_critical_issues())
        critical_issues = report.get_critical_issues()
        self.assertEqual(len(critical_issues), 1)
        self.assertEqual(critical_issues[0]['severity'], 'critical')
    
    def test_priority_score_calculation(self):
        """Test priority score calculation."""
        analyzed_data = {
            'issues': [
                {'text': 'Critical issue', 'severity': 'critical'},
                {'text': 'High priority issue', 'severity': 'high'}
            ]
        }
        
        report = MaintenanceReport.objects.create(
            activity=self.activity,
            title='Test Report',
            analyzed_data=analyzed_data,
            uploaded_by=self.user,
            created_by=self.user,
            updated_by=self.user
        )
        
        score = report.get_priority_score()
        self.assertGreater(score, 0)
        self.assertLessEqual(score, 100)


class MaintenanceReportViewsTest(TransactionTestCase):
    """Test the maintenance report views."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.client.login(username='testuser', password='testpass123')
        
        self.location = Location.objects.create(name='Test Location', is_site=True)
        self.equipment_category = EquipmentCategory.objects.create(name='Test Category')
        self.equipment = Equipment.objects.create(
            name='Test Equipment',
            category=self.equipment_category,
            location=self.location
        )
        self.activity_category = ActivityTypeCategory.objects.create(name='Preventive')
        self.activity_type = MaintenanceActivityType.objects.create(
            name='T-A-1',
            category=self.activity_category,
            frequency_days=30
        )
        self.activity = MaintenanceActivity.objects.create(
            equipment=self.equipment,
            activity_type=self.activity_type,
            title='Test Activity',
            scheduled_start=timezone.now(),
            scheduled_end=timezone.now() + timedelta(hours=2),
            created_by=self.user,
            updated_by=self.user
        )
    
    def test_report_list_view(self):
        """Test the report list view."""
        report = MaintenanceReport.objects.create(
            activity=self.activity,
            title='Test Report',
            uploaded_by=self.user,
            created_by=self.user,
            updated_by=self.user
        )
        
        response = self.client.get(reverse('maintenance:report_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Report')
    
    def test_report_detail_view(self):
        """Test the report detail view."""
        report = MaintenanceReport.objects.create(
            activity=self.activity,
            title='Test Report',
            content='Test content',
            uploaded_by=self.user,
            created_by=self.user,
            updated_by=self.user
        )
        
        response = self.client.get(reverse('maintenance:report_detail', args=[report.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Report')
        self.assertContains(response, 'Test content')
    
    def test_upload_report_view(self):
        """Test uploading a new report."""
        data = {
            'activity_id': self.activity.id,
            'title': 'New Report',
            'content': 'This is a new report.',
            'report_type': 'maintenance'
        }
        
        response = self.client.post(reverse('maintenance:upload_report'), data)
        self.assertEqual(response.status_code, 200)
        
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        
        # Check that report was created
        report = MaintenanceReport.objects.get(title='New Report')
        self.assertEqual(report.content, 'This is a new report.')
    
    def test_analyze_report_view(self):
        """Test analyzing a report."""
        report = MaintenanceReport.objects.create(
            activity=self.activity,
            title='Test Report',
            content='Issues: Critical temperature problem. Parts replaced: Air filter. Work hours: 4 hours.',
            uploaded_by=self.user,
            created_by=self.user,
            updated_by=self.user
        )
        
        response = self.client.post(reverse('maintenance:analyze_report', args=[report.id]))
        self.assertEqual(response.status_code, 200)
        
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        
        # Refresh report from database
        report.refresh_from_db()
        self.assertTrue(report.is_processed)
        self.assertIn('issues', report.analyzed_data)
        self.assertIn('parts_replaced', report.analyzed_data)
    
    def test_get_reports_for_equipment_view(self):
        """Test getting reports for specific equipment."""
        report = MaintenanceReport.objects.create(
            activity=self.activity,
            title='Test Report',
            uploaded_by=self.user,
            created_by=self.user,
            updated_by=self.user
        )
        
        response = self.client.get(reverse('maintenance:get_reports_for_equipment', args=[self.equipment.id]))
        self.assertEqual(response.status_code, 200)
        
        response_data = json.loads(response.content)
        self.assertIn('reports', response_data)
        self.assertEqual(len(response_data['reports']), 1)
        self.assertEqual(response_data['reports'][0]['title'], 'Test Report')


class MaintenanceReportAnalysisTest(TestCase):
    """Test the report analysis functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.location = Location.objects.create(name='Test Location', is_site=True)
        self.equipment_category = EquipmentCategory.objects.create(name='Test Category')
        self.equipment = Equipment.objects.create(
            name='Test Equipment',
            category=self.equipment_category,
            location=self.location
        )
        self.activity_category = ActivityTypeCategory.objects.create(name='Preventive')
        self.activity_type = MaintenanceActivityType.objects.create(
            name='T-A-1',
            category=self.activity_category,
            frequency_days=30
        )
        self.activity = MaintenanceActivity.objects.create(
            equipment=self.equipment,
            activity_type=self.activity_type,
            title='Test Activity',
            scheduled_start=timezone.now(),
            scheduled_end=timezone.now() + timedelta(hours=2),
            created_by=self.user,
            updated_by=self.user
        )
    
    def test_issue_extraction(self):
        """Test extraction of issues from report content."""
        from maintenance.views import analyze_report_content
        
        content = """
        Issues found:
        - Critical temperature reading of 85°C
        - Minor issue: Slight vibration in operation
        - Major problem: Oil pressure low
        """
        
        analyzed_data = analyze_report_content(content)
        
        self.assertIn('issues', analyzed_data)
        issues = analyzed_data['issues']
        self.assertGreater(len(issues), 0)
        
        # Check that critical issues are detected
        critical_issues = [issue for issue in issues if issue['severity'] == 'critical']
        self.assertGreater(len(critical_issues), 0)
        
        # Check that the critical issue contains "critical"
        critical_texts = [issue['text'] for issue in critical_issues]
        self.assertTrue(any('critical' in text.lower() for text in critical_texts))
    
    def test_parts_extraction(self):
        """Test extraction of parts replaced from report content."""
        from maintenance.views import analyze_report_content
        
        content = """
        Parts replaced:
        - Replaced air filter
        - Changed oil filter
        - Installed new spark plugs
        """
        
        analyzed_data = analyze_report_content(content)
        
        self.assertIn('parts_replaced', analyzed_data)
        parts = analyzed_data['parts_replaced']
        self.assertGreater(len(parts), 0)
        self.assertIn('air filter', parts[0]['part'].lower())
    
    def test_measurement_extraction(self):
        """Test extraction of measurements from report content."""
        from maintenance.views import analyze_report_content
        
        content = """
        Measurements taken:
        - Temperature: 85°C
        - Pressure: 120 psi
        - RPM: 1800 rpm
        - Voltage: 24V
        """
        
        analyzed_data = analyze_report_content(content)
        
        self.assertIn('measurements', analyzed_data)
        measurements = analyzed_data['measurements']
        self.assertGreater(len(measurements), 0)
        
        # Check that numeric values are extracted
        for measurement in measurements:
            self.assertIsInstance(measurement['value'], (int, float))
            self.assertIn('unit', measurement)
    
    def test_work_hours_extraction(self):
        """Test extraction of work hours from report content."""
        from maintenance.views import analyze_report_content
        
        content = """
        Work completed in 4.5 hours by technician John Smith.
        Total time spent: 6 hours including setup and cleanup.
        """
        
        analyzed_data = analyze_report_content(content)
        
        self.assertIn('work_hours', analyzed_data)
        self.assertEqual(analyzed_data['work_hours'], 4.5)
    
    def test_date_extraction(self):
        """Test extraction of dates from report content."""
        from maintenance.views import analyze_report_content
        
        content = """
        Report date: 2024-01-15
        Work completed on 01/15/2024
        Next maintenance due: 2024-02-15
        """
        
        analyzed_data = analyze_report_content(content)
        
        self.assertIn('dates', analyzed_data)
        dates = analyzed_data['dates']
        self.assertGreater(len(dates), 0)
        
        # Check that dates are found
        date_strings = [date['date'] for date in dates]
        self.assertIn('2024-01-15', date_strings)


def run_tests():
    """Run all tests and display results."""
    print("=" * 60)
    print("MAINTENANCE REPORT TEST SUITE")
    print("=" * 60)
    
    # Import test classes
    from django.test.utils import get_runner
    from django.conf import settings
    
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    
    # Run tests
    failures = test_runner.run_tests([
        'test_maintenance_reports.MaintenanceReportModelTest',
        'test_maintenance_reports.MaintenanceReportViewsTest',
        'test_maintenance_reports.MaintenanceReportAnalysisTest'
    ])
    
    if failures:
        print(f"\n❌ {len(failures)} test(s) failed!")
        return False
    else:
        print("\n✅ All tests passed!")
        return True


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1) 