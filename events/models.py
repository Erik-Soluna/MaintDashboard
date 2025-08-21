"""
Events models for calendar management.
Simplified: Calendar events are now high-level overviews that link to detailed maintenance activities.
"""

from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from core.models import TimeStampedModel
from equipment.models import Equipment


class CalendarEvent(TimeStampedModel):
    """
    Calendar events for high-level overview of equipment-related activities.
    Simplified: Basic event information with links to detailed maintenance activities.
    """
    
    # Event types are now dynamic based on maintenance activity types
    # The format is 'activity_{id}' where id is the MaintenanceActivityType ID
    # This ensures consistency between calendar events and maintenance activities
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    # Core information - Simplified
    title = models.CharField(max_length=200, help_text="Event title")
    description = models.TextField(blank=True, help_text="Brief event description")
    event_type = models.CharField(
        max_length=50,
        help_text="Type of event (format: 'activity_{id}' for maintenance activities)"
    )
    
    # Equipment association
    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.CASCADE,
        related_name='calendar_events',
        help_text="Equipment this event relates to"
    )
    
    # Timing - Simplified
    event_date = models.DateField(help_text="Event date")
    start_time = models.TimeField(null=True, blank=True, help_text="Event start time")
    end_time = models.TimeField(null=True, blank=True, help_text="Event end time")
    all_day = models.BooleanField(default=False, help_text="All day event")
    
    # Basic properties
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='medium'
    )
    
    # Assignment
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_events',
        help_text="User assigned to this event"
    )
    
    # Status - Simplified
    is_completed = models.BooleanField(default=False)
    
    # Link to detailed maintenance activity (if applicable)
    maintenance_activity = models.ForeignKey(
        'maintenance.MaintenanceActivity',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='calendar_events',
        help_text="Detailed maintenance activity (if this is a maintenance event)"
    )

    class Meta:
        verbose_name = "Calendar Event"
        verbose_name_plural = "Calendar Events"
        ordering = ['event_date', 'start_time']
        indexes = [
            models.Index(fields=['event_date']),
            models.Index(fields=['equipment', 'event_date']),
            models.Index(fields=['event_type', 'priority']),
        ]

    def __str__(self):
        return f"{self.title} - {self.equipment.name} ({self.event_date})"

    def clean(self):
        """Custom validation for calendar events."""
        if self.start_time and self.end_time:
            if self.start_time >= self.end_time:
                raise ValidationError("Start time must be before end time.")
                
        if self.all_day:
            self.start_time = None
            self.end_time = None

    def is_past_due(self):
        """Check if event is past due."""
        from django.utils import timezone
        today = timezone.now().date()
        return self.event_date < today and not self.is_completed
    
    def get_duration(self):
        """Get event duration in hours."""
        if self.all_day:
            return 24
        if self.start_time and self.end_time:
            from datetime import datetime
            start = datetime.combine(self.event_date, self.start_time)
            end = datetime.combine(self.event_date, self.end_time)
            return (end - start).total_seconds() / 3600
        return 0
    
    def is_overdue(self):
        """Check if event is overdue."""
        from django.utils import timezone
        today = timezone.now().date()
        return self.event_date < today and not self.is_completed
    
    def get_priority_display(self):
        """Get priority display with color coding."""
        priority_map = {
            'low': 'Low',
            'medium': 'Medium', 
            'high': 'High',
            'critical': 'Critical'
        }
        return priority_map.get(self.priority, self.priority)
    
    def get_status_display(self):
        """Get status display."""
        return "Completed" if self.is_completed else "Pending"
    
    def get_event_type_display(self):
        """Get event type display."""
        if self.event_type.startswith('activity_'):
            # Extract activity type ID and get the name from maintenance system
            try:
                activity_type_id = self.event_type.replace('activity_', '')
                from maintenance.models import MaintenanceActivityType
                activity_type = MaintenanceActivityType.objects.get(id=activity_type_id)
                return activity_type.name
            except (MaintenanceActivityType.DoesNotExist, ValueError):
                return f"Activity {activity_type_id}"
        return self.event_type


class EventComment(TimeStampedModel):
    """
    Comments on calendar events.
    New model for better event tracking and communication.
    """
    
    event = models.ForeignKey(
        CalendarEvent,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    comment = models.TextField(help_text="Comment text")
    is_internal = models.BooleanField(
        default=True,
        help_text="Internal comment (not visible to external users)"
    )

    class Meta:
        verbose_name = "Event Comment"
        verbose_name_plural = "Event Comments"
        ordering = ['-created_at']

    def __str__(self):
        return f"Comment on {self.event.title} by {self.created_by}"


class EventAttachment(TimeStampedModel):
    """
    File attachments for calendar events.
    New model for better document management.
    """
    
    event = models.ForeignKey(
        CalendarEvent,
        on_delete=models.CASCADE,
        related_name='attachments'
    )
    title = models.CharField(max_length=200, help_text="Attachment title")
    file = models.FileField(
        upload_to='events/attachments/',
        help_text="Attached file"
    )
    description = models.TextField(blank=True, help_text="Attachment description")

    class Meta:
        verbose_name = "Event Attachment"
        verbose_name_plural = "Event Attachments"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.event.title}"


class EventReminder(TimeStampedModel):
    """
    Reminders for calendar events.
    New model for proper notification management.
    """
    
    REMINDER_TYPES = [
        ('email', 'Email Notification'),
        ('sms', 'SMS Notification'),
        ('dashboard', 'Dashboard Notification'),
    ]
    
    event = models.ForeignKey(
        CalendarEvent,
        on_delete=models.CASCADE,
        related_name='reminders'
    )
    reminder_type = models.CharField(max_length=20, choices=REMINDER_TYPES)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='event_reminders'
    )
    reminder_time = models.DateTimeField(help_text="When to send the reminder")
    message = models.TextField(help_text="Reminder message")
    is_sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Event Reminder"
        verbose_name_plural = "Event Reminders"
        ordering = ['reminder_time']
        unique_together = ['event', 'user', 'reminder_type']

    def __str__(self):
        return f"Reminder for {self.event.title} to {self.user.username}"