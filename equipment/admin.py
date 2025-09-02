"""
Admin interface for equipment models.
"""

from django.contrib import admin
from .models import Equipment, EquipmentDocument, EquipmentComponent, EquipmentCategoryField, EquipmentCustomValue, EquipmentCategoryConditionalField


class EquipmentDocumentInline(admin.TabularInline):
    model = EquipmentDocument
    extra = 0
    readonly_fields = ['created_at', 'created_by']


class EquipmentComponentInline(admin.TabularInline):
    model = EquipmentComponent
    extra = 0
    readonly_fields = ['created_at', 'created_by']


class EquipmentCustomValueInline(admin.TabularInline):
    model = EquipmentCustomValue
    extra = 0
    readonly_fields = ['created_at', 'created_by']
    fields = ['field', 'value', 'values_json']


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'category', 'get_site', 'location', 'status', 
        'manufacturer_serial', 'asset_tag', 'created_at'
    ]
    list_filter = [
        'status', 'category', 'location', 'is_active', 
        'created_at', 'next_maintenance_date'
    ]
    search_fields = [
        'name', 'manufacturer_serial', 'asset_tag',
        'manufacturer', 'model_number'
    ]
    readonly_fields = [
        'created_at', 'updated_at', 'created_by', 'updated_by'
    ]
    inlines = [EquipmentDocumentInline, EquipmentComponentInline, EquipmentCustomValueInline]
    
    def get_site(self, obj):
        """Get the site location for this equipment."""
        site = obj.get_site()
        return site.name if site else 'No Site'
    get_site.short_description = 'Site'
    get_site.admin_order_field = 'location__parent_location__name'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'category', 'status', 'is_active')
        }),
        ('Identification', {
            'fields': ('manufacturer_serial', 'asset_tag', 'manufacturer', 'model_number')
        }),
        ('Location', {
            'fields': ('location',)
        }),
        ('Technical Specifications', {
            'fields': ('power_ratings', 'trip_setpoints', 'installed_upgrades'),
            'classes': ('collapse',)
        }),
        ('Documentation', {
            'fields': ('datasheet', 'schematics', 'warranty_details'),
            'classes': ('collapse',)
        }),
        ('Maintenance Tracking', {
            'fields': (
                'dga_due_date', 'next_maintenance_date', 
                'commissioning_date', 'warranty_expiry_date'
            ),
            'classes': ('collapse',)
        }),
        ('Audit Information', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # Creating new object
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
        
    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            if not instance.pk:  # New instance
                instance.created_by = request.user
            instance.updated_by = request.user
            instance.save()
        formset.save_m2m()


@admin.register(EquipmentDocument)
class EquipmentDocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'equipment', 'document_type', 'is_active', 'created_at']
    list_filter = ['document_type', 'is_active', 'created_at']
    search_fields = ['title', 'equipment__name', 'description']
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(EquipmentComponent)
class EquipmentComponentAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'equipment', 'part_number', 'quantity', 
        'is_critical', 'next_replacement_date'
    ]
    list_filter = ['is_critical', 'equipment__category', 'created_at']
    search_fields = ['name', 'equipment__name', 'part_number']
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(EquipmentCategoryField)
class EquipmentCategoryFieldAdmin(admin.ModelAdmin):
    list_display = [
        'label', 'category', 'field_type', 'required', 
        'field_group', 'sort_order', 'is_active'
    ]
    list_filter = [
        'field_type', 'required', 'field_group', 'is_active', 
        'category', 'created_at'
    ]
    search_fields = ['name', 'label', 'category__name', 'help_text']
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    
    fieldsets = (
        ('Field Information', {
            'fields': ('category', 'name', 'label', 'field_type', 'required')
        }),
        ('Field Configuration', {
            'fields': ('help_text', 'default_value', 'choices', 'field_group', 'sort_order')
        }),
        ('Validation', {
            'fields': ('min_value', 'max_value', 'max_length'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Audit Information', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(EquipmentCustomValue)
class EquipmentCustomValueAdmin(admin.ModelAdmin):
    list_display = [
        'equipment', 'field', 'get_display_value', 'created_at'
    ]
    list_filter = [
        'field__category', 'field__field_type', 'created_at'
    ]
    search_fields = [
        'equipment__name', 'field__label', 'value'
    ]
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    
    def get_display_value(self, obj):
        return obj.get_display_value()
    get_display_value.short_description = 'Value'
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(EquipmentCategoryConditionalField)
class EquipmentCategoryConditionalFieldAdmin(admin.ModelAdmin):
    list_display = [
        'target_category', 'field', 'source_category', 'is_active', 'get_effective_label'
    ]
    list_filter = [
        'target_category', 'source_category', 'is_active', 'created_at'
    ]
    search_fields = [
        'target_category__name', 'source_category__name', 'field__label', 'field__name'
    ]
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    
    fieldsets = (
        ('Field Assignment', {
            'fields': ('source_category', 'target_category', 'field', 'is_active')
        }),
        ('Field Overrides', {
            'fields': (
                'override_label', 'override_help_text', 'override_required',
                'override_default_value', 'override_sort_order', 'override_field_group'
            ),
            'classes': ('collapse',)
        }),
        ('Audit Information', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    
    def get_effective_label(self, obj):
        return obj.get_effective_label()
    get_effective_label.short_description = 'Effective Label'
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)