"""users_roles views (split from the original monolithic views.py)."""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth.models import User
from equipment.models import Equipment
from maintenance.models import MaintenanceActivity
from events.models import CalendarEvent
from core.models import Location, EquipmentCategory, Role, Permission, UserProfile, Customer, BrandingSettings, DashboardSettings, CSSCustomization
from core.forms import LocationForm, EquipmentCategoryForm, CustomerForm, UserForm, BrandingSettingsForm, BrandingBasicForm, BrandingNavigationForm, BrandingAppearanceForm, CSSCustomizationForm, CSSPreviewForm, DashboardSettingsForm
from django.utils import timezone
from django.db.models import Q, Count
from datetime import datetime, timedelta, date
from django.http import JsonResponse, HttpResponseRedirect, HttpResponse
from django.core.paginator import Paginator
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST, require_GET
from django.core.management import call_command
from django.core.cache import cache
from django.db import connection
from django.conf import settings
from io import StringIO
import json
import csv
import re
import time
import psutil
import logging
import shutil
import redis
from django_celery_beat.models import PeriodicTask
import requests
from django.test import RequestFactory
from django.contrib.admin.views.decorators import staff_member_required
import hmac
import hashlib
import os
import shutil
import redis
from django_celery_beat.models import PeriodicTask
from django.utils import timezone
from .helpers import *  # noqa: F401,F403 (shared helpers + globals)
from core.rbac import permission_required


@permission_required('users.manage')
def user_management(request):
    """Enhanced user management view with role assignment."""
    if request.method == 'POST':
        action = request.POST.get('action')
        user_id = request.POST.get('user_id')
        
        if action == 'toggle_active' and user_id:
            user = get_object_or_404(User, id=user_id)
            user.is_active = not user.is_active
            user.save()
            status = 'activated' if user.is_active else 'deactivated'
            messages.success(request, f'User {user.username} has been {status}.')
        
        elif action == 'toggle_staff' and user_id:
            user = get_object_or_404(User, id=user_id)
            user.is_staff = not user.is_staff
            user.save()
            status = 'granted' if user.is_staff else 'revoked'
            messages.success(request, f'Staff privileges {status} for {user.username}.')
        
        elif action == 'assign_role' and user_id:
            user = get_object_or_404(User, id=user_id)
            role_id = request.POST.get('role_id')
            
            # Get or create user profile
            profile, created = UserProfile.objects.get_or_create(user=user)
            
            if role_id:
                role = get_object_or_404(Role, id=role_id)
                profile.role = role
                profile.save()
                messages.success(request, f'Role "{role.display_name}" assigned to {user.username}.')
            else:
                profile.role = None
                profile.save()
                messages.success(request, f'Role removed from {user.username}.')
        
        return redirect('core:user_management')
    
    users = User.objects.all().select_related('userprofile', 'userprofile__role').order_by('username')
    roles = Role.objects.filter(is_active=True).order_by('display_name')
    
    # Get user statistics
    total_users = users.count()
    active_users = users.filter(is_active=True).count()
    staff_users = users.filter(is_staff=True).count()
    superusers = users.filter(is_superuser=True).count()
    
    # Pagination
    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'users': users,
        'roles': roles,
        'total_users': total_users,
        'active_users': active_users,
        'staff_users': staff_users,
        'superusers': superusers,
    }
    return render(request, 'core/user_management.html', context)


def _send_welcome_email(request, user):
    """Email a newly-created user a welcome + set-your-password link."""
    from django.contrib.auth.tokens import default_token_generator
    from django.utils.http import urlsafe_base64_encode
    from django.utils.encoding import force_bytes
    from django.template.loader import render_to_string
    from django.core.mail import send_mail
    from django.urls import reverse
    from django.conf import settings

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    ctx = {
        'user': user,
        'set_password_url': request.build_absolute_uri(
            reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token})),
        'login_url': request.build_absolute_uri(reverse('login')),
    }
    subject = render_to_string('registration/account_welcome_subject.txt', ctx).strip()
    body = render_to_string('registration/account_welcome_email.html', ctx)
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)


@permission_required('users.manage')
def add_user(request):
    """Add new user."""
    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            user = form.save()
            email_note = ''
            if user.email:
                try:
                    _send_welcome_email(request, user)
                    email_note = f' A welcome email was sent to {user.email}.'
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning(f"Welcome email failed for {user.username}: {e}")
                    email_note = ' (Could not send the welcome email — check email settings.)'
            messages.success(request, f'User "{user.username}" has been created successfully.' + email_note)
            return redirect('core:user_management')
    else:
        form = UserForm()
    
    context = {
        'form': form,
        'title': 'Add User',
        'action': 'Add'
    }
    return render(request, 'core/user_form.html', context)


@permission_required('users.manage')
def edit_user(request, user_id):
    """Edit existing user."""
    user = get_object_or_404(User, id=user_id)
    profile, created = UserProfile.objects.get_or_create(user=user)
    
    if request.method == 'POST':
        form = UserForm(request.POST, instance=user)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'User "{user.username}" has been updated successfully.')
            return redirect('core:user_management')
    else:
        # Initialize form with user and profile data
        form = UserForm(instance=user, initial={
            'role': profile.role,
            'employee_id': profile.employee_id,
            'department': profile.department,
            'phone_number': profile.phone_number,
        })
    
    context = {
        'form': form,
        'user': user,
        'title': 'Edit User',
        'action': 'Edit'
    }
    return render(request, 'core/user_form.html', context)


