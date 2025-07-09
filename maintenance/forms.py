"""
Forms for maintenance management.
"""

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Row, Column, Submit
from .models import MaintenanceActivity, MaintenanceSchedule, MaintenanceActivityType
from equipment.models import Equipment
from django.contrib.auth.models import User


class MaintenanceActivityForm(forms.ModelForm):
    """Form for creating and editing maintenance activities."""
    
    class Meta:
        model = MaintenanceActivity
        fields = [
            'equipment', 'activity_type', 'title', 'description',
            'status', 'priority', 'assigned_to',
            'scheduled_start', 'scheduled_end',
            'required_status', 'tools_required', 'parts_required',
            'safety_notes'
        ]
        widgets = {
            'scheduled_start': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'scheduled_end': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'description': forms.Textarea(attrs={'rows': 3}),
            'tools_required': forms.Textarea(attrs={'rows': 2}),
            'parts_required': forms.Textarea(attrs={'rows': 2}),
            'safety_notes': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filter active options
        self.fields['equipment'].queryset = Equipment.objects.filter(is_active=True)
        self.fields['activity_type'].queryset = MaintenanceActivityType.objects.filter(is_active=True)
        self.fields['assigned_to'].queryset = User.objects.filter(is_active=True)
        
        # Setup crispy forms helper
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                'Basic Information',
                Row(
                    Column('equipment', css_class='form-group col-md-6 mb-0'),
                    Column('activity_type', css_class='form-group col-md-6 mb-0'),
                ),
                'title',
                'description',
            ),
            Fieldset(
                'Status & Assignment',
                Row(
                    Column('status', css_class='form-group col-md-4 mb-0'),
                    Column('priority', css_class='form-group col-md-4 mb-0'),
                    Column('assigned_to', css_class='form-group col-md-4 mb-0'),
                ),
            ),
            Fieldset(
                'Scheduling',
                Row(
                    Column('scheduled_start', css_class='form-group col-md-6 mb-0'),
                    Column('scheduled_end', css_class='form-group col-md-6 mb-0'),
                ),
            ),
            Fieldset(
                'Requirements',
                'required_status',
                'tools_required',
                'parts_required',
                'safety_notes',
            ),
            Submit('submit', 'Save Activity', css_class='btn btn-primary')
        )


class MaintenanceScheduleForm(forms.ModelForm):
    """Form for maintenance schedules."""
    
    class Meta:
        model = MaintenanceSchedule
        fields = [
            'equipment', 'activity_type', 'frequency', 'frequency_days',
            'start_date', 'end_date', 'auto_generate', 
            'advance_notice_days', 'is_active'
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filter active options
        self.fields['equipment'].queryset = Equipment.objects.filter(is_active=True)
        self.fields['activity_type'].queryset = MaintenanceActivityType.objects.filter(is_active=True)
        
        # Setup crispy forms helper
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                'Basic Information',
                Row(
                    Column('equipment', css_class='form-group col-md-6 mb-0'),
                    Column('activity_type', css_class='form-group col-md-6 mb-0'),
                ),
            ),
            Fieldset(
                'Frequency',
                Row(
                    Column('frequency', css_class='form-group col-md-6 mb-0'),
                    Column('frequency_days', css_class='form-group col-md-6 mb-0'),
                ),
            ),
            Fieldset(
                'Date Range',
                Row(
                    Column('start_date', css_class='form-group col-md-6 mb-0'),
                    Column('end_date', css_class='form-group col-md-6 mb-0'),
                ),
            ),
            Fieldset(
                'Settings',
                Row(
                    Column('auto_generate', css_class='form-group col-md-4 mb-0'),
                    Column('advance_notice_days', css_class='form-group col-md-4 mb-0'),
                    Column('is_active', css_class='form-group col-md-4 mb-0'),
                ),
            ),
            Submit('submit', 'Save Schedule', css_class='btn btn-primary')
        )


class MaintenanceActivityTypeForm(forms.ModelForm):
    """Form for maintenance activity types."""
    
    class Meta:
        model = MaintenanceActivityType
        fields = [
            'name', 'description', 'estimated_duration_hours',
            'frequency_days', 'is_mandatory', 'is_active'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Setup crispy forms helper
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('name', css_class='form-group col-md-6 mb-0'),
                Column('estimated_duration_hours', css_class='form-group col-md-6 mb-0'),
            ),
            'description',
            Row(
                Column('frequency_days', css_class='form-group col-md-4 mb-0'),
                Column('is_mandatory', css_class='form-group col-md-4 mb-0'),
                Column('is_active', css_class='form-group col-md-4 mb-0'),
            ),
            Submit('submit', 'Save Activity Type', css_class='btn btn-primary')
        )