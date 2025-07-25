# Generated by Django 4.2.7 on 2025-07-14 00:17

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('maintenance', '0002_maintenancereport'),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name='maintenancereport',
            name='maintenance_activit_da135f_idx',
        ),
        migrations.RemoveIndex(
            model_name='maintenancereport',
            name='maintenance_uploade_1f0faa_idx',
        ),
        migrations.RemoveIndex(
            model_name='maintenancereport',
            name='maintenance_is_proc_8bf725_idx',
        ),
        migrations.RemoveField(
            model_name='maintenancereport',
            name='activity',
        ),
        migrations.RemoveField(
            model_name='maintenancereport',
            name='analyzed_data',
        ),
        migrations.RemoveField(
            model_name='maintenancereport',
            name='content',
        ),
        migrations.RemoveField(
            model_name='maintenancereport',
            name='document',
        ),
        migrations.RemoveField(
            model_name='maintenancereport',
            name='is_processed',
        ),
        migrations.RemoveField(
            model_name='maintenancereport',
            name='processing_errors',
        ),
        migrations.RemoveField(
            model_name='maintenancereport',
            name='report_date',
        ),
        migrations.RemoveField(
            model_name='maintenancereport',
            name='summary',
        ),
        migrations.RemoveField(
            model_name='maintenancereport',
            name='technician_name',
        ),
        migrations.RemoveField(
            model_name='maintenancereport',
            name='uploaded_by',
        ),
        migrations.RemoveField(
            model_name='maintenancereport',
            name='work_hours',
        ),
        migrations.AddField(
            model_name='maintenancereport',
            name='approved_at',
            field=models.DateTimeField(blank=True, help_text='When the report was approved', null=True),
        ),
        migrations.AddField(
            model_name='maintenancereport',
            name='approved_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='approved_maintenance_reports', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='maintenancereport',
            name='file',
            field=models.FileField(default=2, help_text='The report file (PDF, DOC, etc.)', upload_to='maintenance/reports/'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='maintenancereport',
            name='findings_summary',
            field=models.TextField(blank=True, help_text='Summary of findings from the report'),
        ),
        migrations.AddField(
            model_name='maintenancereport',
            name='maintenance_activity',
            field=models.ForeignKey(default=2, help_text='The maintenance activity this report belongs to', on_delete=django.db.models.deletion.CASCADE, related_name='reports', to='maintenance.maintenanceactivity'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='maintenancereport',
            name='status',
            field=models.CharField(choices=[('draft', 'Draft'), ('completed', 'Completed'), ('approved', 'Approved')], default='draft', help_text='Current status of the report', max_length=20),
        ),
        migrations.AlterField(
            model_name='maintenancereport',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_maintenance_reports', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='maintenancereport',
            name='report_type',
            field=models.CharField(choices=[('inspection', 'Inspection Report'), ('repair', 'Repair Report'), ('testing', 'Testing Report'), ('dga', 'DGA Report'), ('calibration', 'Calibration Report'), ('other', 'Other Report')], default='other', help_text='Type of maintenance report', max_length=20),
        ),
        migrations.AlterField(
            model_name='maintenancereport',
            name='title',
            field=models.CharField(help_text='Title of the report', max_length=200),
        ),
    ]
