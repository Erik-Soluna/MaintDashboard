"""
Equipment models for the maintenance dashboard.
Fixed associations and validation from the original web2py code.
"""

from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from core.models import TimeStampedModel, EquipmentCategory, Location, NaturalSortManager
import json


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
    
    def apply_category_schedules(self, user=None):
        """
        Apply category-based schedules to this equipment.
        Called automatically when equipment is created.
        """
        from maintenance.models import EquipmentCategorySchedule, GlobalSchedule, ScheduleOverride
        
        if not self.category:
            return
        
        # Apply category schedules
        category_schedules = EquipmentCategorySchedule.objects.filter(
            equipment_category=self.category,
            is_active=True
        )
        
        for category_schedule in category_schedules:
            # Check if there's already an override for this activity type
            override = ScheduleOverride.objects.filter(
                equipment=self,
                activity_type=category_schedule.activity_type
            ).first()
            
            if not override and category_schedule.allow_override:
                # Create a default override based on category schedule
                ScheduleOverride.objects.create(
                    equipment=self,
                    activity_type=category_schedule.activity_type,
                    auto_generate=category_schedule.auto_generate,
                    advance_notice_days=category_schedule.advance_notice_days,
                    default_priority=category_schedule.default_priority,
                    default_duration_hours=category_schedule.default_duration_hours,
                    created_by=user
                )
        
        # Apply global schedules
        global_schedules = GlobalSchedule.objects.filter(is_active=True)
        
        for global_schedule in global_schedules:
            # Check if there's already an override for this activity type
            override = ScheduleOverride.objects.filter(
                equipment=self,
                activity_type=global_schedule.activity_type
            ).first()
            
            if not override and global_schedule.allow_override:
                # Create a default override based on global schedule
                ScheduleOverride.objects.create(
                    equipment=self,
                    activity_type=global_schedule.activity_type,
                    auto_generate=global_schedule.auto_generate,
                    advance_notice_days=global_schedule.advance_notice_days,
                    default_priority=global_schedule.default_priority,
                    default_duration_hours=global_schedule.default_duration_hours,
                    created_by=user
                )
    
    def get_effective_schedule(self, activity_type):
        """
        Get the effective schedule for a specific activity type.
        Returns the override if it exists, otherwise returns category/global schedule.
        """
        from maintenance.models import ScheduleOverride, EquipmentCategorySchedule, GlobalSchedule
        
        # Check for override first
        override = ScheduleOverride.objects.filter(
            equipment=self,
            activity_type=activity_type,
            is_active=True
        ).first()
        
        if override:
            return {
                'type': 'override',
                'object': override,
                'frequency': override.get_effective_frequency(),
                'frequency_days': override.get_effective_frequency_days(),
                'auto_generate': override.auto_generate,
                'advance_notice_days': override.advance_notice_days,
                'priority': override.default_priority,
                'duration_hours': override.default_duration_hours,
            }
        
        # Check for category schedule
        if self.category:
            category_schedule = EquipmentCategorySchedule.objects.filter(
                equipment_category=self.category,
                activity_type=activity_type,
                is_active=True
            ).first()
            
            if category_schedule:
                return {
                    'type': 'category',
                    'object': category_schedule,
                    'frequency': category_schedule.frequency,
                    'frequency_days': category_schedule.get_frequency_in_days(),
                    'auto_generate': category_schedule.auto_generate,
                    'advance_notice_days': category_schedule.advance_notice_days,
                    'priority': category_schedule.default_priority,
                    'duration_hours': category_schedule.default_duration_hours,
                }
        
        # Check for global schedule
        global_schedule = GlobalSchedule.objects.filter(
            activity_type=activity_type,
            is_active=True
        ).first()
        
        if global_schedule:
            return {
                'type': 'global',
                'object': global_schedule,
                'frequency': global_schedule.frequency,
                'frequency_days': global_schedule.get_frequency_in_days(),
                'auto_generate': global_schedule.auto_generate,
                'advance_notice_days': global_schedule.advance_notice_days,
                'priority': global_schedule.default_priority,
                'duration_hours': global_schedule.default_duration_hours,
            }
        
        return None
    
    def save(self, *args, **kwargs):
        """Override save to automatically apply category schedules."""
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Apply category schedules for new equipment
        if is_new:
            self.apply_category_schedules()

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
            
        # Note: DGA due date can legitimately be after next maintenance date
        # as they are independent maintenance schedules

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
    
    def get_custom_fields(self):
        """Get all custom fields for this equipment's category."""
        if not self.category:
            return EquipmentCategoryField.objects.none()
        return self.category.custom_fields.filter(is_active=True).order_by('sort_order')
    
    def get_custom_value(self, field_name):
        """Get the value of a custom field by name."""
        try:
            field = self.category.custom_fields.get(name=field_name, is_active=True)
            value_obj = self.custom_values.filter(field=field).first()
            if value_obj:
                return value_obj.get_display_value()
            return field.default_value
        except EquipmentCategoryField.DoesNotExist:
            return None
    
    def set_custom_value(self, field_name, value):
        """Set the value of a custom field by name."""
        try:
            field = self.category.custom_fields.get(name=field_name, is_active=True)
            value_obj, created = self.custom_values.get_or_create(field=field)
            value_obj.set_value(value)
            value_obj.save()
            return value_obj
        except EquipmentCategoryField.DoesNotExist:
            return None
    
    def get_custom_values_dict(self):
        """Get all custom values as a dictionary."""
        result = {}
        for field in self.get_custom_fields():
            result[field.name] = self.get_custom_value(field.name)
        return result
    
    def get_custom_fields_by_group(self):
        """Get custom fields grouped by field_group."""
        fields = self.get_custom_fields()
        groups = {}
        for field in fields:
            group = field.field_group or 'General'
            if group not in groups:
                groups[group] = []
            groups[group].append(field)
        return groups

    def get_conditional_fields(self):
        """Get conditional fields assigned to this equipment's category."""
        if not self.category:
            return EquipmentCategoryConditionalField.objects.none()
        
        return EquipmentCategoryConditionalField.objects.filter(
            target_category=self.category,
            is_active=True
        ).select_related('field', 'source_category').order_by('override_sort_order', 'field__sort_order')

    def get_all_custom_fields(self):
        """Get both native and conditional custom fields for this equipment."""
        # Get native fields from the equipment's category
        native_fields = self.get_custom_fields()
        
        # Get conditional fields assigned to this category
        conditional_fields = self.get_conditional_fields()
        
        # Create a combined list with conditional field overrides
        all_fields = []
        
        # Add native fields
        for field in native_fields:
            all_fields.append({
                'field': field,
                'is_conditional': False,
                'source_category': field.category,
                'effective_label': field.label,
                'effective_help_text': field.help_text,
                'effective_required': field.required,
                'effective_default_value': field.default_value,
                'effective_sort_order': field.sort_order,
                'effective_field_group': field.field_group or 'General',
            })
        
        # Add conditional fields
        for conditional in conditional_fields:
            all_fields.append({
                'field': conditional.field,
                'is_conditional': True,
                'source_category': conditional.source_category,
                'effective_label': conditional.get_effective_label(),
                'effective_help_text': conditional.get_effective_help_text(),
                'effective_required': conditional.get_effective_required(),
                'effective_default_value': conditional.get_effective_default_value(),
                'effective_sort_order': conditional.get_effective_sort_order(),
                'effective_field_group': conditional.get_effective_field_group(),
            })
        
        # Sort by effective sort order
        all_fields.sort(key=lambda x: x['effective_sort_order'])
        return all_fields

    def get_all_custom_fields_by_group(self):
        """Get all custom fields (native and conditional) grouped by field_group."""
        fields = self.get_all_custom_fields()
        groups = {}
        for field_info in fields:
            group = field_info['effective_field_group']
            if group not in groups:
                groups[group] = []
            groups[group].append(field_info)
        return groups

    def get_conditional_value(self, field_name):
        """Get the value of a conditional field by name."""
        try:
            conditional = self.get_conditional_fields().get(field__name=field_name)
            value_obj = self.custom_values.filter(field=conditional.field).first()
            if value_obj:
                return value_obj.get_display_value()
            return conditional.get_effective_default_value()
        except EquipmentCategoryConditionalField.DoesNotExist:
            return None

    def set_conditional_value(self, field_name, value):
        """Set the value of a conditional field by name."""
        try:
            conditional = self.get_conditional_fields().get(field__name=field_name)
            value_obj, created = self.custom_values.get_or_create(field=conditional.field)
            value_obj.set_value(value)
            value_obj.save()
            return value_obj
        except EquipmentCategoryConditionalField.DoesNotExist:
            return None
    
    def is_offline(self):
        """Check if this equipment is offline."""
        return self.status in ['inactive', 'maintenance', 'retired'] or not self.is_active
    
    def get_upstream_equipment(self):
        """Get all upstream equipment that this equipment depends on."""
        from equipment.models import EquipmentConnection
        connections = EquipmentConnection.objects.filter(
            downstream_equipment=self,
            is_active=True
        ).select_related('upstream_equipment')
        return [conn.upstream_equipment for conn in connections]
    
    def get_downstream_equipment(self):
        """Get all downstream equipment that depends on this equipment."""
        from equipment.models import EquipmentConnection
        connections = EquipmentConnection.objects.filter(
            upstream_equipment=self,
            is_active=True
        ).select_related('downstream_equipment')
        return [conn.downstream_equipment for conn in connections]
    
    def get_effective_status(self):
        """
        Get the effective status considering cascading offline from upstream equipment.
        Returns the actual status or 'cascade_offline' if upstream equipment is offline.
        """
        # First check own status
        if self.is_offline():
            return self.status
        
        # Check if any critical upstream equipment is offline
        from equipment.models import EquipmentConnection
        critical_upstream = EquipmentConnection.objects.filter(
            downstream_equipment=self,
            is_active=True,
            is_critical=True
        ).select_related('upstream_equipment')
        
        for connection in critical_upstream:
            upstream = connection.upstream_equipment
            # Recursively check upstream status
            upstream_status = upstream.get_effective_status()
            if upstream_status in ['inactive', 'maintenance', 'retired', 'cascade_offline']:
                return 'cascade_offline'
        
        return self.status
    
    def get_all_affected_downstream(self):
        """
        Get all equipment that would be affected if this equipment goes offline.
        Returns a list of equipment that are downstream through critical connections.
        """
        affected = []
        visited = set()
        to_check = [self]
        
        while to_check:
            current = to_check.pop(0)
            if current.id in visited:
                continue
            visited.add(current.id)
            
            # Get all downstream equipment through critical connections
            from equipment.models import EquipmentConnection
            critical_downstream = EquipmentConnection.objects.filter(
                upstream_equipment=current,
                is_active=True,
                is_critical=True
            ).select_related('downstream_equipment')
            
            for connection in critical_downstream:
                downstream = connection.downstream_equipment
                if downstream.id not in visited:
                    affected.append(downstream)
                    to_check.append(downstream)
        
        return affected
    
    def get_connection_to(self, other_equipment):
        """Get the connection from this equipment to another equipment."""
        from equipment.models import EquipmentConnection
        return EquipmentConnection.objects.filter(
            upstream_equipment=self,
            downstream_equipment=other_equipment,
            is_active=True
        ).first()
    
    def get_connection_from(self, other_equipment):
        """Get the connection from another equipment to this equipment."""
        from equipment.models import EquipmentConnection
        return EquipmentConnection.objects.filter(
            upstream_equipment=other_equipment,
            downstream_equipment=self,
            is_active=True
        ).first()


