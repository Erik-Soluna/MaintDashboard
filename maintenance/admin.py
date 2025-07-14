"""
Admin interface for maintenance models.
"""

from django.contrib import admin
from .models import (
    MaintenanceActivityType, MaintenanceActivity, MaintenanceChecklist, 
    MaintenanceSchedule, ActivityTypeCategory, ActivityTypeTemplate, MaintenanceReport
)


@admin.register(ActivityTypeCategory)
class ActivityTypeCategoryAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'description', 'color', 'icon', 'sort_order', 'is_active', 'created_at'
    ]
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    ordering = ['sort_order', 'name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'sort_order', 'is_active')
        }),
        ('Visual Settings', {
            'fields': ('color', 'icon')
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


@admin.register(ActivityTypeTemplate)
class ActivityTypeTemplateAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'equipment_category', 'category', 'estimated_duration_hours',
        'frequency_days', 'is_mandatory', 'is_active', 'created_at'
    ]
    list_filter = [
        'equipment_category', 'category', 'is_mandatory', 'is_active', 'created_at'
    ]
    search_fields = ['name', 'description', 'equipment_category__name']
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    ordering = ['equipment_category', 'sort_order', 'name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'equipment_category', 'category', 'description', 'sort_order')
        }),
        ('Timing & Requirements', {
            'fields': ('estimated_duration_hours', 'frequency_days', 'is_mandatory')
        }),
        ('Default Settings', {
            'fields': ('default_tools_required', 'default_parts_required', 'default_safety_notes'),
            'classes': ('collapse',)
        }),
        ('Checklist Template', {
            'fields': ('checklist_template',),
            'classes': ('collapse',)
        }),
        ('Settings', {
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


class MaintenanceChecklistInline(admin.TabularInline):
    model = MaintenanceChecklist
    extra = 0
    readonly_fields = ['completed_at', 'completed_by']


@admin.register(MaintenanceActivityType)
class MaintenanceActivityTypeAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'category', 'template', 'frequency_days', 'estimated_duration_hours',
        'is_mandatory', 'is_active', 'created_at'
    ]
    list_filter = ['category', 'template', 'is_mandatory', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    filter_horizontal = ['applicable_equipment_categories']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'category', 'template', 'description')
        }),
        ('Timing & Requirements', {
            'fields': ('estimated_duration_hours', 'frequency_days', 'is_mandatory')
        }),
        ('Requirements', {
            'fields': ('tools_required', 'parts_required', 'safety_notes'),
            'classes': ('collapse',)
        }),
        ('Equipment Categories', {
            'fields': ('applicable_equipment_categories',)
        }),
        ('Settings', {
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


@admin.register(MaintenanceActivity)
class MaintenanceActivityAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'equipment', 'activity_type', 'status', 'priority',
        'scheduled_start', 'assigned_to', 'created_at'
    ]
    list_filter = [
        'status', 'priority', 'activity_type', 'equipment__category',
        'scheduled_start', 'created_at'
    ]
    search_fields = [
        'title', 'equipment__name', 'activity_type__name', 'description'
    ]
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    inlines = [MaintenanceChecklistInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('equipment', 'activity_type', 'title', 'description')
        }),
        ('Status & Assignment', {
            'fields': ('status', 'priority', 'assigned_to')
        }),
        ('Scheduling', {
            'fields': (
                'scheduled_start', 'scheduled_end',
                'actual_start', 'actual_end', 'next_due_date'
            )
        }),
        ('Requirements', {
            'fields': (
                'required_status', 'tools_required', 
                'parts_required', 'safety_notes'
            ),
            'classes': ('collapse',)
        }),
        ('Completion', {
            'fields': ('completion_notes',),
            'classes': ('collapse',)
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


@admin.register(MaintenanceChecklist)
class MaintenanceChecklistAdmin(admin.ModelAdmin):
    list_display = [
        'activity', 'order', 'item_text', 'is_completed',
        'completed_by', 'completed_at'
    ]
    list_filter = ['is_completed', 'is_required', 'activity__status']
    search_fields = ['item_text', 'activity__title', 'notes']
    readonly_fields = ['completed_at', 'created_at', 'updated_at']
    
    def save_model(self, request, obj, form, change):
        if obj.is_completed and not obj.completed_by:
            obj.completed_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(MaintenanceSchedule)
class MaintenanceScheduleAdmin(admin.ModelAdmin):
    list_display = [
        'equipment', 'activity_type', 'frequency', 
        'start_date', 'last_generated', 'is_active'
    ]
    list_filter = [
        'frequency', 'is_active', 'auto_generate',
        'equipment__category', 'activity_type'
    ]
    search_fields = ['equipment__name', 'activity_type__name']
    readonly_fields = [
        'last_generated', 'created_at', 'updated_at', 'created_by', 'updated_by'
    ]
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(MaintenanceReport)
class MaintenanceReportAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'maintenance_activity', 'report_type', 'status', 'created_by',
        'created_at'
    ]
    list_filter = [
        'report_type', 'status', 'maintenance_activity__status', 'created_at'
    ]
    search_fields = [
        'title', 'maintenance_activity__title', 'findings_summary'
    ]
    readonly_fields = [
        'created_at', 'updated_at', 'created_by', 'updated_by'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('activity', 'title', 'report_type', 'uploaded_by')
        }),
        ('Document', {
            'fields': ('document', 'get_file_size_display')
        }),
        ('Content', {
            'fields': ('content', 'summary')
        }),
        ('Analysis', {
            'fields': ('analyzed_data', 'is_processed', 'processing_errors', 'get_priority_score'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('report_date', 'technician_name', 'work_hours'),
            'classes': ('collapse',)
        }),
        ('Audit Information', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    
    def has_critical_issues(self, obj):
        return obj.has_critical_issues()
    has_critical_issues.boolean = True
    has_critical_issues.short_description = 'Critical Issues'
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
            obj.uploaded_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)