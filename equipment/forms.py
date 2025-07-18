"""
Forms for equipment management.
"""

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Row, Column, Submit
from .models import Equipment, EquipmentComponent, EquipmentDocument, EquipmentCategoryField, EquipmentCustomValue
from core.models import EquipmentCategory, Location


class EquipmentForm(forms.ModelForm):
    """Form for creating and editing equipment."""
    
    class Meta:
        model = Equipment
        fields = [
            'name', 'category', 'status', 'manufacturer_serial', 'asset_tag',
            'location', 'manufacturer', 'model_number', 'power_ratings',
            'trip_setpoints', 'datasheet', 'schematics', 'warranty_details',
            'installed_upgrades', 'dga_due_date', 'next_maintenance_date',
            'commissioning_date', 'warranty_expiry_date', 'is_active'
        ]
        widgets = {
            'dga_due_date': forms.DateInput(attrs={'type': 'date'}),
            'next_maintenance_date': forms.DateInput(attrs={'type': 'date'}),
            'commissioning_date': forms.DateInput(attrs={'type': 'date'}),
            'warranty_expiry_date': forms.DateInput(attrs={'type': 'date'}),
            'warranty_details': forms.Textarea(attrs={'rows': 3}),
            'installed_upgrades': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        # Extract request from kwargs to access session data
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        # Filter active categories
        self.fields['category'].queryset = EquipmentCategory.objects.filter(is_active=True)  # type: ignore
        
        # Get selected site for location filtering
        selected_site = None
        if self.request and hasattr(self.request, 'session'):
            selected_site_id = self.request.GET.get('site_id')
            if selected_site_id is None:
                selected_site_id = self.request.session.get('selected_site_id')
            
            if selected_site_id:
                try:
                    selected_site = Location.objects.get(id=selected_site_id, is_site=True)
                except Location.DoesNotExist:
                    pass
        
        # Filter locations based on selected site
        if selected_site:
            # Only show locations under the selected site
            self.fields['location'].queryset = Location.objects.filter(
                parent_location=selected_site,
                is_active=True
            ).order_by('name')  # type: ignore
        else:
            # Show all non-site locations
            self.fields['location'].queryset = Location.objects.filter(
                is_site=False,
                is_active=True
            ).order_by('name')  # type: ignore
        
        # Setup crispy forms helper
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                'Basic Information',
                Row(
                    Column('name', css_class='form-group col-md-6 mb-0'),
                    Column('category', css_class='form-group col-md-6 mb-0'),
                ),
                Row(
                    Column('status', css_class='form-group col-md-6 mb-0'),
                    Column('is_active', css_class='form-group col-md-6 mb-0'),
                ),
            ),
            Fieldset(
                'Identification',
                Row(
                    Column('manufacturer_serial', css_class='form-group col-md-6 mb-0'),
                    Column('asset_tag', css_class='form-group col-md-6 mb-0'),
                ),
                Row(
                    Column('manufacturer', css_class='form-group col-md-6 mb-0'),
                    Column('model_number', css_class='form-group col-md-6 mb-0'),
                ),
            ),
            Fieldset(
                'Location',
                'location',
            ),
            Fieldset(
                'Technical Specifications',
                Row(
                    Column('power_ratings', css_class='form-group col-md-6 mb-0'),
                    Column('trip_setpoints', css_class='form-group col-md-6 mb-0'),
                ),
                'installed_upgrades',
            ),
            Fieldset(
                'Documentation',
                Row(
                    Column('datasheet', css_class='form-group col-md-6 mb-0'),
                    Column('schematics', css_class='form-group col-md-6 mb-0'),
                ),
                'warranty_details',
            ),
            Fieldset(
                'Maintenance Tracking',
                Row(
                    Column('dga_due_date', css_class='form-group col-md-6 mb-0'),
                    Column('next_maintenance_date', css_class='form-group col-md-6 mb-0'),
                ),
                Row(
                    Column('commissioning_date', css_class='form-group col-md-6 mb-0'),
                    Column('warranty_expiry_date', css_class='form-group col-md-6 mb-0'),
                ),
            ),
            Submit('submit', 'Save Equipment', css_class='btn btn-primary')
        )


