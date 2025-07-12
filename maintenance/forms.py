"""
Forms for maintenance management.
Enhanced with better UX for activity types.
"""

from django import forms
from django.db.models import Q
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Row, Column, Submit, HTML, Field
from .models import (
    MaintenanceActivity, MaintenanceSchedule, MaintenanceActivityType,
    ActivityTypeCategory, ActivityTypeTemplate
)
from equipment.models import Equipment
from core.models import EquipmentCategory
from django.contrib.auth.models import User


class ActivityTypeCategoryForm(forms.ModelForm):
    """Form for creating and editing activity type categories."""
    
    class Meta:
        model = ActivityTypeCategory
        fields = ['name', 'description', 'color', 'icon', 'sort_order', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2}),
            'color': forms.TextInput(attrs={'type': 'color'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Setup crispy forms helper
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                'Category Information',
                Row(
                    Column('name', css_class='form-group col-md-8 mb-0'),
                    Column('sort_order', css_class='form-group col-md-4 mb-0'),
                ),
                'description',
                Row(
                    Column('color', css_class='form-group col-md-6 mb-0'),
                    Column('icon', css_class='form-group col-md-6 mb-0'),
                ),
                'is_active',
            ),
            Submit('submit', 'Save Category', css_class='btn btn-primary')
        )


class ActivityTypeTemplateForm(forms.ModelForm):
    """Form for creating and editing activity type templates."""
    
    class Meta:
        model = ActivityTypeTemplate
        fields = [
            'name', 'equipment_category', 'category', 'description',
            'estimated_duration_hours', 'frequency_days', 'is_mandatory',
            'default_tools_required', 'default_parts_required', 'default_safety_notes',
            'checklist_template', 'sort_order', 'is_active'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2}),
            'default_tools_required': forms.Textarea(attrs={'rows': 2}),
            'default_parts_required': forms.Textarea(attrs={'rows': 2}),
            'default_safety_notes': forms.Textarea(attrs={'rows': 2}),
            'checklist_template': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Enter each checklist item on a new line'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filter active options
        self.fields['equipment_category'].queryset = EquipmentCategory.objects.filter(is_active=True)
        self.fields['category'].queryset = ActivityTypeCategory.objects.filter(is_active=True)
        
        # Setup crispy forms helper
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                'Basic Information',
                Row(
                    Column('name', css_class='form-group col-md-8 mb-0'),
                    Column('sort_order', css_class='form-group col-md-4 mb-0'),
                ),
                Row(
                    Column('equipment_category', css_class='form-group col-md-6 mb-0'),
                    Column('category', css_class='form-group col-md-6 mb-0'),
                ),
                'description',
            ),
            Fieldset(
                'Timing & Requirements',
                Row(
                    Column('estimated_duration_hours', css_class='form-group col-md-4 mb-0'),
                    Column('frequency_days', css_class='form-group col-md-4 mb-0'),
                    Column('is_mandatory', css_class='form-group col-md-4 mb-0'),
                ),
            ),
            Fieldset(
                'Default Requirements',
                'default_tools_required',
                'default_parts_required',
                'default_safety_notes',
            ),
            Fieldset(
                'Checklist Template',
                'checklist_template',
                HTML('<small class="form-text text-muted">Enter each checklist item on a new line. These will be automatically added when creating activities from this template.</small>')
            ),
            Fieldset(
                'Settings',
                'is_active',
            ),
            Submit('submit', 'Save Template', css_class='btn btn-primary')
        )


