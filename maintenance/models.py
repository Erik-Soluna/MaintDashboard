"""
Maintenance models for the maintenance dashboard.
Fixed: Proper associations between maintenance activities and schedules.
"""

from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from core.models import TimeStampedModel
from equipment.models import Equipment


class MaintenanceActivityType(TimeStampedModel):
    """
    Types of maintenance activities (replaces hardcoded activities from original).
    Fixed: Made maintenance activity types configurable instead of hardcoded.
    """
    name = models.CharField(max_length=100, unique=True, help_text="Activity type name (e.g., T-A-1, T-A-2)")
    description = models.TextField(help_text="Description of the maintenance activity")
    estimated_duration_hours = models.PositiveIntegerField(
        default=1,
        help_text="Estimated duration in hours"
    )
    frequency_days = models.PositiveIntegerField(
        help_text="Frequency in days (e.g., 365 for annual)"
    )
    is_mandatory = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Maintenance Activity Type"
        verbose_name_plural = "Maintenance Activity Types"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} - {self.description}"


class MaintenanceActivity(TimeStampedModel):
    """
    Individual maintenance activities.
    Fixed: Proper relationship with equipment and improved status tracking.
    """
    
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('overdue', 'Overdue'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    # Core relationships - Fixed from original
    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.CASCADE,
        related_name='maintenance_activities',
        help_text="Equipment this maintenance is for"
    )
    activity_type = models.ForeignKey(
        MaintenanceActivityType,
        on_delete=models.PROTECT,
        related_name='activities',
        help_text="Type of maintenance activity"
    )
    
    # Basic information
    title = models.CharField(max_length=200, help_text="Maintenance activity title")
    description = models.TextField(blank=True, help_text="Detailed description")
    
    # Status and priority
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    
    # Scheduling - Fixed from original disconnected schedule table
    scheduled_start = models.DateTimeField(help_text="Scheduled start date and time")
    scheduled_end = models.DateTimeField(help_text="Scheduled end date and time")
    actual_start = models.DateTimeField(null=True, blank=True)
    actual_end = models.DateTimeField(null=True, blank=True)
    
    # Assignment
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_maintenance',
        help_text="User assigned to perform this maintenance"
    )
    
    # Requirements and results
    required_status = models.CharField(
        max_length=100,
        blank=True,
        help_text="Required equipment status during maintenance"
    )
    tools_required = models.TextField(blank=True, help_text="Tools required for maintenance")
    parts_required = models.TextField(blank=True, help_text="Parts required for maintenance")
    safety_notes = models.TextField(blank=True, help_text="Safety considerations")
    completion_notes = models.TextField(blank=True, help_text="Notes upon completion")
    
    # Next maintenance scheduling
    next_due_date = models.DateField(
        null=True,
        blank=True,
        help_text="When next maintenance of this type is due"
    )

    class Meta:
        verbose_name = "Maintenance Activity"
        verbose_name_plural = "Maintenance Activities"
        ordering = ['-scheduled_start']
        indexes = [
            models.Index(fields=['equipment', 'status']),
            models.Index(fields=['scheduled_start']),
            models.Index(fields=['status', 'priority']),
        ]

    def __str__(self):
        return f"{self.equipment.name} - {self.title} ({self.get_status_display()})"

    def clean(self):
        """Custom validation for maintenance activity."""
        if self.scheduled_start and self.scheduled_end:
            if self.scheduled_start >= self.scheduled_end:
                raise ValidationError("Scheduled start must be before scheduled end.")
                
        if self.actual_start and self.actual_end:
            if self.actual_start >= self.actual_end:
                raise ValidationError("Actual start must be before actual end.")
                
        # Update status based on dates
        now = timezone.now()
        if self.scheduled_end < now and self.status not in ['completed', 'cancelled']:
            self.status = 'overdue'

    def save(self, *args, **kwargs):
        # Auto-calculate next due date if completed
        if self.status == 'completed' and self.actual_end and not self.next_due_date:
            self.next_due_date = (
                self.actual_end.date() + timedelta(days=self.activity_type.frequency_days)
            )
        super().save(*args, **kwargs)

    def get_duration(self):
        """Get actual or estimated duration."""
        if self.actual_start and self.actual_end:
            return self.actual_end - self.actual_start
        elif self.scheduled_start and self.scheduled_end:
            return self.scheduled_end - self.scheduled_start
        return None

    def is_overdue(self):
        """Check if maintenance is overdue."""
        return (
            self.scheduled_end < timezone.now() and 
            self.status not in ['completed', 'cancelled']
        )


