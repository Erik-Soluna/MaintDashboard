"""
Forms for event management.
"""

from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Row, Column, Submit
from .models import CalendarEvent
from equipment.models import Equipment
from django.contrib.auth.models import User


class CalendarEventForm(forms.ModelForm):
    """Form for creating and editing calendar events."""
    
    class Meta:
        model = CalendarEvent
        fields = [
            'title', 'description', 'event_type', 'equipment',
            'event_date', 'start_time', 'end_time', 'all_day',
            'priority', 'assigned_to', 'notify_assigned',
            'is_recurring', 'recurrence_pattern'
        ]
        widgets = {
            'event_date': forms.DateInput(attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filter active options
        self.fields['equipment'].queryset = Equipment.objects.filter(is_active=True)
        self.fields['assigned_to'].queryset = User.objects.filter(is_active=True)
        
        # Setup crispy forms helper
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                'Basic Information',
                'title',
                'description',
                Row(
                    Column('event_type', css_class='form-group col-md-6 mb-0'),
                    Column('priority', css_class='form-group col-md-6 mb-0'),
                ),
            ),
            Fieldset(
                'Association',
                Row(
                    Column('equipment', css_class='form-group col-md-6 mb-0'),
                    Column('assigned_to', css_class='form-group col-md-6 mb-0'),
                ),
            ),
            Fieldset(
                'Timing',
                Row(
                    Column('event_date', css_class='form-group col-md-4 mb-0'),
                    Column('start_time', css_class='form-group col-md-4 mb-0'),
                    Column('end_time', css_class='form-group col-md-4 mb-0'),
                ),
                'all_day',
            ),
            Fieldset(
                'Recurrence',
                Row(
                    Column('is_recurring', css_class='form-group col-md-6 mb-0'),
                    Column('recurrence_pattern', css_class='form-group col-md-6 mb-0'),
                ),
            ),
            Fieldset(
                'Notifications',
                'notify_assigned',
            ),
            Submit('submit', 'Save Event', css_class='btn btn-primary')
        )

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        all_day = cleaned_data.get('all_day')
        
        if all_day:
            # Clear times for all-day events
            cleaned_data['start_time'] = None
            cleaned_data['end_time'] = None
        elif start_time and end_time:
            if start_time >= end_time:
                raise forms.ValidationError("Start time must be before end time.")
        
        return cleaned_data