class EquipmentConnection(TimeStampedModel):
    """
    Connections between equipment showing upstream/downstream dependencies.
    Used to track power, data, or other dependencies between equipment.
    """
    
    CONNECTION_TYPE_CHOICES = [
        ('power', 'Power Supply'),
        ('data', 'Data Connection'),
        ('cooling', 'Cooling System'),
        ('control', 'Control System'),
        ('mechanical', 'Mechanical'),
        ('other', 'Other'),
    ]
    
    upstream_equipment = models.ForeignKey(
        Equipment,
        on_delete=models.CASCADE,
        related_name='downstream_connections',
        help_text="Equipment that supplies power/data/service to downstream equipment"
    )
    downstream_equipment = models.ForeignKey(
        Equipment,
        on_delete=models.CASCADE,
        related_name='upstream_connections',
        help_text="Equipment that depends on the upstream equipment"
    )
    connection_type = models.CharField(
        max_length=20,
        choices=CONNECTION_TYPE_CHOICES,
        default='power',
        help_text="Type of connection between equipment"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of the connection"
    )
    is_critical = models.BooleanField(
        default=True,
        help_text="If True, downstream equipment goes offline when upstream is offline"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this connection is currently active"
    )
    
    class Meta:
        verbose_name = "Equipment Connection"
        verbose_name_plural = "Equipment Connections"
        ordering = ['upstream_equipment', 'downstream_equipment']
        unique_together = ['upstream_equipment', 'downstream_equipment']
        indexes = [
            models.Index(fields=['upstream_equipment']),
            models.Index(fields=['downstream_equipment']),
            models.Index(fields=['connection_type', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.upstream_equipment.name} → {self.downstream_equipment.name} ({self.get_connection_type_display()})"
    
    def clean(self):
        """Validate connection."""
        if self.upstream_equipment == self.downstream_equipment:
            raise ValidationError("Equipment cannot connect to itself.")
        
        # Check for circular dependencies
        if self._creates_circular_dependency():
            raise ValidationError(
                f"This connection would create a circular dependency. "
                f"{self.downstream_equipment.name} is already upstream of {self.upstream_equipment.name}."
            )
    
    def _creates_circular_dependency(self):
        """Check if this connection would create a circular dependency."""
        if not self.downstream_equipment or not self.upstream_equipment:
            return False
        
        # Check if upstream is already downstream of the proposed downstream
        visited = set()
        to_check = [self.downstream_equipment]
        
        while to_check:
            current = to_check.pop(0)
            if current.id in visited:
                continue
            visited.add(current.id)
            
            # If we found the upstream equipment in the downstream chain, it's circular
            if current == self.upstream_equipment:
                return True
            
            # Add all downstream equipment of current to check
            for conn in current.downstream_connections.filter(is_active=True):
                if conn.downstream_equipment.id not in visited:
                    to_check.append(conn.downstream_equipment)
        
        return False


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
        ('maintenance', 'Maintenance Report'),
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


class EquipmentCategoryField(TimeStampedModel):
    """
    Custom fields for equipment categories.
    This allows each category to have its own specific fields.
    """
    
    FIELD_TYPE_CHOICES = [
        ('text', 'Text'),
        ('textarea', 'Long Text'),
        ('number', 'Number'),
        ('decimal', 'Decimal'),
        ('date', 'Date'),
        ('datetime', 'Date & Time'),
        ('boolean', 'Yes/No'),
        ('select', 'Dropdown'),
        ('multiselect', 'Multiple Choice'),
        ('url', 'URL'),
        ('email', 'Email'),
        ('phone', 'Phone Number'),
    ]
    
    category = models.ForeignKey(
        EquipmentCategory,
        on_delete=models.CASCADE,
        related_name='custom_fields',
        help_text="Equipment category this field belongs to"
    )
    
    name = models.CharField(
        max_length=100,
        help_text="Field name (internal use)"
    )
    
    label = models.CharField(
        max_length=200,
        help_text="Display label for the field"
    )
    
    field_type = models.CharField(
        max_length=20,
        choices=FIELD_TYPE_CHOICES,
        default='text',
        help_text="Type of field"
    )
    
    required = models.BooleanField(
        default=False,
        help_text="Is this field required?"
    )
    
    help_text = models.TextField(
        blank=True,
        help_text="Help text to display with the field"
    )
    
    default_value = models.TextField(
        blank=True,
        help_text="Default value for the field"
    )
    
    # For select/multiselect fields
    choices = models.TextField(
        blank=True,
        help_text="Comma-separated choices for select fields"
    )
    
    # Validation
    min_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Minimum value for number fields"
    )
    
    max_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Maximum value for number fields"
    )
    
    max_length = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum length for text fields"
    )
    
    # Display options
    sort_order = models.PositiveIntegerField(
        default=0,
        help_text="Order for displaying fields"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Is this field active?"
    )
    
    # Grouping
    field_group = models.CharField(
        max_length=100,
        blank=True,
        help_text="Group name for organizing fields (e.g., 'Electrical', 'Mechanical')"
    )

    class Meta:
        verbose_name = "Equipment Category Field"
        verbose_name_plural = "Equipment Category Fields"
        ordering = ['category', 'sort_order', 'name']
        unique_together = ['category', 'name']

    def __str__(self):
        return f"{self.category.name} - {self.label}"

    def clean(self):
        """Validate field configuration."""
        if self.name:
            self.name = self.name.strip().lower().replace(' ', '_')
        if not self.name:
            raise ValidationError("Field name cannot be empty.")
        
        if self.label:
            self.label = self.label.strip()
        if not self.label:
            raise ValidationError("Field label cannot be empty.")
        
        # Validate choices for select fields
        if self.field_type in ['select', 'multiselect'] and not self.choices:
            raise ValidationError("Select fields must have choices defined.")
        
        # Validate numeric constraints
        if self.min_value and self.max_value and self.min_value > self.max_value:
            raise ValidationError("Minimum value cannot be greater than maximum value.")

    def get_choices_list(self):
        """Get choices as a list of tuples."""
        if not self.choices:
            return []
        return [(choice.strip(), choice.strip()) for choice in self.choices.split(',') if choice.strip()]


