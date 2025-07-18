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
    
    # Maintenance-specific fields (for maintenance events)
    activity_type = models.ForeignKey(
        'maintenance.MaintenanceActivityType',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='calendar_events',
        help_text="Maintenance activity type (for maintenance events)"
    )
    maintenance_status = models.CharField(
        max_length=20,
        choices=[
            ('scheduled', 'Scheduled'),
            ('pending', 'Pending'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
            ('cancelled', 'Cancelled'),
            ('overdue', 'Overdue'),
        ],
        default='scheduled',
        help_text="Maintenance status (for maintenance events)"
    )
    actual_start = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Actual start time (for maintenance events)"
    )
    actual_end = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Actual end time (for maintenance events)"
    )
    tools_required = models.TextField(
        blank=True,
        help_text="Tools required (for maintenance events)"
    )
    parts_required = models.TextField(
        blank=True,
        help_text="Parts required (for maintenance events)"
    )
    safety_notes = models.TextField(
        blank=True,
        help_text="Safety considerations (for maintenance events)"
    )
    
    # Additional maintenance fields
    estimated_duration_hours = models.PositiveIntegerField(
        default=2,
        help_text="Estimated duration in hours (for maintenance events)"
    )
    frequency_days = models.PositiveIntegerField(
        default=365,
        help_text="Frequency in days (for maintenance events)"
    )
    is_mandatory = models.BooleanField(
        default=False,
        help_text="Is this maintenance activity mandatory?"
    )
    next_due_date = models.DateField(
        null=True,
        blank=True,
        help_text="Next due date for recurring maintenance"
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
    
    # Maintenance activity compatibility methods
    @property
    def scheduled_start(self):
        """Get scheduled start as datetime for maintenance compatibility."""
        from django.utils import timezone
        from datetime import datetime, time
        if self.start_time:
            return timezone.make_aware(datetime.combine(self.event_date, self.start_time))
        return timezone.make_aware(datetime.combine(self.event_date, time(9, 0)))
    
    @property
    def scheduled_end(self):
        """Get scheduled end as datetime for maintenance compatibility."""
        from django.utils import timezone
        from datetime import datetime, time, timedelta
        if self.end_time:
            return timezone.make_aware(datetime.combine(self.event_date, self.end_time))
        # Default to 2 hours after start
        return self.scheduled_start + timedelta(hours=2)
    
    @property
    def status(self):
        """Get status for maintenance compatibility."""
        if self.event_type == 'maintenance':
            return self.maintenance_status
        return 'scheduled' if not self.is_completed else 'completed'
    
    @status.setter
    def status(self, value):
        """Set status for maintenance compatibility."""
        if self.event_type == 'maintenance':
            self.maintenance_status = value
            if value == 'completed':
                self.is_completed = True
    
    def get_duration(self):
        """Get event duration in hours."""
        if self.start_time and self.end_time:
            start_minutes = self.start_time.hour * 60 + self.start_time.minute
            end_minutes = self.end_time.hour * 60 + self.end_time.minute
            return (end_minutes - start_minutes) / 60
        return None
    
    def is_overdue(self):
        """Check if maintenance activity is overdue."""
        from django.utils import timezone
        if self.event_type == 'maintenance' and self.status in ['scheduled', 'pending']:
            return self.scheduled_end < timezone.now()
        return False
    
    def get_priority_display(self):
        """Get priority display name."""
        return dict(self.PRIORITY_CHOICES).get(self.priority, self.priority)
    
    def get_status_display(self):
        """Get status display name."""
        if self.event_type == 'maintenance':
            status_choices = [
                ('scheduled', 'Scheduled'),
                ('pending', 'Pending'),
                ('in_progress', 'In Progress'),
                ('completed', 'Completed'),
                ('cancelled', 'Cancelled'),
                ('overdue', 'Overdue'),
            ]
            return dict(status_choices).get(self.maintenance_status, self.maintenance_status)
        return 'Completed' if self.is_completed else 'Scheduled'
    
    def get_event_type_display(self):
        """Get event type display name."""
        return dict(self.EVENT_TYPES).get(self.event_type, self.event_type)


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