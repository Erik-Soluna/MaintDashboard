THIS SHOULD BE A LINTER ERROR"""
Admin interface for equipment models.
"""

from django.contrib import admin
from .models import Equipment, EquipmentDocument, EquipmentComponent


class EquipmentDocumentInline(admin.TabularInline):
    model = EquipmentDocument
    extra = 0
    readonly_fields = ['created_at', 'created_by']


class EquipmentComponentInline(admin.TabularInline):
    model = EquipmentComponent
    extra = 0
    readonly_fields = ['created_at', 'created_by']


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'category', 'location', 'status', 
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
    inlines = [EquipmentDocumentInline, EquipmentComponentInline]
    
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
    list_display = ['title', 'equipment', 'document_type', 'version', 'is_current', 'created_at']
    list_filter = ['document_type', 'is_current', 'created_at']
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