class EquipmentCustomValue(TimeStampedModel):
    """
    Values for custom fields on equipment.
    This stores the actual values for each equipment's custom fields.
    """
    
    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.CASCADE,
        related_name='custom_values',
        help_text="Equipment this value belongs to"
    )
    
    field = models.ForeignKey(
        EquipmentCategoryField,
        on_delete=models.CASCADE,
        related_name='values',
        help_text="Custom field this value belongs to"
    )
    
    value = models.TextField(
        blank=True,
        help_text="Value for the custom field"
    )
    
    # For multiselect fields, store as JSON array
    values_json = models.TextField(
        blank=True,
        help_text="JSON array for multiselect values"
    )

    class Meta:
        verbose_name = "Equipment Custom Value"
        verbose_name_plural = "Equipment Custom Values"
        ordering = ['equipment', 'field__sort_order']
        unique_together = ['equipment', 'field']

    def __str__(self):
        return f"{self.equipment.name} - {self.field.label}: {self.value}"

    def clean(self):
        """Validate custom value."""
        # Validate based on field type
        if self.field.field_type == 'number':
            try:
                float(self.value)
            except (ValueError, TypeError):
                if self.value:  # Only validate if not empty
                    raise ValidationError("Value must be a number.")
        
        elif self.field.field_type == 'decimal':
            try:
                float(self.value)
            except (ValueError, TypeError):
                if self.value:  # Only validate if not empty
                    raise ValidationError("Value must be a decimal number.")
        
        elif self.field.field_type == 'date':
            from django.utils.dateparse import parse_date
            if self.value and not parse_date(self.value):
                raise ValidationError("Value must be a valid date (YYYY-MM-DD).")
        
        elif self.field.field_type == 'datetime':
            from django.utils.dateparse import parse_datetime
            if self.value and not parse_datetime(self.value):
                raise ValidationError("Value must be a valid date and time.")
        
        elif self.field.field_type == 'email':
            from django.core.validators import validate_email
            if self.value:
                try:
                    validate_email(self.value)
                except ValidationError:
                    raise ValidationError("Value must be a valid email address.")
        
        elif self.field.field_type == 'url':
            from django.core.validators import URLValidator
            if self.value:
                try:
                    URLValidator()(self.value)
                except ValidationError:
                    raise ValidationError("Value must be a valid URL.")
        
        elif self.field.field_type == 'multiselect':
            if self.values_json:
                try:
                    json.loads(self.values_json)
                except json.JSONDecodeError:
                    raise ValidationError("Multiselect values must be valid JSON.")

    def get_display_value(self):
        """Get the display value based on field type."""
        if self.field.field_type == 'boolean':
            return "Yes" if self.value.lower() in ['true', '1', 'yes', 'on'] else "No"
        
        elif self.field.field_type == 'multiselect':
            if self.values_json:
                try:
                    values = json.loads(self.values_json)
                    return ", ".join(values)
                except json.JSONDecodeError:
                    return self.values_json
            return self.value
        
        elif self.field.field_type == 'select':
            # Return the choice label if it exists
            choices = self.field.get_choices_list()
            for choice_value, choice_label in choices:
                if choice_value == self.value:
                    return choice_label
            return self.value
        
        return self.value

    def set_value(self, value):
        """Set the value based on field type."""
        if self.field.field_type == 'multiselect':
            if isinstance(value, list):
                self.values_json = json.dumps(value)
                self.value = ", ".join(value)
            else:
                self.value = str(value)
                self.values_json = json.dumps([str(value)])
        else:
            self.value = str(value) if value is not None else ""
            self.values_json = ""


