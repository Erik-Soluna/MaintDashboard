"""
Equipment models for the maintenance dashboard.
Fixed associations and validation from the original web2py code.
"""

from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from core.models import TimeStampedModel, EquipmentCategory, Location, NaturalSortManager


class Equipment(TimeStampedModel):
    """
    Main equipment model with proper associations.
    Fixed: Added proper validation, unique constraints, and relationships.
    """
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('maintenance', 'Under Maintenance'),
        ('retired', 'Retired'),
    ]

    # Basic Information
    name = models.CharField(
        max_length=200,
        unique=True,
        help_text="Unique equipment name"
    )
    category = models.ForeignKey(
        EquipmentCategory,
        on_delete=models.PROTECT,
        related_name='equipment',
        help_text="Equipment category"
    )
    manufacturer_serial = models.CharField(
        max_length=100,
        unique=True,
        help_text="Manufacturer serial number"
    )
    asset_tag = models.CharField(
        max_length=100,
        unique=True,
        help_text="Internal asset tag",
        db_column='soluna_asset_tag'  # Keep original column name for migration
    )
    
    # Location - Fixed relationship
    location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name='equipment',
        help_text="Equipment location"
    )
    
    # Status and operational info
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )
    is_active = models.BooleanField(default=True)
    
    # Technical specifications
    manufacturer = models.CharField(max_length=100, blank=True)
    model_number = models.CharField(max_length=100, blank=True)
    power_ratings = models.CharField(max_length=200, blank=True)
    trip_setpoints = models.CharField(max_length=200, blank=True)
    
    # Documentation
    datasheet = models.FileField(
        upload_to='equipment/datasheets/',
        blank=True,
        help_text="Equipment datasheet PDF"
    )
    schematics = models.FileField(
        upload_to='equipment/schematics/',
        blank=True,
        help_text="Equipment schematics"
    )
    warranty_details = models.TextField(blank=True)
    installed_upgrades = models.TextField(blank=True)
    
    # Maintenance tracking - Fixed from original issues
    dga_due_date = models.DateField(
        null=True,
        blank=True,
        help_text="DGA (Dissolved Gas Analysis) due date",
        db_column='dga_due'  # Keep original column name
    )
    next_maintenance_date = models.DateField(
        null=True,
        blank=True,
        help_text="Next scheduled maintenance date",
        db_column='item_due_date'  # Keep original column name
    )
    
    # Additional tracking fields
    commissioning_date = models.DateField(null=True, blank=True)
    warranty_expiry_date = models.DateField(null=True, blank=True)

    # Custom manager for natural sorting
    objects = NaturalSortManager()
    
    class Meta:
        verbose_name = "Equipment"
        verbose_name_plural = "Equipment"
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['manufacturer_serial']),
            models.Index(fields=['asset_tag']),
            models.Index(fields=['category', 'location']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"

    def clean(self):
        """Custom validation for equipment."""
        # Clean and validate name
        if self.name:
            self.name = self.name.strip()
        if not self.name:
            raise ValidationError("Equipment name cannot be empty.")
        
        # Clean and validate serial numbers
        if self.manufacturer_serial:
            self.manufacturer_serial = self.manufacturer_serial.strip()
        if self.asset_tag:
            self.asset_tag = self.asset_tag.strip()
            
        # Validate dates
        if (self.dga_due_date and self.next_maintenance_date and 
            self.dga_due_date > self.next_maintenance_date):
            raise ValidationError(
                "DGA due date cannot be after next maintenance date."
            )

    def get_maintenance_status(self):
        """Get the current maintenance status of equipment."""
        from maintenance.models import MaintenanceActivity
        
        pending = MaintenanceActivity.objects.filter(
            equipment=self,
            status='pending'
        ).count()
        
        if pending > 0:
            return f"{pending} pending maintenance activities"
        return "No pending maintenance"

    def get_last_maintenance_date(self):
        last_activity = self.maintenance_activities.filter(status='completed').order_by('-actual_end').first()
        if last_activity and last_activity.actual_end:
            return last_activity.actual_end.date()
        return None

    def get_full_location_path(self):
        """Get the full hierarchical path of the equipment location."""
        return self.location.get_full_path() if self.location else "No Location"
    
    def get_site(self):
        """Get the site location for this equipment."""
        if self.location:
            return self.location.get_site_location()
        return None


class EquipmentDocument(TimeStampedModel):
    """
    Reference documents attached to specific equipment.
    These are reference materials like photos, notes, etc.
    Maintenance reports should use the MaintenanceReport model instead.
    """
    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.CASCADE,
        related_name='documents',
        help_text="Equipment this document belongs to"
    )
    
    DOCUMENT_TYPE_CHOICES = [
        ('photo', 'Equipment Photo'),
        ('note', 'Equipment Note'),
        ('specification', 'Equipment Specification'),
        ('wiring', 'Equipment Wiring'),
        ('other', 'Other Reference'),
    ]
    
    document_type = models.CharField(
        max_length=20,
        choices=DOCUMENT_TYPE_CHOICES,
        default='other',
        help_text="Type of reference document"
    )
    
    title = models.CharField(
        max_length=200,
        help_text="Title of the document"
    )
    
    file = models.FileField(
        upload_to='equipment/documents/',
        help_text="The document file"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Description of the document"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this document is currently active"
    )
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_equipment_documents'
    )

    class Meta:
        verbose_name = "Equipment Document"
        verbose_name_plural = "Equipment Documents"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.equipment.name}"

    def clean(self):
        """Custom validation for equipment document."""
        if self.title:
            self.title = self.title.strip()
        if not self.title:
            raise ValidationError("Document title cannot be empty.")


class EquipmentComponent(TimeStampedModel):
    """
    Components or parts that belong to equipment.
    New model to handle equipment hierarchy better.
    """
    
    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.CASCADE,
        related_name='components'
    )
    name = models.CharField(max_length=200)
    part_number = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    quantity = models.PositiveIntegerField(default=1)
    replacement_date = models.DateField(null=True, blank=True)
    next_replacement_date = models.DateField(null=True, blank=True)
    is_critical = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Equipment Component"
        verbose_name_plural = "Equipment Components"
        ordering = ['name']
        unique_together = ['equipment', 'name']

    def __str__(self):
        return f"{self.equipment.name} - {self.name}"

    def clean(self):
        """Validate component data."""
        if self.name:
            self.name = self.name.strip()
        if not self.name:
            raise ValidationError("Component name cannot be empty.")
            
        if self.quantity < 1:
            raise ValidationError("Quantity must be at least 1.")