"""
Admin interface for events models.
"""

from django.contrib import admin
from .models import CalendarEvent, EventComment, EventAttachment, EventReminder


class EventCommentInline(admin.TabularInline):
    model = EventComment
    extra = 0
    readonly_fields = ['created_at', 'created_by']


class EventAttachmentInline(admin.TabularInline):
    model = EventAttachment
    extra = 0
    readonly_fields = ['created_at', 'created_by']


class EventReminderInline(admin.TabularInline):
    model = EventReminder
    extra = 0
    readonly_fields = ['created_at', 'is_sent', 'sent_at']


@admin.register(CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'equipment', 'event_type', 'event_date', 
        'priority', 'assigned_to', 'is_completed'
    ]
    list_filter = [
        'event_type', 'priority', 'is_completed', 'all_day',
        'event_date', 'equipment__category'
    ]
    search_fields = ['title', 'equipment__name', 'description']
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    inlines = [EventCommentInline, EventAttachmentInline, EventReminderInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'event_type', 'priority')
        }),
        ('Associations', {
            'fields': ('equipment', 'maintenance_activity', 'assigned_to')
        }),
        ('Timing', {
            'fields': ('event_date', 'start_time', 'end_time', 'all_day')
        }),
        ('Recurrence', {
            'fields': ('is_recurring', 'recurrence_pattern'),
            'classes': ('collapse',)
        }),
        ('Notifications', {
            'fields': ('notify_assigned', 'notification_sent'),
            'classes': ('collapse',)
        }),
        ('Completion', {
            'fields': ('is_completed', 'completion_notes'),
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


@admin.register(EventComment)
class EventCommentAdmin(admin.ModelAdmin):
    list_display = ['event', 'created_by', 'is_internal', 'created_at']
    list_filter = ['is_internal', 'created_at']
    search_fields = ['event__title', 'comment']
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(EventAttachment)
class EventAttachmentAdmin(admin.ModelAdmin):
    list_display = ['title', 'event', 'created_by', 'created_at']
    list_filter = ['created_at']
    search_fields = ['title', 'event__title', 'description']
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(EventReminder)
class EventReminderAdmin(admin.ModelAdmin):
    list_display = [
        'event', 'user', 'reminder_type', 'reminder_time', 
        'is_sent', 'sent_at'
    ]
    list_filter = ['reminder_type', 'is_sent', 'reminder_time']
    search_fields = ['event__title', 'user__username', 'message']
    readonly_fields = ['created_at', 'updated_at', 'is_sent', 'sent_at']
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)