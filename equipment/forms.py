"""
Forms for equipment management.
"""

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Row, Column, Submit
from .models import Equipment, EquipmentComponent, EquipmentDocument
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
        super().__init__(*args, **kwargs)
        
        # Filter active categories and locations
        self.fields['category'].queryset = EquipmentCategory.objects.filter(is_active=True)
        self.fields['location'].queryset = Location.objects.filter(is_active=True)
        
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
            'document_type', 'title', 'description', 'file',
            'version', 'is_current'
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
                Column('version', css_class='form-group col-md-3 mb-0'),
                Column('is_current', css_class='form-group col-md-3 mb-0'),
            ),
            'title',
            'description',
            'file',
            Submit('submit', 'Save Document', css_class='btn btn-primary')
        )