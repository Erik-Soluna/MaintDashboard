"""
Core models for the maintenance dashboard.
Contains shared models used across multiple apps.
"""

import re
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

def natural_sort_key(text):
    """Generate a key for natural sorting (handles numbers in strings correctly)."""
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r'(\d+)', str(text))]

class NaturalSortQuerySet(models.QuerySet):
    def natural_order(self):
        from django.db.models import Case, When
        objects = list(self)
        objects.sort(key=lambda obj: natural_sort_key(obj.name))
        sorted_ids = [obj.id for obj in objects]
        preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(sorted_ids)])
        return self.filter(id__in=sorted_ids).order_by(preserved)

class NaturalSortManager(models.Manager.from_queryset(NaturalSortQuerySet)):
    pass


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

    # Custom manager for natural sorting
    objects = NaturalSortManager()

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
        default='light',
        help_text="User interface theme preference"
    )
    
    # Timezone preference
    TIMEZONE_CHOICES = [
        ('America/Chicago', 'Central Time (CT)'),
        ('America/New_York', 'Eastern Time (ET)'),
        ('America/Denver', 'Mountain Time (MT)'),
        ('America/Los_Angeles', 'Pacific Time (PT)'),
        ('America/Anchorage', 'Alaska Time (AKT)'),
        ('Pacific/Honolulu', 'Hawaii Time (HST)'),
        ('UTC', 'UTC'),
        ('Europe/London', 'London (GMT)'),
        ('Europe/Paris', 'Paris (CET)'),
        ('Asia/Tokyo', 'Tokyo (JST)'),
        ('Australia/Sydney', 'Sydney (AEST)'),
    ]
    timezone = models.CharField(
        max_length=50,
        choices=TIMEZONE_CHOICES,
        default='America/Chicago',
        help_text="User's preferred timezone for displaying dates and times"
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
    
    def get_user_timezone(self):
        """Get the user's preferred timezone."""
        return self.timezone or 'America/Chicago'
    
    def convert_to_user_timezone(self, datetime_obj):
        """Convert a datetime object to the user's preferred timezone."""
        from django.utils import timezone
        import pytz
        
        if not datetime_obj:
            return None
        
        # If the datetime is naive (no timezone), assume it's in UTC
        if timezone.is_naive(datetime_obj):
            datetime_obj = timezone.make_aware(datetime_obj, pytz.UTC)
        
        # Convert to user's timezone
        user_tz = pytz.timezone(self.get_user_timezone())
        return datetime_obj.astimezone(user_tz)

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"


class ModelDocument(TimeStampedModel):
    """
    Documents shared across equipment of the same model/category.
    These are reference materials like manuals, specifications, etc.
    """
    equipment_category = models.ForeignKey(
        EquipmentCategory,
        on_delete=models.CASCADE,
        related_name='model_documents',
        help_text="Equipment category this document applies to"
    )
    
    DOCUMENT_TYPE_CHOICES = [
        ('manual', 'Operation Manual'),
        ('specification', 'Technical Specification'),
        ('wiring_diagram', 'Wiring Diagram'),
        ('schematic', 'Schematic Diagram'),
        ('datasheet', 'Data Sheet'),
        ('certification', 'Certification Document'),
        ('other', 'Other Document'),
    ]
    
    document_type = models.CharField(
        max_length=20,
        choices=DOCUMENT_TYPE_CHOICES,
        default='manual',
        help_text="Type of document"
    )
    
    title = models.CharField(
        max_length=200,
        help_text="Title of the document"
    )
    
    file = models.FileField(
        upload_to='model_documents/',
        help_text="The document file (PDF, DOC, etc.)"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Description of the document"
    )
    
    version = models.CharField(
        max_length=50,
        blank=True,
        help_text="Document version (e.g., '1.0', 'Rev A')"
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
        related_name='created_model_documents'
    )

    class Meta:
        verbose_name = "Model Document"
        verbose_name_plural = "Model Documents"
        ordering = ['equipment_category', 'document_type', 'title']
        unique_together = ['equipment_category', 'title', 'version']

    def __str__(self):
        return f"{self.title} - {self.equipment_category.name}"

    def clean(self):
        """Custom validation for model document."""
        if self.title:
            self.title = self.title.strip()
        if not self.title:
            raise ValidationError("Document title cannot be empty.")


class PortainerConfig(models.Model):
    """Configuration for Portainer integration."""
    portainer_url = models.URLField(max_length=500, blank=True, help_text="Portainer webhook URL (e.g., https://portainer:9000/api/stacks/webhooks/...)")
    portainer_user = models.CharField(max_length=100, blank=True, help_text="Portainer username for API access")
    portainer_password = models.CharField(max_length=255, blank=True, help_text="Portainer password for API access")
    stack_name = models.CharField(max_length=100, blank=True, help_text="Docker stack name in Portainer")
    webhook_secret = models.CharField(max_length=255, blank=True, help_text="Optional webhook secret for security")
    image_tag = models.CharField(max_length=50, blank=True, default='latest', help_text="Docker image tag to use for updates (e.g., latest, main, v1.0)")
    
    # Polling frequency options
    POLLING_CHOICES = [
        ('disabled', 'Disabled - Manual updates only'),
        ('5min', 'Every 5 minutes'),
        ('15min', 'Every 15 minutes'),
        ('30min', 'Every 30 minutes'),
        ('1hour', 'Every hour'),
        ('6hours', 'Every 6 hours'),
        ('12hours', 'Every 12 hours'),
        ('daily', 'Once per day'),
    ]
    polling_frequency = models.CharField(
        max_length=20, 
        choices=POLLING_CHOICES, 
        default='disabled',
        help_text="How often to automatically check for and pull the newest version"
    )
    
    # Git tracking for change detection
    last_commit_hash = models.CharField(max_length=100, blank=True, help_text="Last known git commit hash")
    last_commit_date = models.DateTimeField(null=True, blank=True, help_text="Last known git commit date")
    last_check_date = models.DateTimeField(null=True, blank=True, help_text="Last time we checked for changes")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Portainer Configuration"
        verbose_name_plural = "Portainer Configuration"
    
    def __str__(self):
        return f"Portainer Config - {self.portainer_url or 'Not configured'}"
    
    @classmethod
    def get_config(cls):
        """Get the current Portainer configuration, creating one if it doesn't exist."""
        config, created = cls.objects.get_or_create(pk=1)
        return config
    
    def save(self, *args, **kwargs):
        """Ensure only one configuration exists."""
        self.pk = 1
        super().save(*args, **kwargs)


class Logo(models.Model):
    """Site logo that can be managed by admins"""
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to='logos/')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Logo"
        verbose_name_plural = "Logos"

    def __str__(self):
        return self.name

