"""
Forms for core app - managing locations and equipment categories.
"""

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Row, Column, Submit
from .models import Location, EquipmentCategory, Customer, BrandingSettings, CSSCustomization


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
        self.fields['parent_location'].queryset = Location.objects.filter(  # type: ignore
            is_active=True
        ).order_by('name')
        
        # Filter active customers for customer selection
        self.fields['customer'].queryset = Customer.objects.filter(  # type: ignore
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
        is_site = cleaned_data.get('is_site')  # type: ignore
        parent_location = cleaned_data.get('parent_location')  # type: ignore
        
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

class BrandingSettingsForm(forms.ModelForm):
    """Form for editing branding settings"""
    
    class Meta:
        model = BrandingSettings
        fields = [
            'site_name', 'site_tagline', 'window_title_prefix', 'window_title_suffix',
            'header_brand_text', 'logo', 'favicon',
            'navigation_overview_label', 'navigation_equipment_label', 
            'navigation_maintenance_label', 'navigation_calendar_label',
            'navigation_map_label', 'navigation_settings_label', 'navigation_debug_label',
            'footer_copyright_text', 'footer_powered_by_text',
            'primary_color', 'secondary_color', 'accent_color'
        ]
        widgets = {
            'site_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter site name'}),
            'site_tagline': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter optional tagline'}),
            'window_title_prefix': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., SOLUNA -'}),
            'window_title_suffix': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., - Maintenance System'}),
            'header_brand_text': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Text displayed next to logo'}),
            'logo': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'favicon': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'navigation_overview_label': forms.TextInput(attrs={'class': 'form-control'}),
            'navigation_equipment_label': forms.TextInput(attrs={'class': 'form-control'}),
            'navigation_maintenance_label': forms.TextInput(attrs={'class': 'form-control'}),
            'navigation_calendar_label': forms.TextInput(attrs={'class': 'form-control'}),
            'navigation_map_label': forms.TextInput(attrs={'class': 'form-control'}),
            'navigation_settings_label': forms.TextInput(attrs={'class': 'form-control'}),
            'navigation_debug_label': forms.TextInput(attrs={'class': 'form-control'}),
            'footer_copyright_text': forms.TextInput(attrs={'class': 'form-control'}),
            'footer_powered_by_text': forms.TextInput(attrs={'class': 'form-control'}),
            'primary_color': forms.TextInput(attrs={'class': 'form-control color-picker', 'type': 'color'}),
            'secondary_color': forms.TextInput(attrs={'class': 'form-control color-picker', 'type': 'color'}),
            'accent_color': forms.TextInput(attrs={'class': 'form-control color-picker', 'type': 'color'}),
        }
    
    def clean_primary_color(self):
        color = self.cleaned_data['primary_color']
        if not color.startswith('#'):
            color = '#' + color
        return color
    
    def clean_secondary_color(self):
        color = self.cleaned_data['secondary_color']
        if not color.startswith('#'):
            color = '#' + color
        return color
    
    def clean_accent_color(self):
        color = self.cleaned_data['accent_color']
        if not color.startswith('#'):
            color = '#' + color
        return color


class BrandingBasicForm(forms.ModelForm):
    """Form for basic branding settings only"""
    
    class Meta:
        model = BrandingSettings
        fields = [
            'site_name', 'site_tagline', 'window_title_prefix', 'window_title_suffix',
            'header_brand_text', 'logo', 'favicon',
            'footer_copyright_text', 'footer_powered_by_text'
        ]
        widgets = {
            'site_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter site name'}),
            'site_tagline': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter optional tagline'}),
            'window_title_prefix': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., SOLUNA -'}),
            'window_title_suffix': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., - Maintenance System'}),
            'header_brand_text': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Text displayed next to logo'}),
            'logo': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'favicon': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'footer_copyright_text': forms.TextInput(attrs={'class': 'form-control'}),
            'footer_powered_by_text': forms.TextInput(attrs={'class': 'form-control'}),
        }


class BrandingNavigationForm(forms.ModelForm):
    """Form for navigation labels only"""
    
    class Meta:
        model = BrandingSettings
        fields = [
            'navigation_overview_label', 'navigation_equipment_label', 
            'navigation_maintenance_label', 'navigation_calendar_label',
            'navigation_map_label', 'navigation_settings_label', 'navigation_debug_label'
        ]
        widgets = {
            'navigation_overview_label': forms.TextInput(attrs={'class': 'form-control'}),
            'navigation_equipment_label': forms.TextInput(attrs={'class': 'form-control'}),
            'navigation_maintenance_label': forms.TextInput(attrs={'class': 'form-control'}),
            'navigation_calendar_label': forms.TextInput(attrs={'class': 'form-control'}),
            'navigation_map_label': forms.TextInput(attrs={'class': 'form-control'}),
            'navigation_settings_label': forms.TextInput(attrs={'class': 'form-control'}),
            'navigation_debug_label': forms.TextInput(attrs={'class': 'form-control'}),
        }


