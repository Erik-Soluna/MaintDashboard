"""branding_css views (split from the original monolithic views.py)."""
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


@permission_required('administration.write')
def branding_settings(request):
    """Branding settings management page"""
    # Check if branding tables exist before trying to access them
    try:
        from django.db import connection
        from django.db.utils import ProgrammingError
        
        branding_table_exists = False
        css_table_exists = False
        
        try:
            # Check branding table
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM core_brandingsettings LIMIT 1")
                branding_table_exists = True
        except (ProgrammingError, Exception):
            branding_table_exists = False
        
        try:
            # Check CSS table
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM core_csscustomization LIMIT 1")
                css_table_exists = True
        except (ProgrammingError, Exception):
            css_table_exists = False
        
        branding = None
        css_customizations = []
        
        if branding_table_exists:
            try:
                branding = BrandingSettings.objects.get(is_active=True)
            except BrandingSettings.DoesNotExist:
                branding = None
        
        if css_table_exists:
            try:
                css_customizations = CSSCustomization.objects.filter(is_active=True).order_by('-priority', 'order')
            except Exception:
                css_customizations = []
        
        # Always initialize forms if tables exist
        if branding_table_exists:
            basic_form = BrandingBasicForm(instance=branding)
            navigation_form = BrandingNavigationForm(instance=branding)
            appearance_form = BrandingAppearanceForm(instance=branding)
            full_form = BrandingSettingsForm(instance=branding)  # For backward compatibility
        else:
            basic_form = None
            navigation_form = None
            appearance_form = None
            full_form = None
        
        if request.method == 'POST':
            if not branding_table_exists:
                messages.error(request, 'Branding system is not yet set up. Please run database migrations first.')
                return redirect('core:settings')
            
            # Determine which form was submitted based on the form action
            form_type = request.POST.get('form_type', 'basic')
            
            if form_type == 'basic':
                form = BrandingBasicForm(request.POST, request.FILES, instance=branding)
                success_message = 'Basic branding settings updated successfully!'
            elif form_type == 'navigation':
                form = BrandingNavigationForm(request.POST, instance=branding)
                success_message = 'Navigation labels updated successfully!'
            elif form_type == 'appearance':
                form = BrandingAppearanceForm(request.POST, request.FILES, instance=branding)
                success_message = 'Appearance settings updated successfully!'
            else:
                # Fallback to full form
                form = BrandingSettingsForm(request.POST, request.FILES, instance=branding)
                success_message = 'Branding settings updated successfully!'
            
            if form.is_valid():
                branding = form.save()
                messages.success(request, success_message)
                return redirect('core:branding_settings')
            else:
                # If form is invalid, re-initialize the forms with the invalid data
                if form_type == 'basic':
                    basic_form = form
                elif form_type == 'navigation':
                    navigation_form = form
                elif form_type == 'appearance':
                    appearance_form = form
                else:
                    full_form = form
        
        context = {
            'basic_form': basic_form,
            'navigation_form': navigation_form,
            'appearance_form': appearance_form,
            'full_form': full_form,  # For backward compatibility
            'branding': branding,
            'css_customizations': css_customizations,
            'active_tab': 'branding',
            'tables_exist': branding_table_exists and css_table_exists
        }
        return render(request, 'core/branding_settings.html', context)
        
    except Exception as e:
        # If anything goes wrong, show an error message
        messages.error(request, f'Branding system is not available: {str(e)}. Please run database migrations first.')
        return redirect('core:settings')


@login_required
def css_customization_list(request):
    """List all CSS customizations"""
    # Check if CSS customization table exists
    try:
        from django.db import connection
        from django.db.utils import ProgrammingError
        
        css_table_exists = False
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM core_csscustomization LIMIT 1")
                css_table_exists = True
        except (ProgrammingError, Exception):
            css_table_exists = False
        
        if not css_table_exists:
            messages.error(request, 'CSS customization system is not yet set up. Please run database migrations first.')
            return redirect('core:branding_settings')
        
        css_customizations = CSSCustomization.objects.all().order_by('-priority', 'order', 'name')
        
        context = {
            'css_customizations': css_customizations,
            'active_tab': 'branding'
        }
        return render(request, 'core/css_customization_list.html', context)
        
    except Exception as e:
        messages.error(request, f'CSS customization system is not available: {str(e)}. Please run database migrations first.')
        return redirect('core:branding_settings')


@permission_required('administration.write')
def css_customization_create(request):
    """Create a new CSS customization"""
    # Check if CSS customization table exists
    try:
        from django.db import connection
        from django.db.utils import ProgrammingError
        
        css_table_exists = False
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM core_csscustomization LIMIT 1")
                css_table_exists = True
        except (ProgrammingError, Exception):
            css_table_exists = False
        
        if not css_table_exists:
            messages.error(request, 'CSS customization system is not yet set up. Please run database migrations first.')
            return redirect('core:branding_settings')
        
        if request.method == 'POST':
            form = CSSCustomizationForm(request.POST)
            if form.is_valid():
                css_customization = form.save(commit=False)
                css_customization.created_by = request.user
                css_customization.save()
                messages.success(request, 'CSS customization created successfully!')
                return redirect('core:css_customization_list')
        else:
            form = CSSCustomizationForm()
        
        context = {
            'form': form,
            'active_tab': 'branding',
            'is_create': True
        }
        return render(request, 'core/css_customization_form.html', context)
        
    except Exception as e:
        messages.error(request, f'CSS customization system is not available: {str(e)}. Please run database migrations first.')
        return redirect('core:branding_settings')