class BrandingSettings(models.Model):
    """Global branding settings for the website"""
    site_name = models.CharField(max_length=200, default="Maintenance Dashboard", help_text="Main website name displayed in header")
    site_tagline = models.CharField(max_length=300, blank=True, help_text="Optional tagline below the site name")
    window_title_prefix = models.CharField(max_length=100, default="", help_text="Text to prepend to all page titles")
    window_title_suffix = models.CharField(max_length=100, default="", help_text="Text to append to all page titles")
    
    # Header customization
    header_brand_text = models.CharField(max_length=200, default="Maintenance Dashboard", help_text="Text displayed next to logo in header")
    navigation_overview_label = models.CharField(max_length=50, default="Overview", help_text="Label for Overview navigation item")
    navigation_equipment_label = models.CharField(max_length=50, default="Equipment", help_text="Label for Equipment navigation item")
    navigation_maintenance_label = models.CharField(max_length=50, default="Maintenance", help_text="Label for Maintenance navigation item")
    navigation_calendar_label = models.CharField(max_length=50, default="Calendar", help_text="Label for Calendar navigation item")
    navigation_map_label = models.CharField(max_length=50, default="Map", help_text="Label for Map navigation item")
    navigation_settings_label = models.CharField(max_length=50, default="Settings", help_text="Label for Settings navigation item")
    navigation_debug_label = models.CharField(max_length=50, default="Debug", help_text="Label for Debug navigation item")
    
    # Footer customization
    footer_copyright_text = models.CharField(max_length=200, default="© 2025 Maintenance Dashboard. All rights reserved.", help_text="Copyright text in footer")
    footer_powered_by_text = models.CharField(max_length=100, default="Powered by Django", help_text="Text displayed in footer")
    
    # Breadcrumb customization
    breadcrumb_enabled = models.BooleanField(default=True, help_text="Whether to show breadcrumbs globally")
    breadcrumb_home_text = models.CharField(max_length=50, default="Home", help_text="Text for the home breadcrumb link")
    breadcrumb_separator = models.CharField(max_length=10, default=">", help_text="Separator between breadcrumb items")
    
    # Theme customization
    primary_color = models.CharField(max_length=7, default="#4299e1", help_text="Primary color in hex format (#RRGGBB)")
    secondary_color = models.CharField(max_length=7, default="#2d3748", help_text="Secondary color in hex format (#RRGGBB)")
    accent_color = models.CharField(max_length=7, default="#3182ce", help_text="Accent color in hex format (#RRGGBB)")
    
    # Header and navigation colors
    header_background_color = models.CharField(max_length=7, default="#0f1419", help_text="Header background color in hex format (#RRGGBB)")
    header_text_color = models.CharField(max_length=7, default="#ffffff", help_text="Header text color in hex format (#RRGGBB)")
    header_border_color = models.CharField(max_length=7, default="#4a5568", help_text="Header border color in hex format (#RRGGBB)")
    navigation_background_color = models.CharField(max_length=7, default="#2d3748", help_text="Navigation background color in hex format (#RRGGBB)")
    navigation_text_color = models.CharField(max_length=7, default="#e2e8f0", help_text="Navigation text color in hex format (#RRGGBB)")
    navigation_hover_color = models.CharField(max_length=7, default="#4299e1", help_text="Navigation hover color in hex format (#RRGGBB)")
    
    # Content area colors
    content_background_color = models.CharField(max_length=7, default="#1a2238", help_text="Main content background color in hex format (#RRGGBB)")
    content_text_color = models.CharField(max_length=7, default="#e2e8f0", help_text="Main content text color in hex format (#RRGGBB)")
    card_background_color = models.CharField(max_length=7, default="#2d3748", help_text="Card background color in hex format (#RRGGBB)")
    card_border_color = models.CharField(max_length=7, default="#4a5568", help_text="Card border color in hex format (#RRGGBB)")
    
    # Button and form colors
    button_primary_color = models.CharField(max_length=7, default="#4299e1", help_text="Primary button background color in hex format (#RRGGBB)")
    button_primary_text_color = models.CharField(max_length=7, default="#ffffff", help_text="Primary button text color in hex format (#RRGGBB)")
    button_secondary_color = models.CharField(max_length=7, default="#718096", help_text="Secondary button background color in hex format (#RRGGBB)")
    button_secondary_text_color = models.CharField(max_length=7, default="#ffffff", help_text="Secondary button text color in hex format (#RRGGBB)")
    form_background_color = models.CharField(max_length=7, default="#2d3748", help_text="Form background color in hex format (#RRGGBB)")
    form_border_color = models.CharField(max_length=7, default="#4a5568", help_text="Form border color in hex format (#RRGGBB)")
    form_text_color = models.CharField(max_length=7, default="#e2e8f0", help_text="Form text color in hex format (#RRGGBB)")
    
    # Status colors
    success_color = models.CharField(max_length=7, default="#48bb78", help_text="Success color in hex format (#RRGGBB)")
    warning_color = models.CharField(max_length=7, default="#ed8936", help_text="Warning color in hex format (#RRGGBB)")
    danger_color = models.CharField(max_length=7, default="#f56565", help_text="Danger color in hex format (#RRGGBB)")
    info_color = models.CharField(max_length=7, default="#4299e1", help_text="Info color in hex format (#RRGGBB)")
    
    # Maintenance status colors for overview page
    status_color_scheduled = models.CharField(max_length=7, default="#808080", help_text="Scheduled status color")
    status_color_pending = models.CharField(max_length=7, default="#4299e1", help_text="Pending status color")
    status_color_in_progress = models.CharField(max_length=7, default="#ed8936", help_text="In Progress status color")
    status_color_cancelled = models.CharField(max_length=7, default="#000000", help_text="Cancelled status color")
    status_color_completed = models.CharField(max_length=7, default="#48bb78", help_text="Completed status color")
    status_color_overdue = models.CharField(max_length=7, default="#f56565", help_text="Overdue status color")
    
    # Dropdown and menu colors
    dropdown_background_color = models.CharField(max_length=7, default="#2d3748", help_text="Dropdown menu background color in hex format (#RRGGBB)")
    dropdown_background_opacity = models.DecimalField(max_digits=3, decimal_places=2, default=0.95, help_text="Dropdown background opacity (0.00 to 1.00)")
    dropdown_text_color = models.CharField(max_length=7, default="#e2e8f0", help_text="Dropdown menu text color in hex format (#RRGGBB)")
    dropdown_border_color = models.CharField(max_length=7, default="#4a5568", help_text="Dropdown menu border color in hex format (#RRGGBB)")
    dropdown_hover_background_color = models.CharField(max_length=7, default="#4a5568", help_text="Dropdown item hover background color in hex format (#RRGGBB)")
    dropdown_hover_text_color = models.CharField(max_length=7, default="#ffffff", help_text="Dropdown item hover text color in hex format (#RRGGBB)")
    
    # Breadcrumb colors
    breadcrumb_link_color = models.CharField(max_length=7, default="#4299e1", help_text="Breadcrumb link color in hex format (#RRGGBB)")
    breadcrumb_text_color = models.CharField(max_length=7, default="#a0aec0", help_text="Breadcrumb text color in hex format (#RRGGBB)")
    breadcrumb_separator_color = models.CharField(max_length=7, default="#a0aec0", help_text="Breadcrumb separator color in hex format (#RRGGBB)")
    
    # Table hover colors
    table_hover_background_color = models.CharField(max_length=7, default="#374151", help_text="Table row hover background color in hex format (#RRGGBB)")
    table_hover_text_color = models.CharField(max_length=7, default="#ffffff", help_text="Table row hover text color in hex format (#RRGGBB)")
    
    # Logo and favicon
    logo = models.ForeignKey(Logo, on_delete=models.SET_NULL, null=True, blank=True, help_text="Main site logo")
    favicon = models.ImageField(upload_to='favicons/', blank=True, help_text="Website favicon (16x16, 32x32, or 48x48 recommended)")
    
    # Meta settings
    is_active = models.BooleanField(default=True, help_text="Whether these branding settings are currently active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Branding Settings"
        verbose_name_plural = "Branding Settings"
    
    def __str__(self):
        return f"Branding Settings - {self.site_name}"
    
    def save(self, *args, **kwargs):
        # Ensure only one active branding settings instance
        if self.is_active:
            BrandingSettings.objects.exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)