class EnhancedMaintenanceActivityTypeForm(forms.ModelForm):
    """Enhanced form for maintenance activity types with better UX."""
    
    # Add a field for selecting from templates
    use_template = forms.BooleanField(
        required=False,
        label="Use Template",
        help_text="Check to populate fields from a template"
    )
    template_selection = forms.ModelChoiceField(
        queryset=ActivityTypeTemplate.objects.none(),
        required=False,
        label="Select Template",
        help_text="Choose a template to populate default values"
    )
    
    class Meta:
        model = MaintenanceActivityType
        fields = [
            'name', 'category', 'template', 'description',
            'estimated_duration_hours', 'frequency_days', 'is_mandatory',
            'tools_required', 'parts_required', 'safety_notes',
            'applicable_equipment_categories', 'is_active'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'tools_required': forms.Textarea(attrs={'rows': 2}),
            'parts_required': forms.Textarea(attrs={'rows': 2}),
            'safety_notes': forms.Textarea(attrs={'rows': 2}),
            'applicable_equipment_categories': forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filter active options
        self.fields['category'].queryset = ActivityTypeCategory.objects.filter(is_active=True)
        self.fields['template'].queryset = ActivityTypeTemplate.objects.filter(is_active=True)
        self.fields['applicable_equipment_categories'].queryset = EquipmentCategory.objects.filter(is_active=True)
        self.fields['template_selection'].queryset = ActivityTypeTemplate.objects.filter(is_active=True)
        
        # Setup crispy forms helper
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                'Template Selection',
                Row(
                    Column('use_template', css_class='form-group col-md-6 mb-0'),
                    Column('template_selection', css_class='form-group col-md-6 mb-0'),
                ),
                HTML('<div id="template-info" class="alert alert-info" style="display: none;"></div>')
            ),
            Fieldset(
                'Basic Information',
                Row(
                    Column('name', css_class='form-group col-md-8 mb-0'),
                    Column('category', css_class='form-group col-md-4 mb-0'),
                ),
                'description',
                Field('template', css_class='d-none'),  # Hidden field to store template reference
            ),
            Fieldset(
                'Timing & Requirements',
                Row(
                    Column('estimated_duration_hours', css_class='form-group col-md-4 mb-0'),
                    Column('frequency_days', css_class='form-group col-md-4 mb-0'),
                    Column('is_mandatory', css_class='form-group col-md-4 mb-0'),
                ),
            ),
            Fieldset(
                'Requirements',
                'tools_required',
                'parts_required',
                'safety_notes',
            ),
            Fieldset(
                'Equipment Categories',
                'applicable_equipment_categories',
                HTML('<small class="form-text text-muted">Select which equipment categories this activity type applies to.</small>')
            ),
            Fieldset(
                'Settings',
                'is_active',
            ),
            Submit('submit', 'Save Activity Type', css_class='btn btn-primary')
        )


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
        # Extract request from kwargs to access session data
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        # Filter active options
        equipment_queryset = Equipment.objects.filter(is_active=True)
        
        # Apply site filtering if a site is selected
        if self.request and hasattr(self.request, 'session'):
            from core.models import Location
            from django.db.models import Q
            
            selected_site_id = self.request.GET.get('site_id')
            if selected_site_id is None:
                selected_site_id = self.request.session.get('selected_site_id')
            
            if selected_site_id:
                try:
                    selected_site = Location.objects.get(id=selected_site_id, is_site=True)
                    equipment_queryset = equipment_queryset.filter(
                        Q(location__parent_location=selected_site) | Q(location=selected_site)
                    )
                except Location.DoesNotExist:
                    pass
        
        self.fields['equipment'].queryset = equipment_queryset.select_related('category')
        self.fields['activity_type'].queryset = MaintenanceActivityType.objects.filter(is_active=True).select_related('category')
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
                HTML('<div id="activity-suggestions" class="alert alert-info" style="display: none;"></div>')
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
        # Extract request from kwargs to access session data
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        # Filter active options
        equipment_queryset = Equipment.objects.filter(is_active=True)
        
        # Apply site filtering if a site is selected
        if self.request and hasattr(self.request, 'session'):
            from core.models import Location
            from django.db.models import Q
            
            selected_site_id = self.request.GET.get('site_id')
            if selected_site_id is None:
                selected_site_id = self.request.session.get('selected_site_id')
            
            if selected_site_id:
                try:
                    selected_site = Location.objects.get(id=selected_site_id, is_site=True)
                    equipment_queryset = equipment_queryset.filter(
                        Q(location__parent_location=selected_site) | Q(location=selected_site)
                    )
                except Location.DoesNotExist:
                    pass
        
        self.fields['equipment'].queryset = equipment_queryset.select_related('category')
        self.fields['activity_type'].queryset = MaintenanceActivityType.objects.filter(is_active=True).select_related('category')
        
        # Setup crispy forms helper
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                'Basic Information',
                Row(
                    Column('equipment', css_class='form-group col-md-6 mb-0'),
                    Column('activity_type', css_class='form-group col-md-6 mb-0'),
                ),
                HTML('<div id="schedule-suggestions" class="alert alert-info" style="display: none;"></div>')
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


# Legacy form for backwards compatibility
class MaintenanceActivityTypeForm(EnhancedMaintenanceActivityTypeForm):
    """Legacy form - use EnhancedMaintenanceActivityTypeForm instead."""
    pass