class BrandingAppearanceForm(forms.ModelForm):
    """Form for appearance/colors only"""
    
    class Meta:
        model = BrandingSettings
        fields = [
            'primary_color', 'secondary_color', 'accent_color',
            'header_background_color', 'header_text_color', 'header_border_color',
            'navigation_background_color', 'navigation_text_color', 'navigation_hover_color',
            'content_background_color', 'content_text_color', 'card_background_color', 'card_border_color',
            'button_primary_color', 'button_primary_text_color', 'button_secondary_color', 'button_secondary_text_color',
            'form_background_color', 'form_border_color', 'form_text_color',
            'success_color', 'warning_color', 'danger_color', 'info_color',
            'dropdown_background_color', 'dropdown_background_opacity', 'dropdown_text_color', 'dropdown_border_color',
            'dropdown_hover_background_color', 'dropdown_hover_text_color'
        ]
        widgets = {
            'primary_color': forms.TextInput(attrs={'class': 'form-control color-picker', 'type': 'color'}),
            'secondary_color': forms.TextInput(attrs={'class': 'form-control color-picker', 'type': 'color'}),
            'accent_color': forms.TextInput(attrs={'class': 'form-control color-picker', 'type': 'color'}),
            'header_background_color': forms.TextInput(attrs={'class': 'form-control color-picker', 'type': 'color'}),
            'header_text_color': forms.TextInput(attrs={'class': 'form-control color-picker', 'type': 'color'}),
            'header_border_color': forms.TextInput(attrs={'class': 'form-control color-picker', 'type': 'color'}),
            'navigation_background_color': forms.TextInput(attrs={'class': 'form-control color-picker', 'type': 'color'}),
            'navigation_text_color': forms.TextInput(attrs={'class': 'form-control color-picker', 'type': 'color'}),
            'navigation_hover_color': forms.TextInput(attrs={'class': 'form-control color-picker', 'type': 'color'}),
            'content_background_color': forms.TextInput(attrs={'class': 'form-control color-picker', 'type': 'color'}),
            'content_text_color': forms.TextInput(attrs={'class': 'form-control color-picker', 'type': 'color'}),
            'card_background_color': forms.TextInput(attrs={'class': 'form-control color-picker', 'type': 'color'}),
            'card_border_color': forms.TextInput(attrs={'class': 'form-control color-picker', 'type': 'color'}),
            'button_primary_color': forms.TextInput(attrs={'class': 'form-control color-picker', 'type': 'color'}),
            'button_primary_text_color': forms.TextInput(attrs={'class': 'form-control color-picker', 'type': 'color'}),
            'button_secondary_color': forms.TextInput(attrs={'class': 'form-control color-picker', 'type': 'color'}),
            'button_secondary_text_color': forms.TextInput(attrs={'class': 'form-control color-picker', 'type': 'color'}),
            'form_background_color': forms.TextInput(attrs={'class': 'form-control color-picker', 'type': 'color'}),
            'form_border_color': forms.TextInput(attrs={'class': 'form-control color-picker', 'type': 'color'}),
            'form_text_color': forms.TextInput(attrs={'class': 'form-control color-picker', 'type': 'color'}),
            'success_color': forms.TextInput(attrs={'class': 'form-control color-picker', 'type': 'color'}),
            'warning_color': forms.TextInput(attrs={'class': 'form-control color-picker', 'type': 'color'}),
            'danger_color': forms.TextInput(attrs={'class': 'form-control color-picker', 'type': 'color'}),
            'info_color': forms.TextInput(attrs={'class': 'form-control color-picker', 'type': 'color'}),
            'dropdown_background_color': forms.TextInput(attrs={'class': 'form-control color-picker', 'type': 'color'}),
            'dropdown_background_opacity': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 1, 'step': '0.01'}),
            'dropdown_text_color': forms.TextInput(attrs={'class': 'form-control color-picker', 'type': 'color'}),
            'dropdown_border_color': forms.TextInput(attrs={'class': 'form-control color-picker', 'type': 'color'}),
            'dropdown_hover_background_color': forms.TextInput(attrs={'class': 'form-control color-picker', 'type': 'color'}),
            'dropdown_hover_text_color': forms.TextInput(attrs={'class': 'form-control color-picker', 'type': 'color'}),
        }
    
    def clean_primary_color(self):
        color = self.cleaned_data['primary_color']
        if not color.startswith('#'):
            color = '#' + color
        return color
    
    def clean_secondary_color(self):
        color = self.cleaned_data['secondary_color']
        if not color.startswith('#'):
            color = '#' + color
        return color
    
    def clean_accent_color(self):
        color = self.cleaned_data['accent_color']
        if not color.startswith('#'):
            color = '#' + color
        return color
    
    def clean_header_background_color(self):
        color = self.cleaned_data['header_background_color']
        if not color.startswith('#'):
            color = '#' + color
        return color
    
    def clean_header_text_color(self):
        color = self.cleaned_data['header_text_color']
        if not color.startswith('#'):
            color = '#' + color
        return color
    
    def clean_header_border_color(self):
        color = self.cleaned_data['header_border_color']
        if not color.startswith('#'):
            color = '#' + color
        return color
    
    def clean_navigation_background_color(self):
        color = self.cleaned_data['navigation_background_color']
        if not color.startswith('#'):
            color = '#' + color
        return color
    
    def clean_navigation_text_color(self):
        color = self.cleaned_data['navigation_text_color']
        if not color.startswith('#'):
            color = '#' + color
        return color
    
    def clean_navigation_hover_color(self):
        color = self.cleaned_data['navigation_hover_color']
        if not color.startswith('#'):
            color = '#' + color
        return color
    
    def clean_content_background_color(self):
        color = self.cleaned_data['content_background_color']
        if not color.startswith('#'):
            color = '#' + color
        return color
    
    def clean_content_text_color(self):
        color = self.cleaned_data['content_text_color']
        if not color.startswith('#'):
            color = '#' + color
        return color
    
    def clean_card_background_color(self):
        color = self.cleaned_data['card_background_color']
        if not color.startswith('#'):
            color = '#' + color
        return color
    
    def clean_card_border_color(self):
        color = self.cleaned_data['card_border_color']
        if not color.startswith('#'):
            color = '#' + color
        return color
    
    def clean_button_primary_color(self):
        color = self.cleaned_data['button_primary_color']
        if not color.startswith('#'):
            color = '#' + color
        return color
    
    def clean_button_primary_text_color(self):
        color = self.cleaned_data['button_primary_text_color']
        if not color.startswith('#'):
            color = '#' + color
        return color
    
    def clean_button_secondary_color(self):
        color = self.cleaned_data['button_secondary_color']
        if not color.startswith('#'):
            color = '#' + color
        return color
    
    def clean_button_secondary_text_color(self):
        color = self.cleaned_data['button_secondary_text_color']
        if not color.startswith('#'):
            color = '#' + color
        return color
    
    def clean_form_background_color(self):
        color = self.cleaned_data['form_background_color']
        if not color.startswith('#'):
            color = '#' + color
        return color
    
    def clean_form_border_color(self):
        color = self.cleaned_data['form_border_color']
        if not color.startswith('#'):
            color = '#' + color
        return color
    
    def clean_form_text_color(self):
        color = self.cleaned_data['form_text_color']
        if not color.startswith('#'):
            color = '#' + color
        return color
    
    def clean_success_color(self):
        color = self.cleaned_data['success_color']
        if not color.startswith('#'):
            color = '#' + color
        return color
    
    def clean_warning_color(self):
        color = self.cleaned_data['warning_color']
        if not color.startswith('#'):
            color = '#' + color
        return color
    
    def clean_danger_color(self):
        color = self.cleaned_data['danger_color']
        if not color.startswith('#'):
            color = '#' + color
        return color
    
    def clean_info_color(self):
        color = self.cleaned_data['info_color']
        if not color.startswith('#'):
            color = '#' + color
        return color

