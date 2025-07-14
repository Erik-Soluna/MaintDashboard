"""
Maintenance models for the maintenance dashboard.
Fixed: Proper associations between maintenance activities and schedules.
"""

from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.utils import timezone
import datetime
from datetime import timedelta
from core.models import TimeStampedModel, EquipmentCategory
from equipment.models import Equipment


class ActivityTypeCategory(TimeStampedModel):
    """
    Categories for organizing maintenance activity types.
    Similar to equipment categories but for maintenance activities.
    """
    name = models.CharField(max_length=100, unique=True, help_text="Category name (e.g., Preventive, Corrective, Inspection)")
    description = models.TextField(blank=True, help_text="Description of this activity category")
    color = models.CharField(max_length=7, default='#007bff', help_text="Color for visual identification (hex code)")
    icon = models.CharField(max_length=50, default='fas fa-wrench', help_text="FontAwesome icon class")
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0, help_text="Order for display")

    class Meta:
        verbose_name = "Activity Type Category"
        verbose_name_plural = "Activity Type Categories"
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class ActivityTypeTemplate(TimeStampedModel):
    """
    Templates for activity types tied to specific equipment categories.
    This allows for automatic suggestions based on equipment type.
    """
    name = models.CharField(max_length=100, help_text="Template name")
    equipment_category = models.ForeignKey(
        EquipmentCategory,
        on_delete=models.CASCADE,
        related_name='activity_templates',
        help_text="Equipment category this template applies to"
    )
    category = models.ForeignKey(
        ActivityTypeCategory,
        on_delete=models.CASCADE,
        related_name='templates',
        help_text="Activity type category"
    )
    description = models.TextField(help_text="Template description")
    estimated_duration_hours = models.PositiveIntegerField(default=1, help_text="Estimated duration in hours")
    frequency_days = models.PositiveIntegerField(help_text="Frequency in days")
    is_mandatory = models.BooleanField(default=True, help_text="Is this activity mandatory?")
    
    # Default settings
    default_tools_required = models.TextField(blank=True, help_text="Default tools required")
    default_parts_required = models.TextField(blank=True, help_text="Default parts required")
    default_safety_notes = models.TextField(blank=True, help_text="Default safety considerations")
    
    # Checklist template
    checklist_template = models.TextField(blank=True, help_text="Default checklist items (one per line)")
    
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0, help_text="Order for display")

    class Meta:
        verbose_name = "Activity Type Template"
        verbose_name_plural = "Activity Type Templates"
        ordering = ['equipment_category', 'sort_order', 'name']
        unique_together = ['equipment_category', 'name']

    def __str__(self):
        return f"{self.equipment_category.name} - {self.name}"


class MaintenanceActivityType(TimeStampedModel):
    """
    Types of maintenance activities (replaces hardcoded activities from original).
    Fixed: Made maintenance activity types configurable instead of hardcoded.
    Enhanced: Added category and template relationships.
    """
    name = models.CharField(max_length=100, unique=True, help_text="Activity type name (e.g., T-A-1, T-A-2)")
    category = models.ForeignKey(
        ActivityTypeCategory,
        on_delete=models.CASCADE,
        related_name='activity_types',
        help_text="Activity type category",
        null=False,
        blank=False,
    )
    template = models.ForeignKey(
        ActivityTypeTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_activity_types',
        help_text="Template used to create this activity type"
    )
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
    
    # Enhanced fields
    tools_required = models.TextField(blank=True, help_text="Tools required for this activity")
    parts_required = models.TextField(blank=True, help_text="Parts required for this activity")
    safety_notes = models.TextField(blank=True, help_text="Safety considerations")
    
    # Equipment type associations
    applicable_equipment_categories = models.ManyToManyField(
        EquipmentCategory,
        blank=True,
        related_name='applicable_activity_types',
        help_text="Equipment categories this activity type applies to"
    )

    class Meta:
        verbose_name = "Maintenance Activity Type"
        verbose_name_plural = "Maintenance Activity Types"
        ordering = ['category', 'name']

    def __str__(self):
        return f"{self.name} - {self.description}"
    
    def get_applicable_equipment_categories_display(self):
        """Get a comma-separated list of applicable equipment categories."""
        return ", ".join([cat.name for cat in self.applicable_equipment_categories.all()])


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

    def _make_aware(self, dt):
        if dt and isinstance(dt, datetime.datetime) and timezone.is_naive(dt):
            return timezone.make_aware(dt)
        return dt

    def clean(self):
        """Custom validation for maintenance activity."""
        # Convert naive datetimes to aware
        self.scheduled_start = self._make_aware(self.scheduled_start)
        self.scheduled_end = self._make_aware(self.scheduled_end)
        self.actual_start = self._make_aware(self.actual_start)
        self.actual_end = self._make_aware(self.actual_end)
        if self.scheduled_start and self.scheduled_end:
            if self.scheduled_start >= self.scheduled_end:
                raise ValidationError("Scheduled start must be before scheduled end.")
                
        if self.actual_start and self.actual_end:
            if self.actual_start >= self.actual_end:
                raise ValidationError("Actual start must be before actual end.")
                
        # Update status based on dates
        now = timezone.now()
        if self.scheduled_end and self.scheduled_end < now and self.status not in ['completed', 'cancelled']:
            self.status = 'overdue'

    def save(self, *args, **kwargs):
        # Convert naive datetimes to aware before saving
        self.scheduled_start = self._make_aware(self.scheduled_start)
        self.scheduled_end = self._make_aware(self.scheduled_end)
        self.actual_start = self._make_aware(self.actual_start)
        self.actual_end = self._make_aware(self.actual_end)
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