@permission_required('administration.write')
def css_customization_edit(request, pk):
    """Edit an existing CSS customization"""
    # Check if CSS customization table exists
    try:
        from django.db import connection
        from django.db.utils import ProgrammingError
        
        css_table_exists = False
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM core_csscustomization LIMIT 1")
                css_table_exists = True
        except (ProgrammingError, Exception):
            css_table_exists = False
        
        if not css_table_exists:
            messages.error(request, 'CSS customization system is not yet set up. Please run database migrations first.')
            return redirect('core:branding_settings')
        
        try:
            css_customization = CSSCustomization.objects.get(pk=pk)
        except CSSCustomization.DoesNotExist:
            messages.error(request, 'CSS customization not found.')
            return redirect('core:css_customization_list')
        
        if request.method == 'POST':
            form = CSSCustomizationForm(request.POST, instance=css_customization)
            if form.is_valid():
                form.save()
                messages.success(request, 'CSS customization updated successfully!')
                return redirect('core:css_customization_list')
        else:
            form = CSSCustomizationForm(instance=css_customization)
        
        context = {
            'form': form,
            'css_customization': css_customization,
            'active_tab': 'branding',
            'is_create': False
        }
        return render(request, 'core/css_customization_form.html', context)
        
    except Exception as e:
        messages.error(request, f'CSS customization system is not available: {str(e)}. Please run database migrations first.')
        return redirect('core:branding_settings')


@permission_required('administration.write')
def css_customization_delete(request, pk):
    """Delete a CSS customization"""
    # Check if CSS customization table exists
    try:
        from django.db import connection
        from django.db.utils import ProgrammingError
        
        css_table_exists = False
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM core_csscustomization LIMIT 1")
                css_table_exists = True
        except (ProgrammingError, Exception):
            css_table_exists = False
        
        if not css_table_exists:
            messages.error(request, 'CSS customization system is not yet set up. Please run database migrations first.')
            return redirect('core:branding_settings')
        
        try:
            css_customization = CSSCustomization.objects.get(pk=pk)
            name = css_customization.name
            css_customization.delete()
            messages.success(request, f'CSS customization "{name}" deleted successfully!')
        except CSSCustomization.DoesNotExist:
            messages.error(request, 'CSS customization not found.')
        
        return redirect('core:css_customization_list')
        
    except Exception as e:
        messages.error(request, f'CSS customization system is not available: {str(e)}. Please run database migrations first.')
        return redirect('core:branding_settings')


@login_required
def css_preview(request):
    """Preview CSS changes in real-time"""
    # Check if CSS customization table exists
    try:
        from django.db import connection
        from django.db.utils import ProgrammingError
        
        css_table_exists = False
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM core_csscustomization LIMIT 1")
                css_table_exists = True
        except (ProgrammingError, Exception):
            css_table_exists = False
        
        if not css_table_exists:
            messages.error(request, 'CSS customization system is not yet set up. Please run database migrations first.')
            return redirect('core:branding_settings')
        
        if request.method == 'POST':
            form = CSSPreviewForm(request.POST)
            if form.is_valid():
                css_code = form.cleaned_data['css_code']
            else:
                css_code = ''
        else:
            form = CSSPreviewForm()
            css_code = ''
        
        # Get active CSS customizations for comparison
        active_css = CSSCustomization.objects.filter(is_active=True).order_by('-priority', 'order')
        
        context = {
            'form': form,
            'css_code': css_code,
            'active_css': active_css,
            'active_tab': 'branding'
        }
        return render(request, 'core/css_preview.html', context)
        
    except Exception as e:
        messages.error(request, f'CSS customization system is not available: {str(e)}. Please run database migrations first.')
        return redirect('core:branding_settings')


@permission_required('administration.write')
def css_toggle(request, pk):
    """Toggle CSS customization active status"""
    # Check if CSS customization table exists
    try:
        from django.db import connection
        from django.db.utils import ProgrammingError
        
        css_table_exists = False
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM core_csscustomization LIMIT 1")
                css_table_exists = True
        except (ProgrammingError, Exception):
            css_table_exists = False
        
        if not css_table_exists:
            messages.error(request, 'CSS customization system is not yet set up. Please run database migrations first.')
            return redirect('core:branding_settings')
        
        try:
            css_customization = CSSCustomization.objects.get(pk=pk)
            css_customization.is_active = not css_customization.is_active
            css_customization.save()
            
            status = 'activated' if css_customization.is_active else 'deactivated'
            messages.success(request, f'CSS customization "{css_customization.name}" {status} successfully!')
        except CSSCustomization.DoesNotExist:
            messages.error(request, 'CSS customization not found.')
        
        return redirect('core:css_customization_list')
        
    except Exception as e:
        messages.error(request, f'CSS customization system is not available: {str(e)}. Please run database migrations first.')
        return redirect('core:branding_settings')


__all__ = ["branding_settings", "css_customization_list", "css_customization_create", "css_customization_edit", "css_customization_delete", "css_preview", "css_toggle"]