class CSSCustomizationForm(forms.ModelForm):
    """Form for editing CSS customizations"""
    
    class Meta:
        model = CSSCustomization
        fields = ['name', 'item_type', 'description', 'css_code', 'is_active', 'priority', 'order']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter CSS customization name'}),
            'item_type': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Describe what this CSS customization does'}),
            'css_code': forms.Textarea(attrs={
                'class': 'form-control css-editor', 
                'rows': 15, 
                'placeholder': 'Enter CSS code here (without <style> tags)',
                'spellcheck': 'false'
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'priority': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}),
        }
    
    def clean_css_code(self):
        css_code = self.cleaned_data['css_code']
        
        # Basic CSS validation
        if css_code.strip():
            # Check for common issues
            if '<style>' in css_code or '</style>' in css_code:
                raise forms.ValidationError("Please don't include <style> tags in the CSS code.")
            
            if 'javascript:' in css_code.lower():
                raise forms.ValidationError("JavaScript is not allowed in CSS customizations.")
        
        return css_code

class CSSPreviewForm(forms.Form):
    """Form for previewing CSS changes"""
    css_code = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control css-editor', 
            'rows': 15,
            'placeholder': 'Enter CSS code to preview...'
        }),
        required=False
    )
    
    def clean_css_code(self):
        css_code = self.cleaned_data['css_code']
        
        if css_code.strip():
            if '<style>' in css_code or '</style>' in css_code:
                raise forms.ValidationError("Please don't include <style> tags in the CSS code.")
            
            if 'javascript:' in css_code.lower():
                raise forms.ValidationError("JavaScript is not allowed in CSS customizations.")
        
        return css_code