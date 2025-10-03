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
    ActivityTypeCategory, ActivityTypeTemplate, EquipmentCategorySchedule, GlobalSchedule, ScheduleOverride
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
        
        # Add empty choice for category if no categories exist
        if not self.fields['category'].queryset.exists():
            self.fields['category'].empty_label = "No categories available - please create some first"
            self.fields['category'].required = False
        else:
            self.fields['category'].empty_label = "--- Select Category ---"
        
        # Add empty choice for equipment categories if none exist
        if not self.fields['applicable_equipment_categories'].queryset.exists():
            self.fields['applicable_equipment_categories'].help_text = "No equipment categories available - please create some first"
        
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
    
    # Quick creation fields
    quick_category = forms.CharField(
        max_length=100,
        required=False,
        label="Quick Category",
        help_text="Create a new category on the fly"
    )
    quick_activity_type = forms.CharField(
        max_length=100,
        required=False,
        label="Quick Activity Type",
        help_text="Create a new activity type on the fly"
    )
    
    class Meta:
        model = MaintenanceActivity
        fields = [
            'equipment', 'activity_type', 'title', 'description',
            'status', 'priority', 'assigned_to',
            'scheduled_start', 'scheduled_end', 'timezone',
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

    def clean(self):
        """Custom validation for maintenance activity form."""
        cleaned_data = super().clean()
        scheduled_start = cleaned_data.get('scheduled_start')
        scheduled_end = cleaned_data.get('scheduled_end')
        timezone_str = cleaned_data.get('timezone')
        
        # Handle timezone conversion for datetime-local inputs
        if scheduled_start and timezone_str:
            scheduled_start = self._convert_to_timezone(scheduled_start, timezone_str)
            cleaned_data['scheduled_start'] = scheduled_start
            
        if scheduled_end and timezone_str:
            scheduled_end = self._convert_to_timezone(scheduled_end, timezone_str)
            cleaned_data['scheduled_end'] = scheduled_end
        
        if scheduled_start and scheduled_end:
            # Check if start time is after end time
            if scheduled_start >= scheduled_end:
                raise forms.ValidationError(
                    "Scheduled start time must be before scheduled end time. "
                    "You cannot have a start time that is after or equal to the end time."
                )
            
            # Check if start and end are on the same day
            if scheduled_start.date() == scheduled_end.date():
                # For same-day events, ensure start time is before end time
                if scheduled_start.time() >= scheduled_end.time():
                    raise forms.ValidationError(
                        "For same-day maintenance, the start time must be before the end time. "
                        "For example, you cannot start at 7:00 PM and end at 3:00 PM on the same day."
                    )
        
        return cleaned_data
    
    def _convert_to_timezone(self, naive_datetime, timezone_str):
        """Convert naive datetime to timezone-aware datetime."""
        import pytz
        from django.utils import timezone as django_timezone
        
        if naive_datetime.tzinfo is None:
            # Convert naive datetime to the specified timezone
            try:
                target_tz = pytz.timezone(timezone_str)
                # Localize the naive datetime to the target timezone
                localized_dt = target_tz.localize(naive_datetime)
                # Convert to UTC for storage
                return localized_dt.astimezone(pytz.UTC)
            except (pytz.UnknownTimeZoneError, AttributeError):
                # Fallback to default timezone if conversion fails
                return django_timezone.make_aware(naive_datetime)
        
        return naive_datetime
    
    def _convert_from_utc(self, utc_datetime, timezone_str):
        """Convert UTC datetime to naive datetime in specified timezone for display."""
        import pytz
        
        if utc_datetime and utc_datetime.tzinfo:
            try:
                target_tz = pytz.timezone(timezone_str)
                # Convert from UTC to target timezone
                local_dt = utc_datetime.astimezone(target_tz)
                # Return as naive datetime for datetime-local input
                return local_dt.replace(tzinfo=None)
            except (pytz.UnknownTimeZoneError, AttributeError):
                # Fallback to naive UTC datetime
                return utc_datetime.replace(tzinfo=None)
        
        return utc_datetime
    
    def save(self, commit=True):
        """Save the form and handle quick creation of categories and activity types."""
        instance = super().save(commit=False)
        
        # Handle quick creation of category and activity type
        quick_category = self.cleaned_data.get('quick_category')
        quick_activity_type = self.cleaned_data.get('quick_activity_type')
        
        if quick_category and quick_activity_type:
            from maintenance.models import ActivityTypeCategory, MaintenanceActivityType
            
            # Create category if it doesn't exist
            category, created = ActivityTypeCategory.objects.get_or_create(
                name=quick_category,
                defaults={
                    'description': f'Quick created category: {quick_category}',
                    'color': '#6c757d',
                    'icon': 'fas fa-wrench',
                    'is_active': True,
                    'sort_order': 999,
                }
            )
            
            # Create activity type if it doesn't exist
            activity_type, created = MaintenanceActivityType.objects.get_or_create(
                name=quick_activity_type,
                defaults={
                    'category': category,
                    'description': f'Quick created activity type: {quick_activity_type}',
                    'estimated_duration_hours': 2,
                    'frequency_days': 30,
                    'is_mandatory': False,
                    'is_active': True,
                }
            )
            
            # Set the activity type on the instance
            instance.activity_type = activity_type
        
        if commit:
            instance.save()
        
        return instance

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
                if selected_site_id == 'all':
                    # Handle "All Sites" selection - no filtering needed
                    pass
                else:
                    try:
                        selected_site = Location.objects.get(id=selected_site_id, is_site=True)
                        equipment_queryset = equipment_queryset.filter(
                            Q(location__parent_location=selected_site) | Q(location=selected_site)
                        )
                    except (Location.DoesNotExist, ValueError):
                        pass
        
        self.fields['equipment'].queryset = equipment_queryset.select_related('category')
        
        self.fields['activity_type'].queryset = MaintenanceActivityType.objects.filter(is_active=True).select_related('category')
        self.fields['assigned_to'].queryset = User.objects.filter(is_active=True)
        
        # Handle timezone conversion for datetime fields when editing
        if self.instance and self.instance.pk:
            timezone_str = self.instance.timezone
            if timezone_str:
                # Convert UTC datetimes to the activity's timezone for display
                if self.instance.scheduled_start:
                    self.fields['scheduled_start'].initial = self._convert_from_utc(self.instance.scheduled_start, timezone_str)
                if self.instance.scheduled_end:
                    self.fields['scheduled_end'].initial = self._convert_from_utc(self.instance.scheduled_end, timezone_str)
        
        # Add quick creation options to activity type field
        self.fields['activity_type'].widget.attrs.update({
            'data-quick-create': 'true',
            'data-category-field': 'id_quick_category',
            'data-activity-field': 'id_quick_activity_type'
        })
        
        # Setup crispy forms helper
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                'Basic Information',
                Row(
                    Column('equipment', css_class='form-group col-md-6 mb-0'),
                    Column('activity_type', css_class='form-group col-md-6 mb-0'),
                ),
                HTML('<div class="alert alert-info">' +
                     '<strong>Quick Create:</strong> Can\'t find the activity type you need? ' +
                     '<button type="button" class="btn btn-sm btn-outline-primary ms-2" onclick="toggleQuickCreate()">' +
                     '<i class="fas fa-plus"></i> Create New</button>' +
                     '</div>'),
                HTML('<div id="quick-create-fields" style="display: none;" class="border rounded p-3 mb-3 bg-light">' +
                     '<h6><i class="fas fa-magic"></i> Quick Create Activity Type</h6>' +
                     '<div class="row">' +
                     '<div class="col-md-6">' +
                     '<label for="id_quick_category" class="form-label">New Category</label>' +
                     '<input type="text" class="form-control" id="id_quick_category" name="quick_category" placeholder="e.g., Emergency Maintenance">' +
                     '</div>' +
                     '<div class="col-md-6">' +
                     '<label for="id_quick_activity_type" class="form-label">New Activity Type</label>' +
                     '<input type="text" class="form-control" id="id_quick_activity_type" name="quick_activity_type" placeholder="e.g., Emergency Repair">' +
                     '</div>' +
                     '</div>' +
                     '<small class="text-muted">These will be created automatically when you save the maintenance activity.</small>' +
                     '</div>'),
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
                    Column('scheduled_start', css_class='form-group col-md-4 mb-0'),
                    Column('scheduled_end', css_class='form-group col-md-4 mb-0'),
                    Column('timezone', css_class='form-group col-md-4 mb-0'),
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
                if selected_site_id == 'all':
                    # Handle "All Sites" selection - no filtering needed
                    pass
                else:
                    try:
                        selected_site = Location.objects.get(id=selected_site_id, is_site=True)
                        equipment_queryset = equipment_queryset.filter(
                            Q(location__parent_location=selected_site) | Q(location=selected_site)
                        )
                    except (Location.DoesNotExist, ValueError):
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


class EquipmentCategoryScheduleForm(forms.ModelForm):
    """Form for equipment category schedules."""
    
    class Meta:
        model = EquipmentCategorySchedule
        fields = [
            'equipment_category', 'activity_type', 'frequency', 'frequency_days',
            'auto_generate', 'advance_notice_days', 'is_mandatory', 'is_active',
            'allow_override', 'default_priority', 'default_duration_hours'
        ]
        widgets = {
            'frequency_days': forms.NumberInput(attrs={'min': 1}),
            'advance_notice_days': forms.NumberInput(attrs={'min': 0}),
            'default_duration_hours': forms.NumberInput(attrs={'min': 0.5, 'step': 0.5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filter active options
        self.fields['equipment_category'].queryset = EquipmentCategory.objects.filter(is_active=True)
        self.fields['activity_type'].queryset = MaintenanceActivityType.objects.filter(is_active=True).select_related('category')
        
        # Setup crispy forms helper
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-8'
        
        self.helper.layout = Layout(
            Row(
                Column('equipment_category', css_class='form-group col-md-6 mb-0'),
                Column('activity_type', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('frequency', css_class='form-group col-md-6 mb-0'),
                Column('frequency_days', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('auto_generate', css_class='form-group col-md-4 mb-0'),
                Column('advance_notice_days', css_class='form-group col-md-4 mb-0'),
                Column('is_mandatory', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('is_active', css_class='form-group col-md-4 mb-0'),
                Column('allow_override', css_class='form-group col-md-4 mb-0'),
                Column('default_priority', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('default_duration_hours', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column(
                    Submit('save', 'Save Schedule', css_class='btn btn-primary'),
                    css_class='form-group col-md-6 mb-0'
                ),
                Column(
                    HTML('<a href="{% url "maintenance:category_schedule_list" %}" class="btn btn-secondary">Cancel</a>'),
                    css_class='form-group col-md-6 mb-0'
                ),
                css_class='form-row'
            )
        )


class GlobalScheduleForm(forms.ModelForm):
    """Form for global schedules."""
    
    class Meta:
        model = GlobalSchedule
        fields = [
            'name', 'activity_type', 'frequency', 'frequency_days',
            'auto_generate', 'advance_notice_days', 'is_mandatory', 'is_active',
            'allow_override', 'default_priority', 'default_duration_hours', 'description'
        ]
        widgets = {
            'frequency_days': forms.NumberInput(attrs={'min': 1}),
            'advance_notice_days': forms.NumberInput(attrs={'min': 0}),
            'default_duration_hours': forms.NumberInput(attrs={'min': 0.5, 'step': 0.5}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filter active options
        self.fields['activity_type'].queryset = MaintenanceActivityType.objects.filter(is_active=True).select_related('category')
        
        # Setup crispy forms helper
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-8'
        
        self.helper.layout = Layout(
            Row(
                Column('name', css_class='form-group col-md-6 mb-0'),
                Column('activity_type', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('frequency', css_class='form-group col-md-6 mb-0'),
                Column('frequency_days', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('auto_generate', css_class='form-group col-md-4 mb-0'),
                Column('advance_notice_days', css_class='form-group col-md-4 mb-0'),
                Column('is_mandatory', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('is_active', css_class='form-group col-md-4 mb-0'),
                Column('allow_override', css_class='form-group col-md-4 mb-0'),
                Column('default_priority', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('default_duration_hours', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            'description',
            Row(
                Column(
                    Submit('save', 'Save Global Schedule', css_class='btn btn-primary'),
                    css_class='form-group col-md-6 mb-0'
                ),
                Column(
                    HTML('<a href="{% url "maintenance:global_schedule_list" %}" class="btn btn-secondary">Cancel</a>'),
                    css_class='form-group col-md-6 mb-0'
                ),
                css_class='form-row'
            )
        )


class ScheduleOverrideForm(forms.ModelForm):
    """Form for schedule overrides."""
    
    class Meta:
        model = ScheduleOverride
        fields = [
            'equipment', 'activity_type', 'is_active', 'auto_generate',
            'advance_notice_days', 'custom_frequency', 'custom_frequency_days',
            'default_priority', 'default_duration_hours', 'notes'
        ]
        widgets = {
            'advance_notice_days': forms.NumberInput(attrs={'min': 0}),
            'custom_frequency_days': forms.NumberInput(attrs={'min': 1}),
            'default_duration_hours': forms.NumberInput(attrs={'min': 0.5, 'step': 0.5}),
            'notes': forms.Textarea(attrs={'rows': 3}),
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
                if selected_site_id == 'all':
                    # Handle "All Sites" selection - no filtering needed
                    pass
                else:
                    try:
                        selected_site = Location.objects.get(id=selected_site_id, is_site=True)
                        equipment_queryset = equipment_queryset.filter(
                            Q(location__parent_location=selected_site) | Q(location=selected_site)
                        )
                    except (Location.DoesNotExist, ValueError):
                        pass
        
        self.fields['equipment'].queryset = equipment_queryset.select_related('category')
        self.fields['activity_type'].queryset = MaintenanceActivityType.objects.filter(is_active=True).select_related('category')
        
        # Setup crispy forms helper
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-8'
        
        self.helper.layout = Layout(
            Row(
                Column('equipment', css_class='form-group col-md-6 mb-0'),
                Column('activity_type', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('is_active', css_class='form-group col-md-4 mb-0'),
                Column('auto_generate', css_class='form-group col-md-4 mb-0'),
                Column('advance_notice_days', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('custom_frequency', css_class='form-group col-md-6 mb-0'),
                Column('custom_frequency_days', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('default_priority', css_class='form-group col-md-6 mb-0'),
                Column('default_duration_hours', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            'notes',
            Row(
                Column(
                    Submit('save', 'Save Override', css_class='btn btn-primary'),
                    css_class='form-group col-md-6 mb-0'
                ),
                Column(
                    HTML('<a href="{% url "maintenance:schedule_override_list" %}" class="btn btn-secondary">Cancel</a>'),
                    css_class='form-group col-md-6 mb-0'
                ),
                css_class='form-row'
            )
        )