class DashboardSettings(models.Model):
    """Dashboard/Overview page configuration settings"""
    
    # Visibility settings
    show_urgent_items = models.BooleanField(default=True, help_text="Show urgent items section")
    show_upcoming_items = models.BooleanField(default=True, help_text="Show upcoming items section")
    show_active_items = models.BooleanField(default=True, help_text="Show active items section (in progress and pending)")
    show_site_status = models.BooleanField(default=True, help_text="Show site status cards")
    show_kpi_cards = models.BooleanField(default=True, help_text="Show KPI cards at top")
    show_overview_data = models.BooleanField(default=True, help_text="Show overview data (pods/sites)")
    
    # Grouping settings
    group_urgent_by_site = models.BooleanField(default=True, help_text="Group urgent items by site")
    group_upcoming_by_site = models.BooleanField(default=True, help_text="Group upcoming items by site")
    group_active_by_site = models.BooleanField(default=True, help_text="Group active items by site")
    
    # Display limits
    max_urgent_items_per_site = models.IntegerField(default=15, help_text="Maximum urgent items to show per site")
    max_upcoming_items_per_site = models.IntegerField(default=15, help_text="Maximum upcoming items to show per site")
    max_active_items_per_site = models.IntegerField(default=15, help_text="Maximum active items to show per site")
    max_urgent_items_total = models.IntegerField(default=50, help_text="Maximum total urgent items across all sites")
    max_upcoming_items_total = models.IntegerField(default=50, help_text="Maximum total upcoming items across all sites")
    max_active_items_total = models.IntegerField(default=50, help_text="Maximum total active items across all sites")
    
    # Urgent items configuration
    urgent_days_ahead = models.IntegerField(default=7, help_text="Number of days ahead to consider items as urgent")
    upcoming_days_ahead = models.IntegerField(default=30, help_text="Number of days ahead to consider items as upcoming")
    
    # Meta settings
    is_active = models.BooleanField(default=True, help_text="Whether these dashboard settings are currently active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Dashboard Settings"
        verbose_name_plural = "Dashboard Settings"
    
    def __str__(self):
        return "Dashboard Settings"
    
    def save(self, *args, **kwargs):
        # Ensure only one active dashboard settings instance
        if self.is_active:
            DashboardSettings.objects.exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)
    
    @classmethod
    def get_active(cls):
        """Get the active dashboard settings, or create default if none exists"""
        settings = cls.objects.filter(is_active=True).first()
        if not settings:
            settings = cls.objects.create(is_active=True)
        return settings