class EquipmentCategoryConditionalField(TimeStampedModel):
    """
    Conditional field assignments for equipment categories.
    This allows configuring which fields are available for specific equipment categories.
    For example: "oil_type" field only for "Transformers" category, not for "Switchgear".
    """
    
    source_category = models.ForeignKey(
        EquipmentCategory,
        on_delete=models.CASCADE,
        related_name='conditional_field_sources',
        help_text="Equipment category that provides the field"
    )
    
    target_category = models.ForeignKey(
        EquipmentCategory,
        on_delete=models.CASCADE,
        related_name='conditional_field_targets',
        help_text="Equipment category that receives the field"
    )
    
    field = models.ForeignKey(
        EquipmentCategoryField,
        on_delete=models.CASCADE,
        related_name='conditional_assignments',
        help_text="The field to conditionally assign"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Is this conditional field assignment active?"
    )
    
    # Optional: Override field properties for the target category
    override_label = models.CharField(
        max_length=200,
        blank=True,
        help_text="Override the field label for this category (optional)"
    )
    
    override_help_text = models.TextField(
        blank=True,
        help_text="Override the help text for this category (optional)"
    )
    
    override_required = models.BooleanField(
        null=True,
        blank=True,
        help_text="Override the required setting for this category (optional)"
    )
    
    override_default_value = models.TextField(
        blank=True,
        help_text="Override the default value for this category (optional)"
    )
    
    override_sort_order = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Override the sort order for this category (optional)"
    )
    
    override_field_group = models.CharField(
        max_length=100,
        blank=True,
        help_text="Override the field group for this category (optional)"
    )

    class Meta:
        verbose_name = "Equipment Category Conditional Field"
        verbose_name_plural = "Equipment Category Conditional Fields"
        ordering = ['target_category', 'override_sort_order', 'field__sort_order']
        unique_together = ['target_category', 'field']
        indexes = [
            models.Index(fields=['source_category', 'target_category']),
            models.Index(fields=['target_category', 'is_active']),
        ]

    def __str__(self):
        return f"{self.target_category.name} ← {self.field.label} (from {self.source_category.name})"

    def clean(self):
        """Validate conditional field assignment."""
        if self.source_category == self.target_category:
            raise ValidationError("Source and target categories cannot be the same.")
        
        # Ensure the field belongs to the source category
        if self.field.category != self.source_category:
            raise ValidationError("Field must belong to the source category.")

    def get_effective_label(self):
        """Get the effective label (original or override)."""
        return self.override_label or self.field.label

    def get_effective_help_text(self):
        """Get the effective help text (original or override)."""
        return self.override_help_text or self.field.help_text

    def get_effective_required(self):
        """Get the effective required setting (original or override)."""
        if self.override_required is not None:
            return self.override_required
        return self.field.required

    def get_effective_default_value(self):
        """Get the effective default value (original or override)."""
        return self.override_default_value or self.field.default_value

    def get_effective_sort_order(self):
        """Get the effective sort order (original or override)."""
        return self.override_sort_order or self.field.sort_order

    def get_effective_field_group(self):
        """Get the effective field group (original or override)."""
        return self.override_field_group or self.field.field_group or 'General'