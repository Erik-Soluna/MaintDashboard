"""
Admin interface for maintenance models.
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import (
    MaintenanceActivityType, MaintenanceActivity, MaintenanceChecklist, 
    MaintenanceSchedule, ActivityTypeCategory, ActivityTypeTemplate, MaintenanceReport, MaintenanceTimelineEntry
)


@admin.register(ActivityTypeCategory)
class ActivityTypeCategoryAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'description', 'color_preview', 'icon_preview', 'sort_order', 'is_active', 'created_at'
    ]
    list_filter = ['is_active', 'created_at', 'is_global']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    ordering = ['sort_order', 'name']
    list_editable = ['sort_order', 'is_active']
    actions = ['activate_categories', 'deactivate_categories', 'duplicate_categories']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'sort_order', 'is_active', 'is_global')
        }),
        ('Visual Settings', {
            'fields': ('color', 'icon'),
            'description': 'Customize the appearance of this category in the dashboard and reports.'
        }),
        ('Audit Information', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    
    def color_preview(self, obj):
        """Display color as a colored square with hex value."""
        if obj.color:
            return format_html(
                '<span style="display: inline-block; width: 20px; height: 20px; background-color: {}; border: 1px solid #ccc; margin-right: 8px;"></span>{}',
                obj.color, obj.color
            )
        return '-'
    color_preview.short_description = 'Color'
    
    def icon_preview(self, obj):
        """Display icon preview."""
        if obj.icon:
            return format_html('<i class="{}" style="font-size: 18px;"></i>', obj.icon)
        return '-'
    icon_preview.short_description = 'Icon'
    
    def activate_categories(self, request, queryset):
        """Bulk action to activate selected categories."""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} categories were successfully activated.')
    activate_categories.short_description = "Activate selected categories"
    
    def deactivate_categories(self, request, queryset):
        """Bulk action to deactivate selected categories."""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} categories were successfully deactivated.')
    deactivate_categories.short_description = "Deactivate selected categories"
    
    def duplicate_categories(self, request, queryset):
        """Bulk action to duplicate selected categories."""
        duplicated_count = 0
        for category in queryset:
            # Create a copy with a new name
            new_name = f"{category.name} (Copy)"
            counter = 1
            while ActivityTypeCategory.objects.filter(name=new_name).exists():
                counter += 1
                new_name = f"{category.name} (Copy {counter})"
            
            # Create the duplicate
            new_category = ActivityTypeCategory.objects.create(
                name=new_name,
                description=category.description,
                color=category.color,
                icon=category.icon,
                sort_order=category.sort_order + 100,  # Place after original
                is_active=False,  # Start as inactive
                is_global=category.is_global
            )
            duplicated_count += 1
        
        self.message_user(request, f'{duplicated_count} categories were successfully duplicated.')
    duplicate_categories.short_description = "Duplicate selected categories"
    
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
    search_fields = ['name', 'description', 'category__name']
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    filter_horizontal = ['applicable_equipment_categories']
    list_editable = ['is_active', 'is_mandatory']
    actions = ['activate_activity_types', 'deactivate_activity_types', 'duplicate_activity_types']
    
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
            'fields': ('applicable_equipment_categories',),
            'description': 'Select which equipment categories this activity type applies to.'
        }),
        ('Settings', {
            'fields': ('is_active',)
        }),
        ('Audit Information', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    
    def activate_activity_types(self, request, queryset):
        """Bulk action to activate selected activity types."""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} activity types were successfully activated.')
    activate_activity_types.short_description = "Activate selected activity types"
    
    def deactivate_activity_types(self, request, queryset):
        """Bulk action to deactivate selected activity types."""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} activity types were successfully deactivated.')
    deactivate_activity_types.short_description = "Deactivate selected activity types"
    
    def duplicate_activity_types(self, request, queryset):
        """Bulk action to duplicate selected activity types."""
        duplicated_count = 0
        for activity_type in queryset:
            # Create a copy with a new name
            new_name = f"{activity_type.name} (Copy)"
            counter = 1
            while MaintenanceActivityType.objects.filter(name=new_name).exists():
                counter += 1
                new_name = f"{activity_type.name} (Copy {counter})"
            
            # Create the duplicate
            new_activity_type = MaintenanceActivityType.objects.create(
                name=new_name,
                category=activity_type.category,
                template=activity_type.template,
                description=activity_type.description,
                estimated_duration_hours=activity_type.estimated_duration_hours,
                frequency_days=activity_type.frequency_days,
                is_mandatory=activity_type.is_mandatory,
                tools_required=activity_type.tools_required,
                parts_required=activity_type.parts_required,
                safety_notes=activity_type.safety_notes,
                is_active=False,  # Start as inactive
                created_by=request.user,
                updated_by=request.user
            )
            # Copy many-to-many relationships
            new_activity_type.applicable_equipment_categories.set(
                activity_type.applicable_equipment_categories.all()
            )
            duplicated_count += 1
        
        self.message_user(request, f'{duplicated_count} activity types were successfully duplicated.')
    duplicate_activity_types.short_description = "Duplicate selected activity types"
    
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


@admin.register(MaintenanceTimelineEntry)
class MaintenanceTimelineEntryAdmin(admin.ModelAdmin):
    list_display = [
        'activity', 'entry_type', 'title', 'created_by', 'created_at'
    ]
    list_filter = [
        'entry_type', 'created_at', 'activity__status', 'activity__equipment__category'
    ]
    search_fields = [
        'title', 'description', 'activity__title', 'activity__equipment__name'
    ]
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('activity', 'entry_type', 'title', 'description')
        }),
        ('Issue Details', {
            'fields': ('issue_severity', 'resolution_time'),
            'classes': ('collapse',),
            'description': 'Additional fields for issue and resolution entries'
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