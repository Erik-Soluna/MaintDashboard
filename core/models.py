"""
Core models for the maintenance dashboard.
Contains shared models used across multiple apps.
"""

from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


class TimeStampedModel(models.Model):
    """Abstract base class for models that need timestamps."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_created'
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_updated'
    )

    class Meta:
        abstract = True


class EquipmentCategory(TimeStampedModel):
    """
    Equipment categories for organizing equipment.
    Fixed: Made name unique and added proper validation.
    """
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique category name for equipment"
    )
    description = models.TextField(blank=True, help_text="Optional category description")
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Equipment Category"
        verbose_name_plural = "Equipment Categories"
        ordering = ['name']

    def __str__(self):
        return self.name

    def clean(self):
        """Custom validation for category."""
        if self.name:
            self.name = self.name.strip()
        if not self.name:
            raise ValidationError("Category name cannot be empty.")


class Location(TimeStampedModel):
    """
    Hierarchical location model supporting both sites and equipment locations.
    Fixed: Improved hierarchy handling and validation.
    """
    name = models.CharField(max_length=200, help_text="Location name")
    parent_location = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='child_locations',
        help_text="Parent location for hierarchical organization"
    )
    is_site = models.BooleanField(
        default=False,
        help_text="Whether this is a site-level location"
    )
    latitude = models.FloatField(null=True, blank=True, help_text="GPS latitude")
    longitude = models.FloatField(null=True, blank=True, help_text="GPS longitude")
    address = models.TextField(blank=True, help_text="Physical address")
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Location"
        verbose_name_plural = "Locations"
        ordering = ['name']
        constraints = [
            # Ensure site locations don't have parent locations
            models.CheckConstraint(
                check=~(models.Q(is_site=True) & ~models.Q(parent_location=None)),
                name='site_locations_no_parent'
            )
        ]

    def __str__(self):
        if self.parent_location:
            return f"{self.parent_location.name} > {self.name}"
        return self.name

    def clean(self):
        """Custom validation for location hierarchy."""
        if self.name:
            self.name = self.name.strip()
        
        if not self.name:
            raise ValidationError("Location name cannot be empty.")
            
        # Site locations cannot have parent locations
        if self.is_site and self.parent_location:
            raise ValidationError("Site locations cannot have a parent location.")
            
        # Equipment locations must have a parent location
        if not self.is_site and not self.parent_location:
            raise ValidationError("Equipment locations must have a parent location.")
            
        # Prevent circular references
        if self.parent_location and self.pk:
            current = self.parent_location
            while current:
                if current.pk == self.pk:
                    raise ValidationError("Location cannot be its own ancestor.")
                current = current.parent_location

    def get_full_path(self):
        """Get the full hierarchical path of the location."""
        path = [self.name]
        current = self.parent_location
        while current:
            path.insert(0, current.name)
            current = current.parent_location
        return " > ".join(path)

    def get_site_location(self):
        """Get the top-level site location."""
        current = self
        while current.parent_location:
            current = current.parent_location
        return current if current.is_site else None


class UserProfile(models.Model):
    """
    Extended user profile to replace the web2py groupID system.
    Fixed: Use Django's proper user groups instead of custom groupID.
    """
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('manager', 'Maintenance Manager'),
        ('technician', 'Maintenance Technician'),
        ('viewer', 'Read-Only Viewer'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='viewer')
    phone_number = models.CharField(max_length=20, blank=True)
    employee_id = models.CharField(max_length=50, blank=True, unique=True, null=True)
    department = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    
    # Settings preferences
    default_location = models.ForeignKey(
        'Location', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="Default location for new equipment and maintenance activities"
    )
    notifications_enabled = models.BooleanField(default=True)
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.get_role_display()})"

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"