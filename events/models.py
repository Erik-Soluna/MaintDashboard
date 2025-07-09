"""
Events models for calendar management.
Fixed: Proper associations with equipment and maintenance activities.
"""

from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from core.models import TimeStampedModel
from equipment.models import Equipment


class CalendarEvent(TimeStampedModel):
    """
    Calendar events for tracking equipment-related activities.
    Fixed: Proper relationship with equipment and maintenance integration.
    """
    
    EVENT_TYPES = [
        ('maintenance', 'Maintenance Activity'),
        ('inspection', 'Inspection'),
        ('calibration', 'Calibration'),
        ('outage', 'Equipment Outage'),
        ('upgrade', 'Equipment Upgrade'),
        ('commissioning', 'Commissioning'),
        ('decommissioning', 'Decommissioning'),
        ('testing', 'Testing'),
        ('other', 'Other'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    # Core information
    title = models.CharField(max_length=200, help_text="Event title")
    description = models.TextField(blank=True, help_text="Event description")
    event_type = models.CharField(
        max_length=20,
        choices=EVENT_TYPES,
        default='other',
        help_text="Type of event"
    )
    
    # Associations - Fixed from original loose connections
    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.CASCADE,
        related_name='calendar_events',
        help_text="Equipment this event relates to"
    )
    maintenance_activity = models.ForeignKey(
        'maintenance.MaintenanceActivity',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='calendar_events',
        help_text="Associated maintenance activity (if any)"
    )
    
    # Timing
    event_date = models.DateField(help_text="Event date")
    start_time = models.TimeField(null=True, blank=True, help_text="Event start time")
    end_time = models.TimeField(null=True, blank=True, help_text="Event end time")
    all_day = models.BooleanField(default=False, help_text="All day event")
    
    # Event properties
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='medium'
    )
    is_recurring = models.BooleanField(default=False)
    recurrence_pattern = models.CharField(
        max_length=100,
        blank=True,
        help_text="Recurrence pattern (e.g., 'weekly', 'monthly')"
    )
    
    # Assignment and notification
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_events',
        help_text="User assigned to this event"
    )
    notify_assigned = models.BooleanField(
        default=True,
        help_text="Send notification to assigned user"
    )
    notification_sent = models.BooleanField(default=False)
    
    # Status
    is_completed = models.BooleanField(default=False)
    completion_notes = models.TextField(blank=True)

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

    def get_duration(self):
        """Get event duration in hours."""
        if self.start_time and self.end_time:
            start_minutes = self.start_time.hour * 60 + self.start_time.minute
            end_minutes = self.end_time.hour * 60 + self.end_time.minute
            return (end_minutes - start_minutes) / 60
        return None

    def is_past_due(self):
        """Check if event is past due."""
        from django.utils import timezone
        today = timezone.now().date()
        return self.event_date < today and not self.is_completed


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