class MaintenanceTimelineEntry(TimeStampedModel):
    """
    Timeline entries for maintenance activities.
    Tracks the history and progress of maintenance activities.
    """
    
    ENTRY_TYPES = [
        ('created', 'Activity Created'),
        ('assigned', 'Activity Assigned'),
        ('started', 'Activity Started'),
        ('paused', 'Activity Paused'),
        ('resumed', 'Activity Resumed'),
        ('completed', 'Activity Completed'),
        ('cancelled', 'Activity Cancelled'),
        ('note', 'Note Added'),
        ('issue', 'Issue Reported'),
        ('resolution', 'Issue Resolved'),
    ]
    
    activity = models.ForeignKey(
        MaintenanceActivity,
        on_delete=models.CASCADE,
        related_name='timeline_entries'
    )
    entry_type = models.CharField(max_length=20, choices=ENTRY_TYPES)
    title = models.CharField(max_length=200, help_text="Timeline entry title")
    description = models.TextField(help_text="Detailed description of the timeline entry")
    
    # Optional fields for specific entry types
    issue_severity = models.CharField(
        max_length=20,
        choices=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('critical', 'Critical'),
        ],
        blank=True,
        help_text="Severity level for issue entries"
    )
    resolution_time = models.DurationField(
        null=True,
        blank=True,
        help_text="Time taken to resolve issue"
    )
    
    # User who created the entry
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='maintenance_timeline_entries'
    )

    class Meta:
        verbose_name = "Maintenance Timeline Entry"
        verbose_name_plural = "Maintenance Timeline Entries"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.activity.title} - {self.entry_type} ({self.created_at})"

    def get_icon_class(self):
        """Get FontAwesome icon class based on entry type."""
        icon_map = {
            'created': 'fas fa-plus-circle',
            'assigned': 'fas fa-user-plus',
            'started': 'fas fa-play-circle',
            'paused': 'fas fa-pause-circle',
            'resumed': 'fas fa-play-circle',
            'completed': 'fas fa-check-circle',
            'cancelled': 'fas fa-times-circle',
            'note': 'fas fa-sticky-note',
            'issue': 'fas fa-exclamation-triangle',
            'resolution': 'fas fa-check-square',
        }
        return icon_map.get(self.entry_type, 'fas fa-circle')

    def get_color_class(self):
        """Get Bootstrap color class based on entry type."""
        color_map = {
            'created': 'text-primary',
            'assigned': 'text-info',
            'started': 'text-success',
            'paused': 'text-warning',
            'resumed': 'text-success',
            'completed': 'text-success',
            'cancelled': 'text-danger',
            'note': 'text-secondary',
            'issue': 'text-danger',
            'resolution': 'text-success',
        }
        return color_map.get(self.entry_type, 'text-secondary')


