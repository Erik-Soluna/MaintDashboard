"""
Admin interface for maintenance models.
"""

from django.contrib import admin
from .models import MaintenanceActivityType, MaintenanceActivity, MaintenanceChecklist, MaintenanceSchedule


class MaintenanceChecklistInline(admin.TabularInline):
    model = MaintenanceChecklist
    extra = 0
    readonly_fields = ['completed_at', 'completed_by']


@admin.register(MaintenanceActivityType)
class MaintenanceActivityTypeAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'description', 'frequency_days', 'estimated_duration_hours',
        'is_mandatory', 'is_active', 'created_at'
    ]
    list_filter = ['is_mandatory', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    
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