class DynamicEquipmentForm(EquipmentForm):
    """Dynamic form that includes custom fields based on equipment category."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add custom fields based on the selected category
        if self.instance and self.instance.pk:
            # Editing existing equipment
            self.add_custom_fields(self.instance.category)
        elif 'category' in self.data:
            # New equipment with category selected
            try:
                category_id = self.data.get('category')
                if category_id:
                    category = EquipmentCategory.objects.get(id=category_id)
                    self.add_custom_fields(category)
            except EquipmentCategory.DoesNotExist:
                pass
    
    def add_custom_fields(self, category):
        """Add custom fields for the given category."""
        if not category:
            return
        
        custom_fields = EquipmentCategoryField.objects.filter(
            category=category,
            is_active=True
        ).order_by('sort_order')
        
        # Group fields by field_group
        field_groups = {}
        for field in custom_fields:
            group = field.field_group or 'General'
            if group not in field_groups:
                field_groups[group] = []
            field_groups[group].append(field)
        
        # Create form fields for each custom field
        for group, fields in field_groups.items():
            for field in fields:
                form_field = self.create_form_field(field)
                if form_field:
                    self.fields[f'custom_{field.name}'] = form_field
                    
                    # Set initial value if editing
                    if self.instance and self.instance.pk:
                        initial_value = self.instance.get_custom_value(field.name)
                        if initial_value:
                            self.fields[f'custom_{field.name}'].initial = initial_value
    
    def create_form_field(self, field):
        """Create a form field based on the custom field definition."""
        field_kwargs = {
            'label': field.label,
            'required': field.required,
            'help_text': field.help_text,
        }
        
        if field.field_type == 'text':
            return forms.CharField(max_length=255, **field_kwargs)
        
        elif field.field_type == 'textarea':
            return forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), **field_kwargs)
        
        elif field.field_type == 'number':
            return forms.IntegerField(**field_kwargs)
        
        elif field.field_type == 'decimal':
            return forms.DecimalField(**field_kwargs)
        
        elif field.field_type == 'date':
            return forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), **field_kwargs)
        
        elif field.field_type == 'datetime':
            return forms.DateTimeField(widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}), **field_kwargs)
        
        elif field.field_type == 'boolean':
            return forms.BooleanField(**field_kwargs)
        
        elif field.field_type == 'select':
            choices = field.get_choices_list()
            return forms.ChoiceField(choices=choices, **field_kwargs)
        
        elif field.field_type == 'multiselect':
            choices = field.get_choices_list()
            return forms.MultipleChoiceField(
                choices=choices,
                widget=forms.CheckboxSelectMultiple,
                **field_kwargs
            )
        
        elif field.field_type == 'url':
            return forms.URLField(**field_kwargs)
        
        elif field.field_type == 'email':
            return forms.EmailField(**field_kwargs)
        
        elif field.field_type == 'phone':
            return forms.CharField(max_length=20, **field_kwargs)
        
        return None
    
    def save(self, commit=True):
        """Save the equipment and its custom field values."""
        equipment = super().save(commit=False)
        
        if commit:
            equipment.save()
            
            # Save custom field values
            for field_name, value in self.cleaned_data.items():
                if field_name.startswith('custom_'):
                    custom_field_name = field_name[7:]  # Remove 'custom_' prefix
                    equipment.set_custom_value(custom_field_name, value)
        
        return equipment


class EquipmentComponentForm(forms.ModelForm):
    """Form for equipment components."""
    
    class Meta:
        model = EquipmentComponent
        fields = [
            'name', 'part_number', 'description', 'quantity',
            'replacement_date', 'next_replacement_date', 'is_critical'
        ]
        widgets = {
            'replacement_date': forms.DateInput(attrs={'type': 'date'}),
            'next_replacement_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('name', css_class='form-group col-md-6 mb-0'),
                Column('part_number', css_class='form-group col-md-6 mb-0'),
            ),
            'description',
            Row(
                Column('quantity', css_class='form-group col-md-4 mb-0'),
                Column('is_critical', css_class='form-group col-md-4 mb-0'),
            ),
            Row(
                Column('replacement_date', css_class='form-group col-md-6 mb-0'),
                Column('next_replacement_date', css_class='form-group col-md-6 mb-0'),
            ),
            Submit('submit', 'Save Component', css_class='btn btn-primary')
        )


class EquipmentDocumentForm(forms.ModelForm):
    """Form for equipment documents."""
    
    class Meta:
        model = EquipmentDocument
        fields = [
            'document_type', 'title', 'description', 'file', 'is_active'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('document_type', css_class='form-group col-md-6 mb-0'),
                Column('is_active', css_class='form-group col-md-6 mb-0'),
            ),
            'title',
            'description',
            'file',
            Submit('submit', 'Save Document', css_class='btn btn-primary')
        )