class CSSCustomization(models.Model):
    """CSS customizations for different item types and components"""
    ITEM_TYPE_CHOICES = [
        ('header', 'Header'),
        ('navigation', 'Navigation'),
        ('dashboard', 'Dashboard'),
        ('equipment', 'Equipment'),
        ('maintenance', 'Maintenance'),
        ('calendar', 'Calendar'),
        ('map', 'Map'),
        ('settings', 'Settings'),
        ('forms', 'Forms'),
        ('tables', 'Tables'),
        ('buttons', 'Buttons'),
        ('cards', 'Cards'),
        ('modals', 'Modals'),
        ('alerts', 'Alerts'),
        ('breadcrumbs', 'Breadcrumbs'),
        ('footer', 'Footer'),
        ('global', 'Global'),
    ]
    
    name = models.CharField(max_length=100, help_text="Name for this CSS customization")
    item_type = models.CharField(max_length=20, choices=ITEM_TYPE_CHOICES, help_text="Type of item this CSS affects")
    description = models.TextField(blank=True, help_text="Description of what this CSS customization does")
    
    # CSS content
    css_code = models.TextField(help_text="CSS code (without <style> tags)")
    is_active = models.BooleanField(default=True, help_text="Whether this CSS customization is currently active")
    
    # Priority and ordering
    priority = models.IntegerField(default=0, help_text="Higher priority CSS loads later (overrides earlier CSS)")
    order = models.IntegerField(default=0, help_text="Order within the same priority level")
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "CSS Customization"
        verbose_name_plural = "CSS Customizations"
        ordering = ['-priority', 'order', 'name']
    
    def __str__(self):
        return f"{self.get_item_type_display()} - {self.name}"
    
    def get_css_with_comments(self):
        """Return CSS with descriptive comments"""
        comments = f"/* {self.name} - {self.description} */\n"
        return comments + self.css_code