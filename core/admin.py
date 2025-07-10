"""
Custom admin configuration for core models.
Includes special handling for first-time login password changes.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy, path
from django.utils.timezone import now
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from .models import EquipmentCategory, Location, UserProfile


# Custom Password Change View for Admin
@method_decorator(staff_member_required, name='dispatch')
class AdminPasswordChangeView(PasswordChangeView):
    """
    Custom password change view that updates last_login when password
    is successfully changed for first-time login users.
    """
    template_name = 'admin/auth/user/password_change_form.html'
    success_url = reverse_lazy('admin:password_change_done')

    def form_valid(self, form):
        """Handle successful password change."""
        response = super().form_valid(form)
        
        # If this is a first-time login (last_login is None), update it
        if self.request.user.last_login is None:
            self.request.user.last_login = now()
            self.request.user.save(update_fields=['last_login'])
            
            messages.success(
                self.request,
                'Password changed successfully! You can now access all features.'
            )
        
        return response


# Custom User Admin
class UserProfileInline(admin.StackedInline):
    """Inline admin for user profiles."""
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fields = ('role', 'employee_id', 'department', 'phone_number', 'is_active')


class CustomUserAdmin(BaseUserAdmin):
    """Extended User admin with profile inline."""
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_role', 'last_login')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'date_joined', 'userprofile__role')
    
    def get_role(self, obj):
        """Get user role from profile."""
        try:
            if obj.userprofile.role:
                return obj.userprofile.role.display_name
            else:
                return 'No Role Assigned'
        except UserProfile.DoesNotExist:
            return 'No Profile'
    get_role.short_description = 'Role'
    get_role.admin_order_field = 'userprofile__role'


# Equipment Category Admin
@admin.register(EquipmentCategory)
class EquipmentCategoryAdmin(admin.ModelAdmin):
    """Admin for equipment categories."""
    list_display = ('name', 'description', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    ordering = ('name',)
    
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'is_active')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    
    def save_model(self, request, obj, form, change):
        """Set created_by and updated_by fields."""
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


# Location Admin
@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    """Admin for locations with hierarchy support."""
    list_display = ('name', 'parent_location', 'is_site', 'is_active', 'created_at')
    list_filter = ('is_site', 'is_active', 'created_at')
    search_fields = ('name', 'address')
    ordering = ('name',)
    
    fieldsets = (
        (None, {
            'fields': ('name', 'parent_location', 'is_site', 'is_active')
        }),
        ('Details', {
            'fields': ('address', 'latitude', 'longitude'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    
    def save_model(self, request, obj, form, change):
        """Set created_by and updated_by fields."""
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


# User Profile Admin
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Admin for user profiles."""
    list_display = ('user', 'role', 'employee_id', 'department', 'is_active')
    list_filter = ('role', 'is_active', 'department')
    search_fields = ('user__username', 'user__email', 'employee_id', 'department')
    ordering = ('user__username',)
    
    fieldsets = (
        (None, {
            'fields': ('user', 'role', 'is_active')
        }),
        ('Details', {
            'fields': ('employee_id', 'department', 'phone_number')
        }),
    )


# Unregister the default User admin and register our custom one
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

# Customize admin site headers
admin.site.site_header = 'Maintenance Dashboard Administration'
admin.site.site_title = 'Maintenance Dashboard Admin'
admin.site.index_title = 'Welcome to Maintenance Dashboard Administration'