class MaintenanceChecklist(TimeStampedModel):
    """
    Checklist items for maintenance activities.
    New model to handle detailed maintenance procedures.
    """
    
    activity = models.ForeignKey(
        MaintenanceActivity,
        on_delete=models.CASCADE,
        related_name='checklist_items'
    )
    activity_type = models.ForeignKey(
        MaintenanceActivityType,
        on_delete=models.CASCADE,
        related_name='checklist_templates',
        help_text="Activity type this checklist item belongs to"
    )
    item_text = models.TextField(help_text="Checklist item description")
    order = models.PositiveIntegerField(default=1, help_text="Order of this item in the checklist")
    is_completed = models.BooleanField(default=False)
    completed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='completed_checklist_items'
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, help_text="Notes for this checklist item")
    is_required = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Maintenance Checklist Item"
        verbose_name_plural = "Maintenance Checklist Items"
        ordering = ['activity', 'order']
        unique_together = ['activity', 'order']

    def __str__(self):
        return f"{self.activity} - Step {self.order}"

    def save(self, *args, **kwargs):
        if self.is_completed and not self.completed_at:
            self.completed_at = timezone.now()
        super().save(*args, **kwargs)


class MaintenanceSchedule(TimeStampedModel):
    """
    Recurring maintenance schedules.
    Fixed: Proper connection to equipment and activity types.
    """
    
    FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi_annual', 'Semi-Annual'),
        ('annual', 'Annual'),
        ('custom', 'Custom'),
    ]

    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.CASCADE,
        related_name='maintenance_schedules'
    )
    activity_type = models.ForeignKey(
        MaintenanceActivityType,
        on_delete=models.CASCADE,
        related_name='schedules'
    )
    
    # Scheduling
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    frequency_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Custom frequency in days (for custom frequency type)"
    )
    start_date = models.DateField(help_text="When this schedule starts")
    end_date = models.DateField(
        null=True,
        blank=True,
        help_text="When this schedule ends (optional)"
    )
    last_generated = models.DateField(
        null=True,
        blank=True,
        help_text="Last date activities were generated for this schedule"
    )
    
    # Settings
    auto_generate = models.BooleanField(
        default=True,
        help_text="Automatically generate maintenance activities"
    )
    advance_notice_days = models.PositiveIntegerField(
        default=7,
        help_text="Days in advance to generate activities"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Maintenance Schedule"
        verbose_name_plural = "Maintenance Schedules"
        ordering = ['equipment', 'activity_type']
        unique_together = ['equipment', 'activity_type']

    def __str__(self):
        return f"{self.equipment.name} - {self.activity_type.name} ({self.get_frequency_display()})"

    def get_frequency_in_days(self):
        """Convert frequency to days."""
        frequency_map = {
            'daily': 1,
            'weekly': 7,
            'monthly': 30,
            'quarterly': 90,
            'semi_annual': 180,
            'annual': 365,
        }
        
        if self.frequency == 'custom':
            return self.frequency_days or 365
        return frequency_map.get(self.frequency, 365)

    def generate_next_activity(self):
        """Generate the next maintenance activity for this schedule."""
        if not self.is_active:
            return None
            
        # Calculate next due date
        last_activity = MaintenanceActivity.objects.filter(
            equipment=self.equipment,
            activity_type=self.activity_type,
            status='completed'
        ).order_by('-actual_end').first()
        
        if last_activity and last_activity.actual_end:
            next_date = last_activity.actual_end.date() + timedelta(days=self.get_frequency_in_days())
        else:
            next_date = self.start_date
            
        # Check if we should generate the activity
        advance_date = timezone.now().date() + timedelta(days=self.advance_notice_days)
        if next_date <= advance_date:
            # Check if activity already exists
            existing = MaintenanceActivity.objects.filter(
                equipment=self.equipment,
                activity_type=self.activity_type,
                scheduled_start__date=next_date
            ).exists()
            
            if not existing:
                activity = MaintenanceActivity.objects.create(
                    equipment=self.equipment,
                    activity_type=self.activity_type,
                    title=f"{self.activity_type.name} - {self.equipment.name}",
                    description=self.activity_type.description,
                    scheduled_start=timezone.datetime.combine(
                        next_date, 
                        timezone.datetime.min.time()
                    ).replace(tzinfo=timezone.get_current_timezone()),
                    scheduled_end=timezone.datetime.combine(
                        next_date, 
                        timezone.datetime.min.time()
                    ).replace(tzinfo=timezone.get_current_timezone()) + 
                    timedelta(hours=self.activity_type.estimated_duration_hours),
                    status='scheduled',
                    priority='medium' if self.activity_type.is_mandatory else 'low',
                    created_by=self.created_by,
                )
                
                # Create corresponding calendar event for generated activity
                try:
                    from events.models import CalendarEvent
                    calendar_event = CalendarEvent.objects.create(
                        title=f"Maintenance: {activity.title}",
                        description=activity.description,
                        event_type='maintenance',
                        equipment=activity.equipment,
                        maintenance_activity=activity,
                        event_date=activity.scheduled_start.date(),
                        start_time=activity.scheduled_start.time(),
                        end_time=activity.scheduled_end.time() if activity.scheduled_end else None,
                        assigned_to=activity.assigned_to,
                        priority=activity.priority,
                        created_by=activity.created_by
                    )
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.info(f"Created calendar event for scheduled maintenance activity: {activity.title}")
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error creating calendar event for scheduled activity {activity.id}: {str(e)}")
                
                self.last_generated = next_date
                self.save()
                
                return activity
        return None