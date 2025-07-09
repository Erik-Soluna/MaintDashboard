"""
Forms for core app - managing locations and equipment categories.
"""

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Row, Column, Submit
from .models import Location, EquipmentCategory


class LocationForm(forms.ModelForm):
    """Form for creating and editing locations."""
    
    class Meta:
        model = Location
        fields = [
            'name', 'parent_location', 'is_site', 'address', 
            'latitude', 'longitude', 'is_active'
        ]
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
            'latitude': forms.NumberInput(attrs={'step': 'any'}),
            'longitude': forms.NumberInput(attrs={'step': 'any'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filter active locations for parent selection
        self.fields['parent_location'].queryset = Location.objects.filter(
            is_active=True
        ).order_by('name')
        
        # Setup crispy forms helper
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                'Basic Information',
                Row(
                    Column('name', css_class='form-group col-md-6 mb-0'),
                    Column('parent_location', css_class='form-group col-md-6 mb-0'),
                ),
                Row(
                    Column('is_site', css_class='form-group col-md-6 mb-0'),
                    Column('is_active', css_class='form-group col-md-6 mb-0'),
                ),
            ),
            Fieldset(
                'Location Details',
                'address',
                Row(
                    Column('latitude', css_class='form-group col-md-6 mb-0'),
                    Column('longitude', css_class='form-group col-md-6 mb-0'),
                ),
            ),
            Submit('submit', 'Save Location', css_class='btn btn-primary')
        )

    def clean(self):
        """Custom validation for location."""
        cleaned_data = super().clean()
        is_site = cleaned_data.get('is_site')
        parent_location = cleaned_data.get('parent_location')
        
        # Site locations cannot have parent locations
        if is_site and parent_location:
            raise forms.ValidationError("Site locations cannot have a parent location.")
        
        # Non-site locations must have a parent location
        if not is_site and not parent_location:
            raise forms.ValidationError("Non-site locations must have a parent location.")
        
        return cleaned_data


class EquipmentCategoryForm(forms.ModelForm):
    """Form for creating and editing equipment categories."""
    
    class Meta:
        model = EquipmentCategory
        fields = ['name', 'description', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Setup crispy forms helper
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                'Category Information',
                'name',
                'description',
                'is_active',
            ),
            Submit('submit', 'Save Category', css_class='btn btn-primary')
        )

    def clean_name(self):
        """Validate category name."""
        name = self.cleaned_data.get('name')
        if name:
            name = name.strip()
            if not name:
                raise forms.ValidationError("Category name cannot be empty.")
        return name