@login_required
@user_passes_test(is_staff_or_superuser)
def users_api(request):
    """API endpoint for user management."""
    if request.method == 'GET':
        try:
            users = User.objects.select_related('userprofile').values(
                'id', 'username', 'first_name', 'last_name', 'email',
                'is_active', 'is_staff', 'is_superuser', 'last_login',
                'userprofile__department', 'userprofile__phone_number'
            )
            return JsonResponse(list(users), safe=False)
        except Exception as e:
            return JsonResponse({
                'error': f'Error fetching users: {str(e)}'
            }, status=500)


@login_required
@user_passes_test(is_staff_or_superuser)
def roles_permissions_management(request):
    """Role and permission management view."""
    roles = Role.objects.all().prefetch_related('permissions').order_by('display_name')
    permissions = Permission.objects.filter(is_active=True).order_by('module', 'name')
    
    # Group permissions by module
    permissions_by_module = {}
    for permission in permissions:
        if permission.module not in permissions_by_module:
            permissions_by_module[permission.module] = []
        permissions_by_module[permission.module].append(permission)
    
    context = {
        'roles': roles,
        'permissions': permissions,
        'permissions_by_module': permissions_by_module,
    }
    return render(request, 'core/roles_permissions_management.html', context)


@login_required
@user_passes_test(is_staff_or_superuser)
def role_detail_api(request, role_id):
    """API endpoint for role management."""
    role = get_object_or_404(Role, id=role_id)
    
    if request.method == 'GET':
        # Return role details with permissions
        permissions = list(role.permissions.values('id', 'name', 'codename', 'module'))
        return JsonResponse({
            'id': role.id,
            'name': role.name,
            'display_name': role.display_name,
            'description': role.description,
            'is_active': role.is_active,
            'is_system_role': role.is_system_role,
            'permissions': permissions
        })
    
    elif request.method == 'PUT':
        try:
            data = json.loads(request.body)
            
            # Validate required fields
            name = data.get('name', role.name).strip()
            display_name = data.get('display_name', role.display_name).strip()
            
            if not name:
                return JsonResponse({
                    'error': 'Role name is required'
                }, status=400)
            
            if not display_name:
                return JsonResponse({
                    'error': 'Display name is required'
                }, status=400)
            
            # Check for duplicate role names (excluding current role)
            if Role.objects.filter(name=name).exclude(id=role.id).exists():
                return JsonResponse({
                    'error': f'A role with the name "{name}" already exists'
                }, status=400)
            
            # Update role
            role.name = name
            role.display_name = display_name
            role.description = data.get('description', role.description)
            role.is_active = data.get('is_active', role.is_active)
            role.updated_by = request.user
            role.save()
            
            # Update permissions
            if 'permission_ids' in data:
                permission_ids = data['permission_ids']
                role.permissions.set(permission_ids)
            
            return JsonResponse({'message': 'Role updated successfully'})
            
        except json.JSONDecodeError:
            return JsonResponse({
                'error': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'error': f'Error updating role: {str(e)}'
            }, status=500)
    
    elif request.method == 'DELETE':
        # Delete role (only if not system role)
        if role.is_system_role:
            return JsonResponse({'error': 'Cannot delete system role'}, status=400)
        
        # Check if any users have this role
        users_with_role = UserProfile.objects.filter(role=role).count()
        if users_with_role > 0:
            return JsonResponse({
                'error': f'Cannot delete role. {users_with_role} users are assigned to this role.'
            }, status=400)
        
        role.delete()
        return JsonResponse({'message': 'Role deleted successfully'})


@login_required
@user_passes_test(is_staff_or_superuser)
def roles_api(request):
    """API endpoint for role management."""
    if request.method == 'GET':
        roles = Role.objects.all().values(
            'id', 'name', 'display_name', 'description', 'is_active', 'is_system_role'
        )
        return JsonResponse(list(roles), safe=False)
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Validate required fields
            name = data.get('name', '').strip()
            display_name = data.get('display_name', '').strip()
            
            if not name:
                return JsonResponse({
                    'error': 'Role name is required'
                }, status=400)
            
            if not display_name:
                return JsonResponse({
                    'error': 'Display name is required'
                }, status=400)
            
            # Check for duplicate role names
            if Role.objects.filter(name=name).exists():
                return JsonResponse({
                    'error': f'A role with the name "{name}" already exists'
                }, status=400)
            
            # Create role
            role = Role.objects.create(
                name=name,
                display_name=display_name,
                description=data.get('description', ''),
                is_active=data.get('is_active', True),
                created_by=request.user,
                updated_by=request.user
            )
            
            # Assign permissions
            if 'permission_ids' in data:
                permission_ids = data['permission_ids']
                role.permissions.set(permission_ids)
            
            return JsonResponse({
                'id': role.id,
                'name': role.name,
                'display_name': role.display_name,
                'message': 'Role created successfully'
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'error': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'error': f'Error creating role: {str(e)}'
            }, status=500)


@login_required
@user_passes_test(is_staff_or_superuser)
@require_http_methods(["POST"])
def reset_rbac(request):
    """Reset RBAC (Role-Based Access Control) system."""
    try:
        from django.core.management import call_command
        from io import StringIO
        
        # Capture command output
        output = StringIO()
        
        # Call the reset RBAC command
        call_command('reset_rbac', stdout=output, verbosity=2)
        
        result = output.getvalue()
        output.close()
        
        return JsonResponse({
            'success': True,
            'message': 'RBAC system reset successfully',
            'output': result
        })
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return JsonResponse({
            'success': False,
            'error': f'Error resetting RBAC: {str(e)}',
            'details': error_details
        }, status=500)


__all__ = ["user_management", "add_user", "edit_user", "users_api", "roles_permissions_management", "role_detail_api", "roles_api", "reset_rbac"]