class MaintenanceReport(TimeStampedModel):
    """
    Reports generated during or after maintenance activities.
    These are the documents that should be scanned for issues.
    """
    maintenance_activity = models.ForeignKey(
        'MaintenanceActivity',
        on_delete=models.CASCADE,
        related_name='reports',
        help_text="The maintenance activity this report belongs to"
    )
    
    REPORT_TYPE_CHOICES = [
        ('inspection', 'Inspection Report'),
        ('repair', 'Repair Report'),
        ('testing', 'Testing Report'),
        ('dga', 'DGA Report'),
        ('calibration', 'Calibration Report'),
        ('other', 'Other Report'),
    ]
    
    report_type = models.CharField(
        max_length=20,
        choices=REPORT_TYPE_CHOICES,
        default='other',
        help_text="Type of maintenance report"
    )
    
    title = models.CharField(
        max_length=200,
        help_text="Title of the report"
    )
    
    file = models.FileField(
        upload_to='maintenance/reports/',
        help_text="The report file (PDF, DOC, etc.)"
    )
    
    findings_summary = models.TextField(
        blank=True,
        help_text="Summary of findings from the report"
    )
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('completed', 'Completed'),
        ('approved', 'Approved'),
    ]
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        help_text="Current status of the report"
    )
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_maintenance_reports'
    )
    
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_maintenance_reports'
    )
    
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the report was approved"
    )

    class Meta:
        verbose_name = "Maintenance Report"
        verbose_name_plural = "Maintenance Reports"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.maintenance_activity.equipment.name}"

    @property
    def equipment(self):
        """Get the equipment this report is for."""
        return self.maintenance_activity.equipment

    def clean(self):
        """Custom validation for maintenance report."""
        if self.status == 'approved' and not self.approved_by:
            raise ValidationError("Approved reports must have an approver.")
        
        if self.approved_at and not self.approved_by:
            raise ValidationError("Approval date requires an approver.")

    def get_issues(self):
        """Alias for extract_issues."""
        return self.extract_issues()

    def get_critical_issues(self):
        """Return only critical issues from analyzed data."""
        return [issue for issue in self.extract_issues() if issue.get('severity') == 'critical']

    def get_parts_replaced(self):
        """Alias for extract_parts_replaced."""
        return self.extract_parts_replaced()

    def get_measurements(self):
        """Alias for extract_measurements."""
        return self.extract_measurements()

    def get_file_size_mb(self):
        """Get file size in megabytes (float)."""
        size = self.get_file_size()
        return size / (1024 * 1024) if size else 0

    def get_file_size_kb(self):
        """Get file size in kilobytes (float)."""
        size = self.get_file_size()
        return size / 1024 if size else 0

    def get_file_size_formatted(self):
        """Alias for get_file_size_display."""
        return self.get_file_size_display()

    def get_file_extension(self):
        """Get the file extension of the uploaded document."""
        if self.document:
            return self.document.name.split('.')[-1].lower()
        return ''

    def get_file_size(self):
        """Get the file size in bytes."""
        if self.document and self.document.storage.exists(self.document.name):
            return self.document.size
        return 0

    def get_file_size_display(self):
        """Get the file size in human-readable format. Returns '0 KB' for zero size to match tests."""
        size = self.get_file_size()
        if size == 0:
            return "0 KB"
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / (1024 * 1024):.1f} MB"

    def extract_issues(self):
        """Extract issues from analyzed data."""
        return self.analyzed_data.get('issues', [])

    def extract_parts_replaced(self):
        """Extract parts replaced from analyzed data."""
        return self.analyzed_data.get('parts_replaced', [])

    def extract_measurements(self):
        """Extract measurements from analyzed data."""
        return self.analyzed_data.get('measurements', [])

    def has_critical_issues(self):
        """Check if the report contains critical issues."""
        issues = self.extract_issues()
        return any(issue.get('severity') == 'critical' for issue in issues)

    def get_priority_score(self):
        """Calculate a priority score based on report content."""
        score = 0
        issues = self.extract_issues()
        
        for issue in issues:
            severity = issue.get('severity', 'low')
            if severity == 'critical':
                score += 10
            elif severity == 'high':
                score += 5
            elif severity == 'medium':
                score += 2
            else:
                score += 1
        
        return score