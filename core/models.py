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


class Customer(TimeStampedModel):
    """
    Customer model for tracking which customers are associated with locations.
    This helps identify who is affected by maintenance activities.
    """
    name = models.CharField(
        max_length=200,
        unique=True,
        help_text="Customer/client name"
    )
    code = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        help_text="Customer code or abbreviation"
    )
    contact_email = models.EmailField(
        blank=True,
        help_text="Primary contact email for notifications"
    )
    contact_phone = models.CharField(
        max_length=20,
        blank=True,
        help_text="Primary contact phone number"
    )
    description = models.TextField(
        blank=True,
        help_text="Additional customer information"
    )
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Customer"
        verbose_name_plural = "Customers"
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def clean(self):
        """Custom validation for customer."""
        if self.name:
            self.name = self.name.strip()
        if not self.name:
            raise ValidationError("Customer name cannot be empty.")
        
        # Auto-generate code if not provided
        if not self.code:
            self.code = self.name.upper().replace(' ', '_')[:20]


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
    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='locations',
        help_text="Customer associated with this location"
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
            ),
            # Ensure non-site locations have parent locations
            models.CheckConstraint(
                check=~(models.Q(is_site=False) & models.Q(parent_location=None)),
                name='non_site_locations_have_parent'
            )
        ]

    def __str__(self):
        location_str = self.name
        if self.parent_location:
            location_str = f"{self.parent_location.name} > {self.name}"
        
        if self.customer:
            location_str += f" ({self.customer.name})"
        
        return location_str

    def clean(self):
        """Custom validation for location hierarchy."""
        if self.name:
            self.name = self.name.strip()
        
        if not self.name:
            raise ValidationError("Location name cannot be empty.")
            
        # Site locations cannot have parent locations
        if self.is_site and self.parent_location:
            raise ValidationError("Site locations cannot have a parent location.")
            
        # Non-site locations must have a parent location
        if not self.is_site and not self.parent_location:
            raise ValidationError("Non-site locations must have a parent location.")
            
        # Prevent circular references
        if self.parent_location and self.pk:
            current = self.parent_location
            depth = 0
            while current:
                if current.pk == self.pk:
                    raise ValidationError("Location cannot be its own ancestor.")
                if depth > 10:  # Prevent infinite loops and very deep nesting
                    raise ValidationError("Location hierarchy is too deep (maximum 10 levels).")
                current = current.parent_location
                depth += 1

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
    
    def get_effective_customer(self):
        """Get the customer for this location, inherited from parent if not set directly."""
        if self.customer:
            return self.customer
        
        # Look up the hierarchy for a customer
        current = self.parent_location
        while current:
            if current.customer:
                return current.customer
            current = current.parent_location
        
        return None
    
    def get_customer_display(self):
        """Get a display string showing customer assignment."""
        customer = self.get_effective_customer()
        if not customer:
            return "No customer assigned"
        
        if self.customer == customer:
            return f"Direct: {customer.name}"
        else:
            return f"Inherited: {customer.name}"


class Permission(models.Model):
    """
    Permission model for RBAC system.
    """
    name = models.CharField(max_length=100, unique=True)
    codename = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    module = models.CharField(max_length=50, help_text="Module this permission belongs to")
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Permission"
        verbose_name_plural = "Permissions"
        ordering = ['module', 'name']
    
    def __str__(self):
        return f"{self.module}: {self.name}"


class Role(TimeStampedModel):
    """
    Role model for RBAC system.
    """
    name = models.CharField(max_length=50, unique=True)
    display_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    permissions = models.ManyToManyField(Permission, blank=True)
    is_active = models.BooleanField(default=True)
    is_system_role = models.BooleanField(default=False, help_text="System roles cannot be deleted")
    
    class Meta:
        verbose_name = "Role"
        verbose_name_plural = "Roles"
        ordering = ['name']
    
    def __str__(self):
        return self.display_name
    
    def has_permission(self, permission_codename):
        """Check if this role has a specific permission."""
        return self.permissions.filter(
            codename=permission_codename,
            is_active=True
        ).exists()


class UserProfile(models.Model):
    """
    Extended user profile with RBAC support.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True)
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
    default_site = models.ForeignKey(
        'Location',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users_with_default_site',
        limit_choices_to={'is_site': True},
        help_text="Default site for dashboard filtering"
    )
    notifications_enabled = models.BooleanField(default=True)
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)
    
    # UI preferences
    THEME_CHOICES = [
        ('dark', 'Dark Theme'),
        ('light', 'Light Theme'),
    ]
    theme_preference = models.CharField(
        max_length=10,
        choices=THEME_CHOICES,
        default='dark',
        help_text="User interface theme preference"
    )

    def __str__(self):
        role_name = self.role.display_name if self.role else "No Role"
        return f"{self.user.get_full_name()} ({role_name})"

    def has_permission(self, permission_codename):
        """Check if user has a specific permission."""
        if self.user.is_superuser:
            return True
        
        if not self.role or not self.role.is_active:
            return False
        
        return self.role.has_permission(permission_codename)
    
    def get_permissions(self):
        """Get all permissions for this user."""
        if self.user.is_superuser:
            return Permission.objects.filter(is_active=True)
        
        if not self.role or not self.role.is_active:
            return Permission.objects.none()
        
        return self.role.permissions.filter(is_active=True)
    
    def is_admin(self):
        """Check if user is an admin."""
        return self.has_permission('admin.full_access') or self.user.is_superuser
    
    def is_manager(self):
        """Check if user is a manager."""
        return self.has_permission('maintenance.manage_all') or self.is_admin()
    
    def can_create_equipment(self):
        """Check if user can create equipment."""
        return self.has_permission('equipment.create') or self.is_admin()
    
    def can_edit_equipment(self):
        """Check if user can edit equipment."""
        return self.has_permission('equipment.edit') or self.is_admin()
    
    def can_delete_equipment(self):
        """Check if user can delete equipment."""
        return self.has_permission('equipment.delete') or self.is_admin()
    
    def can_view_equipment(self):
        """Check if user can view equipment."""
        return self.has_permission('equipment.view') or self.is_admin()
    
    def can_manage_maintenance(self):
        """Check if user can manage maintenance."""
        return self.has_permission('maintenance.manage') or self.is_admin()
    
    def can_complete_maintenance(self):
        """Check if user can complete maintenance."""
        return self.has_permission('maintenance.complete') or self.is_admin()
    
    def can_assign_maintenance(self):
        """Check if user can assign maintenance."""
        return self.has_permission('maintenance.assign') or self.is_admin()
    
    def can_manage_users(self):
        """Check if user can manage users."""
        return self.has_permission('users.manage') or self.is_admin()
    
    def can_manage_settings(self):
        """Check if user can manage settings."""
        return self.has_permission('settings.manage') or self.is_admin()

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"