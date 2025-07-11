"""
Forms for core app - managing locations and equipment categories.
"""

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Row, Column, Submit
from .models import Location, EquipmentCategory, Customer


class LocationForm(forms.ModelForm):
    """Form for creating and editing locations."""
    
    class Meta:
        model = Location
        fields = [
            'name', 'parent_location', 'customer', 'is_site', 'address', 
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
        
        # Filter active customers for customer selection
        self.fields['customer'].queryset = Customer.objects.filter(
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
                    Column('customer', css_class='form-group col-md-6 mb-0'),
                    Column('is_site', css_class='form-group col-md-3 mb-0'),
                    Column('is_active', css_class='form-group col-md-3 mb-0'),
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


class CustomerForm(forms.ModelForm):
    """Form for creating and editing customers."""
    
    class Meta:
        model = Customer
        fields = ['name', 'code', 'contact_email', 'contact_phone', 'description', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Setup crispy forms helper
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                'Customer Information',
                Row(
                    Column('name', css_class='form-group col-md-8 mb-0'),
                    Column('code', css_class='form-group col-md-4 mb-0'),
                ),
                Row(
                    Column('contact_email', css_class='form-group col-md-6 mb-0'),
                    Column('contact_phone', css_class='form-group col-md-6 mb-0'),
                ),
                'description',
                'is_active',
            ),
            Submit('submit', 'Save Customer', css_class='btn btn-primary')
        )

    def clean_name(self):
        """Validate customer name."""
        name = self.cleaned_data.get('name')
        if name:
            name = name.strip()
            if not name:
                raise forms.ValidationError("Customer name cannot be empty.")
        return name
    
    def clean_code(self):
        """Validate customer code and auto-generate if needed."""
        code = self.cleaned_data.get('code')
        name = self.cleaned_data.get('name')
        
        if not code and name:
            # Auto-generate code from name
            code = name.upper().replace(' ', '_')[:20]
        
        if code:
            code = code.strip().upper()
            if not code:
                raise forms.ValidationError("Customer code cannot be empty.")
        
        return code